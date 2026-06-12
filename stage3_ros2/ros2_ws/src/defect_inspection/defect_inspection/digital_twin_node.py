"""digital_twin_node — maintains the live digital-twin state.

Subscribes to /inspection/result (InspectionResult), records every part in the
Stage 2 digital twin (append-only JSONL), and publishes:
    * /inspection/decision_marker (visualization_msgs/MarkerArray) — a colored
      text marker showing the latest decision and a running-statistics marker,
      for RViz.

Parameters:
    store (str)        digital-twin JSONL path. Default outputs/digital_twin.jsonl.
    repo_root (str)    repo path, if stage2_decision isn't pip-installed.
    marker_frame (str) TF frame the RViz markers are placed in. Default "world".
"""
from __future__ import annotations

import rclpy
from rclpy.node import Node
from visualization_msgs.msg import Marker, MarkerArray

from defect_inspection_interfaces.msg import InspectionResult

from ._repo import ensure_repo_on_path


def _hex_to_rgb(h: str) -> tuple[float, float, float]:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))  # type: ignore


class DigitalTwinNode(Node):
    def __init__(self):
        super().__init__("digital_twin_node")
        self.declare_parameter("store", "")
        self.declare_parameter("repo_root", "")
        self.declare_parameter("marker_frame", "world")

        store = self.get_parameter("store").get_parameter_value().string_value
        repo_root = self.get_parameter("repo_root").get_parameter_value().string_value
        self.marker_frame = self.get_parameter(
            "marker_frame").get_parameter_value().string_value

        ensure_repo_on_path(repo_root)
        from stage2_decision.digital_twin import DigitalTwin
        from stage2_decision.grading import DECISION_COLORS

        self.twin = DigitalTwin(store or None)
        self.decision_colors = DECISION_COLORS

        self.marker_pub = self.create_publisher(
            MarkerArray, "/inspection/decision_marker", 10)
        self.sub = self.create_subscription(
            InspectionResult, "/inspection/result", self.on_result, 10)

        self.get_logger().info(f"digital_twin_node ready, store={self.twin.store_path}")

    def on_result(self, msg: InspectionResult):
        grading = {
            "pred_class": msg.pred_class,
            "model_confidence": round(msg.confidence, 4),
            "defect_area_pct": round(msg.defect_area_pct, 2),
            "severity": round(msg.severity, 3),
            "condition_score": round(msg.condition_score, 1),
            "decision": msg.decision,
            "decision_confidence": round(msg.decision_confidence, 3),
        }
        stored = self.twin.add(image=msg.source_id, grading=grading, part_id=msg.part_id)
        stats = self.twin.stats()

        self.get_logger().info(
            f"recorded {stored['part_id']} ({msg.source_id}) → {msg.decision} | "
            f"twin now holds {stats['total_parts']} parts, "
            f"recovery rate {stats['recovery_rate_pct']:.0f}%")

        self.marker_pub.publish(self._markers(msg, stats))

    def _markers(self, msg: InspectionResult, stats: dict) -> MarkerArray:
        arr = MarkerArray()

        # 1) Latest-decision text, colored by decision.
        r, g, b = _hex_to_rgb(self.decision_colors.get(msg.decision, "#888888"))
        latest = Marker()
        latest.header.frame_id = self.marker_frame
        latest.header.stamp = self.get_clock().now().to_msg()
        latest.ns = "decision"
        latest.id = 0
        latest.type = Marker.TEXT_VIEW_FACING
        latest.action = Marker.ADD
        latest.pose.position.x = 0.0
        latest.pose.position.y = 0.0
        latest.pose.position.z = 1.2
        latest.pose.orientation.w = 1.0
        latest.scale.z = 0.12          # text height (m)
        latest.color.r, latest.color.g, latest.color.b, latest.color.a = r, g, b, 1.0
        latest.text = (f"{msg.decision}\n{msg.source_id}\n"
                       f"{msg.pred_class}  cond {msg.condition_score:.0f}/100")
        arr.markers.append(latest)

        # 2) Running statistics text.
        counts = stats["decision_counts"]
        stat = Marker()
        stat.header.frame_id = self.marker_frame
        stat.header.stamp = latest.header.stamp
        stat.ns = "stats"
        stat.id = 1
        stat.type = Marker.TEXT_VIEW_FACING
        stat.action = Marker.ADD
        stat.pose.position.x = 0.0
        stat.pose.position.y = 0.0
        stat.pose.position.z = 0.85
        stat.pose.orientation.w = 1.0
        stat.scale.z = 0.07
        stat.color.r = stat.color.g = stat.color.b = stat.color.a = 1.0
        stat.text = (f"parts: {stats['total_parts']}  |  "
                     f"REUSE {counts['REUSE']}  REPAIR {counts['REPAIR']}  "
                     f"RECYCLE {counts['RECYCLE']}  |  "
                     f"recovery {stats['recovery_rate_pct']:.0f}%")
        arr.markers.append(stat)
        return arr


def main(args=None):
    rclpy.init(args=args)
    node = DigitalTwinNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
