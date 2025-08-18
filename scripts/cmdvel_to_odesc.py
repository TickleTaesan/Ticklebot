#!/usr/bin/env python3
import math, time, yaml, serial
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist

CONFIG_PATH = "config/robot.yaml"

with open(CONFIG_PATH, "r") as f:
    C = yaml.safe_load(f)

R = C.get("wheel_radius", 0.05)             # [m]
L = C.get("wheel_separation", 0.30)         # [m]
N = C.get("gear_ratio", 1.0)                 # motor:wheel
PORT = C.get("uart_port", "/dev/ttyUSB0")
BAUD = C.get("uart_baud", 115200)
VEL_TOPIC = C.get("vel_navi_topic", "/cmd_vel")

LEFT_ID  = int(C.get("left_motor_index", 0))
RIGHT_ID = int(C.get("right_motor_index", 1))
INV_L = bool(C.get("invert_left", False))
INV_R = bool(C.get("invert_right", False))
MAX_TURNS = float(C.get("motor_max_turns", 20.0))
WATCHDOG = float(C.get("watchdog_timeout", 0.5))

class CmdVelToOdesc(Node):
    def __init__(self):
        super().__init__('cmdvel_to_odesc')
        self.ser = serial.Serial(PORT, baudrate=BAUD, timeout=0.02)
        self.get_logger().info(f"Opened {PORT} @ {BAUD}")
        self.last_cmd_time = time.time()
        self.sub = self.create_subscription(Twist, VEL_TOPIC, self.cb, 20)
        self.timer = self.create_timer(0.05, self.on_timer)  # 20Hz keepalive

    def cb(self, msg: Twist):
        v = msg.linear.x
        w = msg.angular.z
        # (v, ω) → 바퀴 각속도[rad/s]
        wl = (v - w * L/2.0) / R
        wr = (v + w * L/2.0) / R
        # 바퀴[rad/s] → 모터축[turn/s] (감속비 반영)
        ml = (wl * N) / (2.0*math.pi)
        mr = (wr * N) / (2.0*math.pi)

        if INV_L: ml = -ml
        if INV_R: mr = -mr

        # 한계 걸기 (ODrive vel_limit와 일치 또는 더 낮게)
        ml = max(-MAX_TURNS, min(MAX_TURNS, ml))
        mr = max(-MAX_TURNS, min(MAX_TURNS, mr))

        self._send_v(LEFT_ID,  ml)
        self._send_v(RIGHT_ID, mr)
        self.last_cmd_time = time.time()

    def _send_v(self, motor_idx: int, turns_per_s: float):
        # ODrive/ODESC ASCII: v <axis> <turns/s> [torque_ff]
        cmd = f"v {motor_idx} {turns_per_s:.6f}\n"
        try:
            self.ser.write(cmd.encode("ascii"))
        except Exception as e:
            self.get_logger().error(f"UART write failed: {e}")

    def on_timer(self):
        # /cmd_vel 미수신 시 정지 (워치독)
        if (time.time() - self.last_cmd_time) > WATCHDOG:
            self._send_v(LEFT_ID,  0.0)
            self._send_v(RIGHT_ID, 0.0)

def main():
    rclpy.init()
    node = CmdVelToOdesc()
    try:
        rclpy.spin(node)
    finally:
        try:
            node._send_v(LEFT_ID,  0.0)
            node._send_v(RIGHT_ID, 0.0)
        except Exception:
            pass
        node.destroy_node()
        rclpy.shutdown()

if __name__ == "__main__":
    main()
