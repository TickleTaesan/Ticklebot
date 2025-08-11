from __future__ import annotations

import os
import shutil
from pathlib import Path

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy

from sensor_msgs.msg import Image

from PIL import Image as PILImage
import numpy as np


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


def msg_to_pil(msg: Image) -> PILImage.Image:
    # Minimal reimplementation to avoid importing original utils
    arr = np.frombuffer(msg.data, dtype=np.uint8)
    c = 3 if msg.step == msg.width * 3 else 1
    try:
        img = arr.reshape((msg.height, msg.width, -1))
    except Exception:
        img = arr.reshape((msg.height, msg.width, c))
    return PILImage.fromarray(img)


class CreateTopomapNode(Node):
    def __init__(self) -> None:
        super().__init__('create_topomap')

        # Parameters
        self.declare_parameter('dir', 'topomap')
        self.declare_parameter('dt', 1.0)
        self.declare_parameter('image_topic', '/usb_cam/image_raw')
        default_out = str(REPO_ROOT / 'deployment' / 'topomaps' / 'images')
        self.declare_parameter('output_root', default_out)

        self.dir_name: str = str(self.get_parameter('dir').value)
        self.dt: float = float(self.get_parameter('dt').value)
        self.image_topic: str = str(self.get_parameter('image_topic').value)
        self.output_root: str = str(self.get_parameter('output_root').value)

        # Prepare output dir
        self.topomap_dir = Path(self.output_root) / self.dir_name
        self.topomap_dir.mkdir(parents=True, exist_ok=True)
        # Clean existing
        for f in self.topomap_dir.iterdir():
            if f.is_file() or f.is_symlink():
                f.unlink()
            elif f.is_dir():
                shutil.rmtree(f)

        # QoS for sensors
        sensor_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=5,
        )
        self.create_subscription(Image, self.image_topic, self._image_cb, sensor_qos)

        # State
        self._latest: PILImage.Image | None = None
        self._idx: int = 0

        # Timer
        self.create_timer(max(self.dt, 1e-3), self._tick)
        self.get_logger().info(f'Saving images every {self.dt}s to {self.topomap_dir}')

    def _image_cb(self, msg: Image) -> None:
        self._latest = msg_to_pil(msg)

    def _tick(self) -> None:
        if self._latest is None:
            return
        out = self.topomap_dir / f'{self._idx}.png'
        try:
            self._latest.save(out)
            self.get_logger().info(f'saved {out.name}')
            self._idx += 1
        except Exception as e:
            self.get_logger().error(f'failed to save image: {e}')


def main() -> None:
    rclpy.init()
    node = CreateTopomapNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


