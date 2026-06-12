"""inspection_node — runs the Stage 1 computer-vision + ML model.

Subscribes to camera frames, runs the trained surface-defect model with Grad-CAM,
and publishes:
    * /inspection/overlay   (sensor_msgs/Image)  — original|heatmap|overlay panel
    * /inspection/detection (DetectionResult)    — class + confidence + defect-area%

Grading into REUSE/REPAIR/RECYCLE is the decision node's job; this node only does
detection, keeping the CV concern isolated.

Parameters:
    weights (str)         path to the Stage 1 checkpoint (best_model.pt).
    device (str)          "cpu" | "cuda" | "auto". Default "cpu".
    repo_root (str)       repo path, if stage1_vision isn't pip-installed.
    mask_threshold (float) Grad-CAM threshold for the binary defect mask / area%.
"""
from __future__ import annotations

import numpy as np
import rclpy
from cv_bridge import CvBridge
from rclpy.node import Node
from sensor_msgs.msg import Image

from defect_inspection_interfaces.msg import DetectionResult

from ._repo import ensure_repo_on_path


class InspectionNode(Node):
    def __init__(self):
        super().__init__("inspection_node")
        self.declare_parameter("weights", "")
        self.declare_parameter("device", "cpu")
        self.declare_parameter("repo_root", "")
        self.declare_parameter("mask_threshold", 0.5)

        weights = self.get_parameter("weights").get_parameter_value().string_value
        device = self.get_parameter("device").get_parameter_value().string_value
        repo_root = self.get_parameter("repo_root").get_parameter_value().string_value
        self.mask_threshold = self.get_parameter(
            "mask_threshold").get_parameter_value().double_value

        # Make Stage 1 importable, then load the model (heavy imports kept local
        # so the rest of the graph can start even if torch is slow to import).
        ensure_repo_on_path(repo_root)
        import torch  # noqa: F401
        from stage1_vision import model as model_lib
        from stage1_vision import utils
        from stage1_vision.dataset import build_transforms
        from stage1_vision.gradcam import GradCAM
        from stage1_vision.inference import (
            _softmax_probs,
            defect_mask_and_area,
            make_overlay,
        )

        self._torch = torch
        self._make_overlay = make_overlay
        self._defect_mask_and_area = defect_mask_and_area
        self._softmax_probs = _softmax_probs

        self.device = utils.resolve_device(device)
        if not weights:
            self.get_logger().error("Parameter 'weights' is empty — set it to your "
                                    "Stage 1 checkpoint (outputs/best_model.pt).")
        self.model, ckpt = model_lib.load_checkpoint(weights, map_location=self.device)
        self.model.to(self.device)
        self.class_names = ckpt["class_names"]
        self.image_size = ckpt["image_size"]
        self.transform = build_transforms(self.image_size, train=False, augment=False)
        self.target_layer = model_lib.last_conv_layer(self.model, ckpt["backbone"])
        self._GradCAM = GradCAM

        self.bridge = CvBridge()
        self.overlay_pub = self.create_publisher(Image, "/inspection/overlay", 10)
        self.det_pub = self.create_publisher(DetectionResult, "/inspection/detection", 10)
        self.sub = self.create_subscription(
            Image, "/inspection/image_raw", self.on_image, 10)

        self.get_logger().info(
            f"inspection_node ready: {ckpt['backbone']} on {self.device}, "
            f"classes={self.class_names}")

    def on_image(self, msg: Image):
        from PIL import Image as PILImage

        source_id = msg.header.frame_id or "unknown"
        bgr = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        rgb = bgr[:, :, ::-1]
        pil = PILImage.fromarray(rgb)

        tensor = self.transform(pil).unsqueeze(0).to(self.device)

        cam = self._GradCAM(self.model, self.target_layer)
        heatmap, class_idx, confidence = cam(tensor)        # Grad-CAM (needs grad)
        probs = self._softmax_probs(self.model, tensor, self.device)
        cam.remove_hooks()

        pred_class = self.class_names[class_idx]
        _, area_pct = self._defect_mask_and_area(heatmap, self.mask_threshold)

        # Publish the visualization overlay for RViz.
        rgb_vis = np.array(pil.resize((self.image_size, self.image_size)))
        label = f"{pred_class}  {confidence*100:.1f}%  area={area_pct:.1f}%"
        panel_bgr = self._make_overlay(rgb_vis, heatmap, label)  # BGR
        overlay_msg = self.bridge.cv2_to_imgmsg(panel_bgr, encoding="bgr8")
        overlay_msg.header.stamp = msg.header.stamp
        overlay_msg.header.frame_id = "camera_optical_frame"
        self.overlay_pub.publish(overlay_msg)

        # Publish the structured detection for the decision node.
        det = DetectionResult()
        det.header.stamp = msg.header.stamp
        det.header.frame_id = "camera_optical_frame"
        det.source_id = source_id
        det.pred_class = pred_class
        det.confidence = float(confidence)
        det.defect_area_pct = float(area_pct)
        self.det_pub.publish(det)

        _ = probs  # full vector available if a richer message is wanted later
        self.get_logger().info(
            f"detected {pred_class} (conf {confidence:.2f}, area {area_pct:.1f}%) "
            f"on {source_id}")


def main(args=None):
    rclpy.init(args=args)
    node = InspectionNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
