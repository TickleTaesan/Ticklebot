from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import List

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy

from std_msgs.msg import Float32MultiArray
from sensor_msgs.msg import Image


def get_repo_root() -> Path:
    here = Path(__file__).resolve()
    for p in [here.parents[4], *here.parents]:
        if (p / 'train' / 'config').exists() and (p / 'deployment' / 'src').exists():
            return p
    env = os.getenv('NOMAD_ROOT')
    if env:
        return Path(env).expanduser().resolve()
    return here.parents[4]


REPO_ROOT = get_repo_root()
sys.path.insert(0, str(REPO_ROOT / 'deployment' / 'src'))

try:
    from topic_names import IMAGE_TOPIC, WAYPOINT_TOPIC  # type: ignore
except Exception:
    IMAGE_TOPIC = '/usb_cam/image_raw'
    WAYPOINT_TOPIC = '/waypoint'


class ExploreDummyNode(Node):
    def __init__(self) -> None:
        super().__init__('explore_dummy')

        # Parameters
        self.declare_parameter('dx', 0.05)
        self.declare_parameter('dy', 0.0)
        self.declare_parameter('rate', 9.0)
        self.declare_parameter('waypoint_topic', WAYPOINT_TOPIC)
        self.dx: float = float(self.get_parameter('dx').value)
        self.dy: float = float(self.get_parameter('dy').value)
        self.rate_hz: float = float(self.get_parameter('rate').value)
        self.waypoint_topic: str = str(self.get_parameter('waypoint_topic').value)

        # I/O
        self.waypoint_pub = self.create_publisher(Float32MultiArray, self.waypoint_topic, 10)

        # Optional subscribe to image for debug (won't fail if no camera)
        sensor_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=5,
        )
        self.create_subscription(Image, IMAGE_TOPIC, self._image_cb, sensor_qos)

        # Timer
        self.create_timer(1.0 / max(self.rate_hz, 1e-3), self._tick)
        self.get_logger().info(f'ExploreDummyNode started (publishing to {self.waypoint_topic})')

    def _image_cb(self, msg: Image) -> None:
        # No-op; just confirms subscription is wired
        pass

    def _tick(self) -> None:
        msg = Float32MultiArray()
        msg.data = [self.dx, self.dy]
        self.waypoint_pub.publish(msg)
        self.get_logger().info(f'Published dummy waypoint: {msg.data}')


def main() -> None:
    rclpy.init()
    node = ExploreDummyNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


