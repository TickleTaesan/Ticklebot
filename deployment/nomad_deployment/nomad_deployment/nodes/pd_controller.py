from typing import Optional, List

import math
import serial

import rclpy
from rclpy.node import Node

from geometry_msgs.msg import Twist
from std_msgs.msg import Float32MultiArray, Bool


def clip_angle(angle: float) -> float:
    wrapped = (angle + math.pi) % (2.0 * math.pi) - math.pi
    return wrapped


class PDControllerNode(Node):
    def __init__(self) -> None:
        super().__init__('pd_controller')

        # Parameters (defaults match original behavior where possible)
        self.declare_parameter('max_v', 0.4)
        self.declare_parameter('max_w', 0.8)
        self.declare_parameter('frame_rate', 9)
        self.declare_parameter('waypoint_timeout', 1.0)
        self.declare_parameter('vel_topic', '/cmd_vel/nav')

        # Differential drive params
        self.declare_parameter('wheel_separation', 0.26)
        self.declare_parameter('wheel_radius', 0.069)

        # Serial (ODESC) params
        self.declare_parameter('use_serial', True)
        self.declare_parameter('serial_port', '/dev/ttyUSB0')
        self.declare_parameter('baudrate', 115200)

        # Topics
        self.declare_parameter('waypoint_topic', '/waypoint')
        self.declare_parameter('reached_goal_topic', '/topoplan/reached_goal')

        self.max_v: float = float(self.get_parameter('max_v').value)
        self.max_w: float = float(self.get_parameter('max_w').value)
        self.frame_rate: float = float(self.get_parameter('frame_rate').value)
        self.dt: float = 1.0 / max(self.frame_rate, 1e-3)
        self.timeout: float = float(self.get_parameter('waypoint_timeout').value)
        self.vel_topic: str = str(self.get_parameter('vel_topic').value)

        self.L: float = float(self.get_parameter('wheel_separation').value)
        self.R: float = float(self.get_parameter('wheel_radius').value)

        self.use_serial: bool = bool(self.get_parameter('use_serial').value)
        self.serial_port: str = str(self.get_parameter('serial_port').value)
        self.baudrate: int = int(self.get_parameter('baudrate').value)

        self.waypoint_topic: str = str(self.get_parameter('waypoint_topic').value)
        self.reached_goal_topic: str = str(self.get_parameter('reached_goal_topic').value)

        # State
        self._latest_waypoint: Optional[List[float]] = None
        self._latest_waypoint_time = self.get_clock().now()
        self._reached_goal: bool = False
        self._reverse_mode: bool = False

        # Serial init
        self._ser: Optional[serial.Serial] = None
        if self.use_serial:
            try:
                self._ser = serial.Serial(self.serial_port, self.baudrate, timeout=1)
                # Allow device to be ready
                self.get_logger().info(f'Connected to ODESC at {self.serial_port}')
                # Example init (mirror of original intent)
                try:
                    self._ser.write(b"odrv0.axis0.requested_state = 3\n")
                    self._ser.write(b"odrv0.axis1.requested_state = 3\n")
                except Exception as e:
                    self.get_logger().warn(f'ODESC init commands failed: {e}')
            except Exception as e:
                self.get_logger().error(f'Failed to open serial: {e}')
                self._ser = None

        # Pub/Sub
        self.vel_pub = self.create_publisher(Twist, self.vel_topic, 10)
        self.create_subscription(Float32MultiArray, self.waypoint_topic, self._waypoint_cb, 10)
        self.create_subscription(Bool, self.reached_goal_topic, self._reached_goal_cb, 10)

        # Timer loop
        self.create_timer(self.dt, self._control_loop)
        self.get_logger().info('PDControllerNode started')

    # Callbacks
    def _waypoint_cb(self, msg: Float32MultiArray) -> None:
        self._latest_waypoint = list(msg.data)
        self._latest_waypoint_time = self.get_clock().now()

    def _reached_goal_cb(self, msg: Bool) -> None:
        self._reached_goal = bool(msg.data)

    # Core
    def _control_loop(self) -> None:
        cmd = Twist()

        if self._reached_goal:
            self._send_serial_speeds(0.0, 0.0)
            self.vel_pub.publish(cmd)
            return

        if not self._waypoint_valid():
            self.vel_pub.publish(cmd)
            return

        vx, wz = self._pd_from_waypoint(self._latest_waypoint or [])
        if self._reverse_mode:
            vx = -vx

        # Serial drive (optional)
        left, right = self._diff_drive(vx, wz)
        sent = self._send_serial_speeds(left, right)

        # Always publish Twist for observability
        cmd.linear.x = vx
        cmd.angular.z = wz
        self.vel_pub.publish(cmd)

        if self.use_serial and not sent:
            self.get_logger().warn('Failed sending serial ODESC command')

    def _waypoint_valid(self) -> bool:
        if self._latest_waypoint is None:
            return False
        age = (self.get_clock().now() - self._latest_waypoint_time).nanoseconds / 1e9
        if age > self.timeout:
            return False
        n = len(self._latest_waypoint)
        return n in (2, 4)

    def _pd_from_waypoint(self, waypoint: List[float]) -> (float, float):
        # waypoint: [dx, dy] or [dx, dy, hx, hy]
        eps = 1e-8
        if len(waypoint) == 2:
            dx, dy = waypoint
            hx = hy = 0.0
        else:
            dx, dy, hx, hy = waypoint

        if len(waypoint) == 4 and abs(dx) < eps and abs(dy) < eps:
            v = 0.0
            w = clip_angle(math.atan2(hy, hx)) / self.dt
        elif abs(dx) < eps:
            v = 0.0
            w = math.copysign(math.pi / (2.0 * self.dt), dy)
        else:
            v = dx / self.dt
            w = math.atan(dy / dx) / self.dt

        v = max(0.0, min(self.max_v, v))
        w = max(-self.max_w, min(self.max_w, w))
        return v, w

    def _diff_drive(self, v: float, w: float) -> (float, float):
        # v_left = v - (w * L) / 2
        # v_right = v + (w * L) / 2
        left = v - (w * self.L) / 2.0
        right = v + (w * self.L) / 2.0
        return left, right

    def _send_serial_speeds(self, v_left: float, v_right: float) -> bool:
        if not self.use_serial or self._ser is None:
            return False if self.use_serial else True
        try:
            # Convert linear m/s at wheel rim to RPM
            # RPM = (linear_speed / (2*pi*R)) * 60
            left_rpm = int((v_left / (2.0 * math.pi * self.R)) * 60.0)
            right_rpm = int((v_right / (2.0 * math.pi * self.R)) * 60.0)
            self._ser.write(f"odrv0.axis0.controller.vel_setpoint = {left_rpm}\n".encode())
            self._ser.write(f"odrv0.axis1.controller.vel_setpoint = {right_rpm}\n".encode())
            return True
        except Exception as e:
            self.get_logger().error(f'ODESC write failed: {e}')
            return False

    def destroy_node(self):
        try:
            if self._ser is not None:
                # Stop wheels
                try:
                    self._ser.write(b"odrv0.axis0.controller.vel_setpoint = 0\n")
                    self._ser.write(b"odrv0.axis1.controller.vel_setpoint = 0\n")
                except Exception:
                    pass
                self._ser.close()
        finally:
            super().destroy_node()


def main() -> None:
    rclpy.init()
    node = PDControllerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


