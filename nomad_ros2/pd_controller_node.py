#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
import numpy as np
import yaml
from typing import Tuple
import time

# ROS2
from geometry_msgs.msg import Twist
from std_msgs.msg import Float32MultiArray, Bool

from .topic_names import (WAYPOINT_TOPIC, 
                         GOAL_REACHED_TOPIC,
                         ROBOT_CMD_VEL_TOPIC)

# CONSTANTS
CONFIG_PATH = "../config/robot.yaml"
with open(CONFIG_PATH, "r") as f:
    robot_config = yaml.safe_load(f)
MAX_V = robot_config["max_v"]
MAX_W = robot_config["max_w"]
VEL_TOPIC = robot_config["vel_navi_topic"]
DT = 1/robot_config["frame_rate"]
RATE = 9
EPS = 1e-8
WAYPOINT_TIMEOUT = 1  # seconds
FLIP_ANG_VEL = np.pi/4


class ROS2Data:
    """ROS2 compatible data wrapper with timeout functionality"""
    def __init__(self, timeout: int = 3, queue_size: int = 1, name: str = ""):
        self.timeout = timeout
        self.last_time_received = float("-inf")
        self.queue_size = queue_size
        self.data = None
        self.name = name
        self.phantom = False
    
    def get(self):
        return self.data
    
    def set(self, data): 
        time_waited = time.time() - self.last_time_received
        if self.queue_size == 1:
            self.data = data
        else:
            if self.data is None or time_waited > self.timeout:  # reset queue if timeout
                self.data = []
            if len(self.data) == self.queue_size:
                self.data.pop(0)
            self.data.append(data)
        self.last_time_received = time.time()
        
    def is_valid(self, verbose: bool = False):
        time_waited = time.time() - self.last_time_received
        valid = time_waited < self.timeout
        if self.queue_size > 1:
            valid = valid and len(self.data) == self.queue_size
        if verbose and not valid:
            print(f"Not receiving {self.name} data for {time_waited} seconds (timeout: {self.timeout} seconds)")
        return valid


def clip_angle(theta) -> float:
    """Clip angle to [-pi, pi]"""
    theta %= 2 * np.pi
    if -np.pi < theta < np.pi:
        return theta
    return theta - 2 * np.pi


def pd_controller(waypoint: np.ndarray) -> Tuple[float]:
    """PD controller for the robot"""
    assert len(waypoint) == 2 or len(waypoint) == 4, "waypoint must be a 2D or 4D vector"
    if len(waypoint) == 2:
        dx, dy = waypoint
    else:
        dx, dy, hx, hy = waypoint
    
    # this controller only uses the predicted heading if dx and dy near zero
    if len(waypoint) == 4 and np.abs(dx) < EPS and np.abs(dy) < EPS:
        v = 0
        w = clip_angle(np.arctan2(hy, hx))/DT        
    elif np.abs(dx) < EPS:
        v = 0
        w = np.sign(dy) * np.pi/(2*DT)
    else:
        v = dx / DT
        w = np.arctan(dy/dx) / DT
    
    v = np.clip(v, 0, MAX_V)
    w = np.clip(w, -MAX_W, MAX_W)
    return v, w


class PDControllerNode(Node):
    def __init__(self):
        super().__init__('pd_controller_node')
        
        # Initialize data structures
        self.vel_msg = Twist()
        self.waypoint = ROS2Data(WAYPOINT_TIMEOUT, name="waypoint")
        self.reached_goal = False
        self.reverse_mode = False
        self.current_yaw = None
        
        # Setup ROS2 interface
        self.setup_ros2_interface()
        
        # Setup timer for control loop
        self.timer = self.create_timer(1.0 / RATE, self.control_loop)
        
        self.get_logger().info("PD Controller node initialized successfully")
    
    def setup_ros2_interface(self):
        """Setup ROS2 publishers and subscribers"""
        # QoS profile for real-time data
        qos_profile = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=1
        )
        
        # Subscribers
        self.waypoint_sub = self.create_subscription(
            Float32MultiArray,
            WAYPOINT_TOPIC,
            self.callback_drive,
            qos_profile
        )
        
        self.reached_goal_sub = self.create_subscription(
            Bool,
            GOAL_REACHED_TOPIC,
            self.callback_reached_goal,
            qos_profile
        )
        
        # Publishers
        self.vel_out = self.create_publisher(
            Twist,
            VEL_TOPIC,
            1
        )
        
        self.get_logger().info("ROS2 interface setup complete")
    
    def callback_drive(self, waypoint_msg: Float32MultiArray):
        """Callback function for the waypoint subscriber"""
        self.get_logger().info("Setting waypoint")
        self.waypoint.set(waypoint_msg.data)
    
    def callback_reached_goal(self, reached_goal_msg: Bool):
        """Callback function for the reached goal subscriber"""
        self.reached_goal = reached_goal_msg.data
    
    def control_loop(self):
        """Main control loop"""
        self.vel_msg = Twist()
        
        if self.reached_goal:
            self.vel_out.publish(self.vel_msg)
            self.get_logger().info("Reached goal! Stopping...")
            self.timer.cancel()
            return
        elif self.waypoint.is_valid(verbose=True):
            v, w = pd_controller(self.waypoint.get())
            if self.reverse_mode:
                v *= -1
            self.vel_msg.linear.x = v
            self.vel_msg.angular.z = w
            self.get_logger().info(f"Publishing new vel: {v}, {w}")
        
        self.vel_out.publish(self.vel_msg)


def main(args=None):
    rclpy.init(args=args)
    
    try:
        node = PDControllerNode()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main() 