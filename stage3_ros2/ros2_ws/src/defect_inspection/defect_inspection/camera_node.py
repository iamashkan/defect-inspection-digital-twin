"""camera_node — simulates the inspection cell's fixed camera.

Publishes a stream of "recovered part" images (from a folder, e.g. the Stage 1
test set) as sensor_msgs/Image on `/inspection/image_raw` at a fixed rate. This
stands in for a real camera feed so the rest of the pipeline runs in pure
simulation; when launched with Gazebo, the Gazebo scene provides the 3D visual of
the cell while this node provides the defect imagery the CV model actually sees.

Parameters:
    image_dir (str)      folder of part images to cycle through (recursively).
    publish_rate (float) Hz. Default 0.5 (one part every 2 s).
    loop (bool)          restart from the first image after the last. Default True.
    frame_id (str)       NOTE: for the demo we carry the *source filename* in the
                         image header.frame_id so downstream nodes can label the
                         part. Set to a real TF frame if you don't need that.
"""
from __future__ import annotations

from pathlib import Path

import cv2
import rclpy
from cv_bridge import CvBridge
from rclpy.node import Node
from sensor_msgs.msg import Image

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}


class CameraNode(Node):
    def __init__(self):
        super().__init__("camera_node")
        self.declare_parameter("image_dir", "")
        self.declare_parameter("publish_rate", 0.5)
        self.declare_parameter("loop", True)
        self.declare_parameter("frame_id", "camera_optical_frame")

        image_dir = self.get_parameter("image_dir").get_parameter_value().string_value
        self.rate = self.get_parameter("publish_rate").get_parameter_value().double_value
        self.loop = self.get_parameter("loop").get_parameter_value().bool_value

        self.bridge = CvBridge()
        self.publisher = self.create_publisher(Image, "/inspection/image_raw", 10)

        self.images = self._gather(image_dir)
        if not self.images:
            self.get_logger().error(
                f"No images found under '{image_dir}'. Set the image_dir parameter "
                f"to a folder of part images (e.g. data/synthetic/test)."
            )
        else:
            self.get_logger().info(
                f"camera_node: {len(self.images)} images from '{image_dir}', "
                f"publishing at {self.rate} Hz on /inspection/image_raw"
            )

        self.idx = 0
        period = 1.0 / self.rate if self.rate > 0 else 2.0
        self.timer = self.create_timer(period, self.tick)

    @staticmethod
    def _gather(image_dir: str) -> list[Path]:
        d = Path(image_dir).expanduser()
        if not d.is_dir():
            return []
        return sorted(p for p in d.rglob("*") if p.suffix.lower() in IMAGE_EXTS)

    def tick(self):
        if not self.images:
            return
        if self.idx >= len(self.images):
            if not self.loop:
                self.get_logger().info("camera_node: reached end of images (loop=False).")
                self.timer.cancel()
                return
            self.idx = 0

        path = self.images[self.idx]
        self.idx += 1

        bgr = cv2.imread(str(path))
        if bgr is None:
            self.get_logger().warn(f"could not read {path}, skipping")
            return

        msg = self.bridge.cv2_to_imgmsg(bgr, encoding="bgr8")
        msg.header.stamp = self.get_clock().now().to_msg()
        # Demo convenience: carry the source filename so the twin can label the part.
        msg.header.frame_id = path.name
        self.publisher.publish(msg)
        self.get_logger().info(f"published part image: {path.name}")


def main(args=None):
    rclpy.init(args=args)
    node = CameraNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
