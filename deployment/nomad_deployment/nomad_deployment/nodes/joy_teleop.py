from typing import Optional

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy

from geometry_msgs.msg import Twist
from sensor_msgs.msg import Joy
from std_msgs.msg import Bool


class JoyTeleopNode(Node):
    def __init__(self) -> None:
        super().__init__('joy_teleop')

        # Parameters
        self.declare_parameter('max_v', 0.4)
        self.declare_parameter('max_w', 0.8)
        self.declare_parameter('deadman_switch', 4)  # example index
        self.declare_parameter('lin_vel_axis', 1)
        self.declare_parameter('ang_vel_axis', 0)
        self.declare_parameter('publish_rate', 9.0)
        self.declare_parameter('vel_topic', '/cmd_vel/teleop')
        self.declare_parameter('joy_bumper_topic', '/joy_bumper')

        self.max_v: float = float(self.get_parameter('max_v').value)
        self.max_w: float = float(self.get_parameter('max_w').value)
        self.deadman_switch: int = int(self.get_parameter('deadman_switch').value)
        self.lin_axis: int = int(self.get_parameter('lin_vel_axis').value)
        self.ang_axis: int = int(self.get_parameter('ang_vel_axis').value)
        self.publish_rate: float = float(self.get_parameter('publish_rate').value)
        self.vel_topic: str = str(self.get_parameter('vel_topic').value)
        self.joy_bumper_topic: str = str(self.get_parameter('joy_bumper_topic').value)

        # QoS for sensors
        sensor_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=5,
        )

        # Publishers
        self.vel_pub = self.create_publisher(Twist, self.vel_topic, 10)
        self.bumper_pub = self.create_publisher(Bool, self.joy_bumper_topic, 10)

        # State
        self.button_pressed: bool = False
        self.bumper: bool = False
        self.current_cmd: Twist = Twist()

        # Subscriber
        self.create_subscription(Joy, 'joy', self.joy_callback, sensor_qos)

        # Timer for publishing
        self.create_timer(1.0 / max(self.publish_rate, 1e-3), self.timer_cb)

        self.get_logger().info('JoyTeleopNode started')

    def joy_callback(self, msg: Joy) -> None:
        try:
            self.button_pressed = bool(msg.buttons[self.deadman_switch])
        except Exception:
            self.button_pressed = False

        # Optional: use previous index as bumper
        try:
            self.bumper = bool(msg.buttons[max(self.deadman_switch - 1, 0)])
        except Exception:
            self.bumper = False

        if self.button_pressed:
            vx = self.max_v * float(msg.axes[self.lin_axis]) if len(msg.axes) > self.lin_axis else 0.0
            wz = self.max_w * float(msg.axes[self.ang_axis]) if len(msg.axes) > self.ang_axis else 0.0
            self.current_cmd.linear.x = vx
            self.current_cmd.angular.z = wz
        else:
            self.current_cmd = Twist()

    def timer_cb(self) -> None:
        # Publish teleop velocity
        self.vel_pub.publish(self.current_cmd)

        # Publish bumper state
        bumper_msg = Bool()
        bumper_msg.data = self.bumper
        self.bumper_pub.publish(bumper_msg)


def main() -> None:
    rclpy.init()
    node = JoyTeleopNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


