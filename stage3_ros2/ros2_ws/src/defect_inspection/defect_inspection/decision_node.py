"""decision_node — grades detections into a recovery decision (Stage 2).

Subscribes to /inspection/detection (DetectionResult), runs the transparent
Stage 2 grader, and publishes /inspection/result (InspectionResult) with the
condition score, REUSE/REPAIR/RECYCLE decision and decision confidence.

Parameters:
    reuse_min (float)   condition score ≥ this → REUSE. Default 80.
    repair_min (float)  condition score ≥ this → REPAIR (else RECYCLE). Default 50.
    repo_root (str)     repo path, if stage2_decision isn't pip-installed.
"""
from __future__ import annotations

import uuid

import rclpy
from rclpy.node import Node

from defect_inspection_interfaces.msg import DetectionResult, InspectionResult

from ._repo import ensure_repo_on_path


class DecisionNode(Node):
    def __init__(self):
        super().__init__("decision_node")
        self.declare_parameter("reuse_min", 80.0)
        self.declare_parameter("repair_min", 50.0)
        self.declare_parameter("repo_root", "")

        reuse_min = self.get_parameter("reuse_min").get_parameter_value().double_value
        repair_min = self.get_parameter("repair_min").get_parameter_value().double_value
        repo_root = self.get_parameter("repo_root").get_parameter_value().string_value

        ensure_repo_on_path(repo_root)
        from stage2_decision.grading import GradingConfig, grade_record

        self._grade_record = grade_record
        self.grading_cfg = GradingConfig(reuse_min=reuse_min, repair_min=repair_min)

        self.pub = self.create_publisher(InspectionResult, "/inspection/result", 10)
        self.sub = self.create_subscription(
            DetectionResult, "/inspection/detection", self.on_detection, 10)

        self.get_logger().info(
            f"decision_node ready (REUSE≥{reuse_min:.0f}, REPAIR≥{repair_min:.0f})")

    def on_detection(self, det: DetectionResult):
        record = {
            "pred_class": det.pred_class,
            "confidence": det.confidence,
            "defect_area_pct": det.defect_area_pct,
        }
        g = self._grade_record(record, self.grading_cfg)

        res = InspectionResult()
        res.header = det.header
        res.part_id = f"PART-{uuid.uuid4().hex[:8].upper()}"
        res.source_id = det.source_id
        res.pred_class = g["pred_class"]
        res.confidence = float(g["model_confidence"])
        res.defect_area_pct = float(g["defect_area_pct"])
        res.severity = float(g["severity"])
        res.condition_score = float(g["condition_score"])
        res.decision = g["decision"]
        res.decision_confidence = float(g["decision_confidence"])
        self.pub.publish(res)

        self.get_logger().info(
            f"{res.source_id}: {res.pred_class} → {res.decision} "
            f"(condition {res.condition_score:.0f}/100, conf {res.decision_confidence:.2f})")


def main(args=None):
    rclpy.init(args=args)
    node = DecisionNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
