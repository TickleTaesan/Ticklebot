#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
import argparse
import os
import shutil
import time

# ROS2
from sensor_msgs.msg import Image, Joy

# Import from original utils (will be converted later)
import sys
sys.path.append('../deployment/src')
from utils import msg_to_pil

from .topic_names import IMAGE_TOPIC, JOY_TOPIC

# CONSTANTS
TOPOMAP_IMAGES_DIR = "../topomaps/images"


def remove_files_in_dir(dir_path: str):
    """Remove all files in a directory"""
    for f in os.listdir(dir_path):
        file_path = os.path.join(dir_path, f)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print("Failed to delete %s. Reason: %s" % (file_path, e))


class CreateTopomapNode(Node):
    def __init__(self, args):
        super().__init__('create_topomap_node')
        
        # Initialize variables
        self.obs_img = None
        self.args = args
        self.i = 0
        self.start_time = float("inf")
        self.last_image_time = 0
        
        # Setup topomap directory
        self.topomap_name_dir = os.path.join(TOPOMAP_IMAGES_DIR, args.dir)
        if not os.path.isdir(self.topomap_name_dir):
            os.makedirs(self.topomap_name_dir)
        else:
            self.get_logger().info(f"{self.topomap_name_dir} already exists. Removing previous images...")
            remove_files_in_dir(self.topomap_name_dir)
        
        assert args.dt > 0, "dt must be positive"
        
        # Setup ROS2 interface
        self.setup_ros2_interface()
        
        # Setup timer for image processing
        self.timer = self.create_timer(args.dt, self.process_image)
        
        self.get_logger().info("Create Topomap node initialized successfully")
    
    def setup_ros2_interface(self):
        """Setup ROS2 publishers and subscribers"""
        # QoS profile for real-time data
        qos_profile = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=1
        )
        
        # Subscribers
        self.image_sub = self.create_subscription(
            Image,
            IMAGE_TOPIC,
            self.callback_obs,
            qos_profile
        )
        
        self.joy_sub = self.create_subscription(
            Joy,
            JOY_TOPIC,
            self.callback_joy,
            qos_profile
        )
        
        # Publishers
        self.subgoals_pub = self.create_publisher(
            Image,
            "/subgoals",
            1
        )
        
        self.get_logger().info("ROS2 interface setup complete")
    
    def callback_obs(self, msg: Image):
        """Callback for image observations"""
        self.obs_img = msg_to_pil(msg)
        self.last_image_time = time.time()
    
    def callback_joy(self, msg: Joy):
        """Callback for joystick input"""
        if msg.buttons[0]:
            self.get_logger().info("Joystick button pressed. Shutting down...")
            rclpy.shutdown()
    
    def process_image(self):
        """Process and save image at regular intervals"""
        current_time = time.time()
        
        # Check if we're receiving images
        if current_time - self.last_image_time > 2 * self.args.dt:
            self.get_logger().info(f"Topic {IMAGE_TOPIC} not publishing anymore. Shutting down...")
            rclpy.shutdown()
            return
        
        if self.obs_img is not None:
            # Save image
            image_path = os.path.join(self.topomap_name_dir, f"{self.i}.png")
            self.obs_img.save(image_path)
            self.get_logger().info(f"Saved image {self.i}")
            
            # Publish to subgoals topic (optional)
            # self.subgoals_pub.publish(self.obs_img)
            
            self.i += 1
            self.obs_img = None
            self.start_time = current_time


def main(args=None):
    rclpy.init(args=args)
    
    # Parse arguments (simplified for ROS2)
    parser = argparse.ArgumentParser(
        description=f"Code to generate topomaps from the {IMAGE_TOPIC} topic"
    )
    parser.add_argument("--dir", "-d", default="topomap", type=str,
                       help="path to topological map images in ../topomaps/images directory")
    parser.add_argument("--dt", "-t", default=1.0, type=float,
                       help=f"time between images sampled from the {IMAGE_TOPIC} topic")
    
    # For ROS2, we'll use default arguments for now
    # In a real implementation, you'd get these from ROS2 parameters
    args = parser.parse_args([])  # Empty list for default values
    
    try:
        node = CreateTopomapNode(args)
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main() 