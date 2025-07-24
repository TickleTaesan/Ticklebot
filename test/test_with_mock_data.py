#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
import numpy as np
import time
import threading
from PIL import Image as PILImage

# ROS2 messages
from sensor_msgs.msg import Image, Joy
from geometry_msgs.msg import Twist
from std_msgs.msg import Float32MultiArray, Bool

# Import utility functions
from nomad_ros2.utils import msg_to_pil, pil_to_msg


class MockCameraNode(Node):
    """Mock camera node that publishes test images"""
    
    def __init__(self):
        super().__init__('mock_camera')
        
        # Create a test image
        self.test_image = self.create_test_image()
        
        # Setup publisher
        qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=1
        )
        
        self.image_pub = self.create_publisher(
            Image,
            '/usb_cam/image_raw',
            qos
        )
        
        # Setup timer to publish images
        self.timer = self.create_timer(0.1, self.publish_image)  # 10 Hz
        
        self.get_logger().info("Mock camera node started")
    
    def create_test_image(self):
        """Create a test image with some patterns"""
        # Create a 640x480 RGB image with some patterns
        img_array = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Add some colored rectangles
        img_array[100:200, 100:300] = [255, 0, 0]  # Red rectangle
        img_array[250:350, 400:600] = [0, 255, 0]  # Green rectangle
        img_array[400:450, 200:400] = [0, 0, 255]  # Blue rectangle
        
        # Add some text-like patterns
        for i in range(0, 640, 50):
            img_array[50:70, i:i+30] = [128, 128, 128]  # Gray bars
        
        return PILImage.fromarray(img_array)
    
    def publish_image(self):
        """Publish the test image"""
        ros_msg = pil_to_msg(self.test_image)
        self.image_pub.publish(ros_msg)


class MockJoystickNode(Node):
    """Mock joystick node that publishes test joystick data"""
    
    def __init__(self):
        super().__init__('mock_joystick')
        
        # Setup publisher
        qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=1
        )
        
        self.joy_pub = self.create_publisher(
            Joy,
            '/joy',
            qos
        )
        
        # Setup timer to publish joystick data
        self.timer = self.create_timer(0.1, self.publish_joystick)  # 10 Hz
        
        # Joystick state
        self.axes = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]  # 6 axes
        self.buttons = [0, 0, 0, 0, 0, 0, 0, 0]     # 8 buttons
        
        self.get_logger().info("Mock joystick node started")
    
    def publish_joystick(self):
        """Publish joystick data"""
        joy_msg = Joy()
        joy_msg.header.stamp = self.get_clock().now().to_msg()
        joy_msg.axes = self.axes
        joy_msg.buttons = self.buttons
        self.joy_pub.publish(joy_msg)
    
    def set_axes(self, axes):
        """Set joystick axes values"""
        self.axes = axes
    
    def set_buttons(self, buttons):
        """Set joystick button values"""
        self.buttons = buttons


class MockRobotNode(Node):
    """Mock robot node that simulates robot movement"""
    
    def __init__(self):
        super().__init__('mock_robot')
        
        # Robot state
        self.x = 0.0
        self.y = 0.0
        self.theta = 0.0
        self.v = 0.0
        self.w = 0.0
        
        # Setup subscriber for velocity commands
        qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=1
        )
        
        self.cmd_vel_sub = self.create_subscription(
            Twist,
            '/cmd_vel',
            self.cmd_vel_callback,
            qos
        )
        
        # Setup timer for robot simulation
        self.timer = self.create_timer(0.05, self.update_robot)  # 20 Hz
        
        self.get_logger().info("Mock robot node started")
    
    def cmd_vel_callback(self, msg):
        """Handle velocity commands"""
        self.v = msg.linear.x
        self.w = msg.angular.z
        
        self.get_logger().info(f"Received velocity command: v={self.v:.2f}, w={self.w:.2f}")
    
    def update_robot(self):
        """Update robot position based on velocity"""
        dt = 0.05  # 20 Hz update rate
        
        # Simple kinematic model
        self.theta += self.w * dt
        self.x += self.v * np.cos(self.theta) * dt
        self.y += self.v * np.sin(self.theta) * dt
        
        # Keep theta in [-pi, pi]
        self.theta = np.arctan2(np.sin(self.theta), np.cos(self.theta))


