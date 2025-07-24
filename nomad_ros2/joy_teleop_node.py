#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
import yaml

# ROS2
from geometry_msgs.msg import Twist
from sensor_msgs.msg import Joy
from std_msgs.msg import Bool

from .topic_names import (JOY_TOPIC,
                         ROBOT_CMD_VEL_TOPIC)

# CONSTANTS
CONFIG_PATH = "../config/robot.yaml"
with open(CONFIG_PATH, "r") as f:
    robot_config = yaml.safe_load(f)
MAX_V = 0.4
MAX_W = 0.8
VEL_TOPIC = robot_config["vel_teleop_topic"]
JOY_CONFIG_PATH = "../config/joystick.yaml"
with open(JOY_CONFIG_PATH, "r") as f:
    joy_config = yaml.safe_load(f)
DEADMAN_SWITCH = joy_config["deadman_switch"]  # button index
LIN_VEL_BUTTON = joy_config["lin_vel_button"]
ANG_VEL_BUTTON = joy_config["ang_vel_button"]
RATE = 9


class JoyTeleopNode(Node):
    def __init__(self):
        super().__init__('joy_teleop_node')
        
        # Initialize variables
        self.vel_msg = Twist()
        self.button = None
        self.bumper = False
        
        # Setup ROS2 interface
        self.setup_ros2_interface()
        
        # Setup timer for teleop loop
        self.timer = self.create_timer(1.0 / RATE, self.teleop_loop)
        
        self.get_logger().info("Joy Teleop node initialized successfully")
    
    def setup_ros2_interface(self):
        """Setup ROS2 publishers and subscribers"""
        # QoS profile for real-time data
        qos_profile = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=1
        )
        
        # Subscribers
        self.joy_sub = self.create_subscription(
            Joy,
            JOY_TOPIC,
            self.callback_joy,
            qos_profile
        )
        
        # Publishers
        self.vel_pub = self.create_publisher(
            Twist,
            VEL_TOPIC,
            1
        )
        
        self.bumper_pub = self.create_publisher(
            Bool,
            "/joy_bumper",  # Using the same topic name as original
            1
        )
        
        self.get_logger().info("ROS2 interface setup complete")
    
    def callback_joy(self, data: Joy):
        """Callback function for the joystick subscriber"""
        self.button = data.buttons[DEADMAN_SWITCH] 
        bumper_button = data.buttons[DEADMAN_SWITCH - 1]
        
        if self.button is not None:  # hold down the dead-man switch to teleop the robot
            self.vel_msg.linear.x = MAX_V * data.axes[LIN_VEL_BUTTON]
            self.vel_msg.angular.z = MAX_W * data.axes[ANG_VEL_BUTTON]    
        else:
            self.vel_msg = Twist()
            self.vel_pub.publish(self.vel_msg)
        
        if bumper_button is not None:
            self.bumper = bool(data.buttons[DEADMAN_SWITCH - 1])
        else:
            self.bumper = False
    
    def teleop_loop(self):
        """Main teleop loop"""
        if self.button:
            self.get_logger().info(f"Teleoperating the robot: {self.vel_msg}")
            self.vel_pub.publish(self.vel_msg)
        
        bumper_msg = Bool()
        bumper_msg.data = self.bumper
        self.bumper_pub.publish(bumper_msg)
        
        if self.bumper:
            self.get_logger().info("Bumper pressed!")


def main(args=None):
    rclpy.init(args=args)
    
    try:
        node = JoyTeleopNode()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main() 