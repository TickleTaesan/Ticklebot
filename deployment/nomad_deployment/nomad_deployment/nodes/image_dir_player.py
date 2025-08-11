from __future__ import annotations

import os
from typing import List

import numpy as np
from PIL import Image as PILImage

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy

from sensor_msgs.msg import Image


def list_images(directory: str) -> List[str]:
    exts = {'.jpg', '.jpeg', '.png', '.bmp'}
    files = [f for f in os.listdir(directory) if os.path.splitext(f)[1].lower() in exts]
    # numeric sort if possible
    try:
        files = sorted(files, key=lambda x: int(os.path.splitext(x)[0]))
    except Exception:
        files = sorted(files)
    return [os.path.join(directory, f) for f in files]


def pil_to_ros_image(pil_img: PILImage.Image, encoding: str = 'rgb8') -> Image:
    img = np.asarray(pil_img)
    if img.ndim == 2:
        img = np.repeat(img[..., None], 3, axis=2)
    h, w, c = img.shape
    if c == 4:
        img = img[:, :, :3]
        c = 3
    msg = Image()
    msg.height = h
    msg.width = w
    msg.encoding = encoding
    msg.is_bigendian = 0
    msg.step = w * c
    msg.data = img.tobytes()
    return msg


class ImageDirPlayer(Node):
    def __init__(self) -> None:
        super().__init__('image_dir_player')
        self.declare_parameter('dir', '')
        self.declare_parameter('rate', 9.0)
        self.declare_parameter('topic', '/usb_cam/image_raw')
        self.declare_parameter('loop', False)

        self.dir: str = str(self.get_parameter('dir').value)
        self.rate_hz: float = float(self.get_parameter('rate').value)
        self.topic: str = str(self.get_parameter('topic').value)
        self.loop: bool = bool(self.get_parameter('loop').value)

        assert os.path.isdir(self.dir), f'Directory not found: {self.dir}'
        self.images = list_images(self.dir)
        assert len(self.images) > 0, f'No images in: {self.dir}'

        qos = QoSProfile(reliability=ReliabilityPolicy.BEST_EFFORT,
                         history=HistoryPolicy.KEEP_LAST,
                         depth=5)
        self.pub = self.create_publisher(Image, self.topic, qos)

        self.idx = 0
        self.create_timer(1.0 / max(self.rate_hz, 1e-3), self._tick)
        self.get_logger().info(f'Publishing {len(self.images)} images from {self.dir} to {self.topic} at {self.rate_hz} Hz')

    def _tick(self) -> None:
        if self.idx >= len(self.images):
            if self.loop:
                self.idx = 0
            else:
                self.get_logger().info('Finished all images. Stopping node.')
                rclpy.shutdown()
                return
        path = self.images[self.idx]
        pil_img = PILImage.open(path).convert('RGB')
        self.pub.publish(pil_to_ros_image(pil_img, 'rgb8'))
        self.idx += 1


def main() -> None:
    rclpy.init()
    node = ImageDirPlayer()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if rclpy.ok():
            node.destroy_node()
            rclpy.shutdown()