class TestMonitorNode(Node):
    """Test monitor node that collects and analyzes data"""
    
    def __init__(self):
        super().__init__('test_monitor')
        
        # Data collection
        self.received_images = []
        self.received_waypoints = []
        self.received_velocities = []
        self.received_joystick = []
        
        # Setup subscribers
        qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=10
        )
        
        self.image_sub = self.create_subscription(
            Image,
            '/usb_cam/image_raw',
            self.image_callback,
            qos
        )
        
        self.waypoint_sub = self.create_subscription(
            Float32MultiArray,
            '/waypoint',
            self.waypoint_callback,
            qos
        )
        
        self.cmd_vel_sub = self.create_subscription(
            Twist,
            '/cmd_vel',
            self.cmd_vel_callback,
            qos
        )
        
        self.joy_sub = self.create_subscription(
            Joy,
            '/joy',
            self.joy_callback,
            qos
        )
        
        # Setup timer for monitoring
        self.timer = self.create_timer(1.0, self.print_status)  # 1 Hz
        
        self.get_logger().info("Test monitor node started")
    
    def image_callback(self, msg):
        """Handle received images"""
        self.received_images.append(msg)
        if len(self.received_images) > 100:  # Keep only last 100
            self.received_images.pop(0)
    
    def waypoint_callback(self, msg):
        """Handle received waypoints"""
        self.received_waypoints.append(msg.data)
        if len(self.received_waypoints) > 100:
            self.received_waypoints.pop(0)
    
    def cmd_vel_callback(self, msg):
        """Handle received velocity commands"""
        self.received_velocities.append([msg.linear.x, msg.angular.z])
        if len(self.received_velocities) > 100:
            self.received_velocities.pop(0)
    
    def joy_callback(self, msg):
        """Handle received joystick data"""
        self.received_joystick.append([msg.axes, msg.buttons])
        if len(self.received_joystick) > 100:
            self.received_joystick.pop(0)
    
    def print_status(self):
        """Print current status"""
        self.get_logger().info(
            f"Status - Images: {len(self.received_images)}, "
            f"Waypoints: {len(self.received_waypoints)}, "
            f"Velocities: {len(self.received_velocities)}, "
            f"Joystick: {len(self.received_joystick)}"
        )
    
    def get_statistics(self):
        """Get test statistics"""
        return {
            'images_received': len(self.received_images),
            'waypoints_received': len(self.received_waypoints),
            'velocities_received': len(self.received_velocities),
            'joystick_received': len(self.received_joystick)
        }


def run_mock_test(duration=30):
    """Run a mock test for specified duration"""
    rclpy.init()
    
    try:
        # Create mock nodes
        mock_camera = MockCameraNode()
        mock_joystick = MockJoystickNode()
        mock_robot = MockRobotNode()
        test_monitor = TestMonitorNode()
        
        # Create a thread to simulate joystick input
        def joystick_simulation():
            time.sleep(5)  # Wait for system to start
            
            # Simulate forward movement
            mock_joystick.set_axes([0.5, 0.0, 0.0, 0.0, 0.0, 0.0])  # Forward
            mock_joystick.set_buttons([1, 0, 0, 0, 0, 0, 0, 0])     # Deadman switch
            time.sleep(3)
            
            # Simulate turning
            mock_joystick.set_axes([0.0, 0.3, 0.0, 0.0, 0.0, 0.0])  # Turn right
            time.sleep(2)
            
            # Stop
            mock_joystick.set_axes([0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
            mock_joystick.set_buttons([0, 0, 0, 0, 0, 0, 0, 0])
        
        # Start joystick simulation in a separate thread
        joystick_thread = threading.Thread(target=joystick_simulation)
        joystick_thread.start()
        
        # Run the test
        start_time = time.time()
        while time.time() - start_time < duration:
            rclpy.spin_once(mock_camera, timeout_sec=0.1)
            rclpy.spin_once(mock_joystick, timeout_sec=0.1)
            rclpy.spin_once(mock_robot, timeout_sec=0.1)
            rclpy.spin_once(test_monitor, timeout_sec=0.1)
        
        # Get final statistics
        stats = test_monitor.get_statistics()
        print(f"\nTest completed! Statistics:")
        print(f"Images received: {stats['images_received']}")
        print(f"Waypoints received: {stats['waypoints_received']}")
        print(f"Velocities received: {stats['velocities_received']}")
        print(f"Joystick messages received: {stats['joystick_received']}")
        
        # Cleanup
        mock_camera.destroy_node()
        mock_joystick.destroy_node()
        mock_robot.destroy_node()
        test_monitor.destroy_node()
        
    finally:
        rclpy.shutdown()


if __name__ == '__main__':
    print("Starting mock test...")
    run_mock_test(duration=20)  # Run for 20 seconds 