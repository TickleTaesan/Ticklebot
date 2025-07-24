#!/usr/bin/env python3

import pytest
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
import numpy as np
import time
import threading

# Import the nodes to test
from nomad_ros2.pd_controller_node import PDControllerNode, pd_controller, clip_angle
from nomad_ros2.joy_teleop_node import JoyTeleopNode
from nomad_ros2.utils import msg_to_pil, pil_to_msg, setup_ros2_qos

# ROS2 messages
from sensor_msgs.msg import Image, Joy
from geometry_msgs.msg import Twist
from std_msgs.msg import Float32MultiArray, Bool


class TestPDController:
    """Test PD Controller functionality"""
    
    def test_clip_angle(self):
        """Test angle clipping function"""
        # Test normal angles
        assert abs(clip_angle(0.5) - 0.5) < 1e-6
        assert abs(clip_angle(-0.5) - (-0.5)) < 1e-6
        
        # Test angles outside [-pi, pi]
        assert abs(clip_angle(2 * np.pi + 0.5) - 0.5) < 1e-6
        assert abs(clip_angle(-2 * np.pi - 0.5) - (-0.5)) < 1e-6
        
        # Test edge cases
        assert abs(clip_angle(np.pi) - np.pi) < 1e-6
        assert abs(clip_angle(-np.pi) - (-np.pi)) < 1e-6
    
    def test_pd_controller_2d_waypoint(self):
        """Test PD controller with 2D waypoint"""
        waypoint = np.array([1.0, 0.5])
        v, w = pd_controller(waypoint)
        
        # Check that outputs are within expected ranges
        assert 0 <= v <= 0.5  # MAX_V from config
        assert -0.8 <= w <= 0.8  # MAX_W from config
        
        # Check that outputs are reasonable
        assert v > 0  # Should move forward for positive x
        assert abs(w) < np.pi/2  # Should not turn too sharply
    
    def test_pd_controller_4d_waypoint(self):
        """Test PD controller with 4D waypoint (including heading)"""
        waypoint = np.array([0.0, 0.0, 1.0, 0.0])  # No displacement, heading right
        v, w = pd_controller(waypoint)
        
        # Should not move forward when dx=dy=0
        assert v == 0
        # Should turn based on heading
        assert w != 0


class TestJoyTeleop:
    """Test Joy Teleop functionality"""
    
    def test_joy_callback(self):
        """Test joystick callback processing"""
        # This would require a more complex setup with actual ROS2 nodes
        # For now, we'll test the logic separately
        pass


class TestUtils:
    """Test utility functions"""
    
    def test_setup_ros2_qos(self):
        """Test QoS profile setup"""
        qos = setup_ros2_qos(reliability='best_effort', history='keep_last', depth=5)
        
        assert qos.reliability == ReliabilityPolicy.BEST_EFFORT
        assert qos.history == HistoryPolicy.KEEP_LAST
        assert qos.depth == 5
    
    def test_image_conversion(self):
        """Test image message conversion"""
        # Create a simple test image
        from PIL import Image as PILImage
        import numpy as np
        
        # Create a 100x100 RGB test image
        test_array = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        pil_img = PILImage.fromarray(test_array)
        
        # Convert to ROS2 message
        ros_msg = pil_to_msg(pil_img)
        
        # Convert back to PIL
        converted_pil = msg_to_pil(ros_msg)
        
        # Check that the images are similar (allowing for encoding differences)
        original_array = np.array(pil_img)
        converted_array = np.array(converted_pil)
        
        # The images should have the same shape
        assert original_array.shape == converted_array.shape


class TestNodeIntegration:
    """Integration tests for ROS2 nodes"""
    
    @pytest.fixture(autouse=True)
    def setup_rclpy(self):
        """Setup and teardown rclpy for each test"""
        rclpy.init()
        yield
        rclpy.shutdown()
    
    def test_pd_controller_node_creation(self):
        """Test that PD controller node can be created"""
        try:
            node = PDControllerNode()
            assert node is not None
            assert node.get_name() == 'pd_controller_node'
        finally:
            if 'node' in locals():
                node.destroy_node()
    
    def test_joy_teleop_node_creation(self):
        """Test that Joy teleop node can be created"""
        try:
            node = JoyTeleopNode()
            assert node is not None
            assert node.get_name() == 'joy_teleop_node'
        finally:
            if 'node' in locals():
                node.destroy_node()


class TestTopicCommunication:
    """Test topic communication between nodes"""
    
    @pytest.fixture(autouse=True)
    def setup_rclpy(self):
        """Setup and teardown rclpy for each test"""
        rclpy.init()
        yield
        rclpy.shutdown()
    
    def test_waypoint_topic_communication(self):
        """Test waypoint topic communication"""
        # Create a simple test node to publish waypoints
        test_node = Node('test_publisher')
        
        # Create publisher
        qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=1
        )
        
        pub = test_node.create_publisher(Float32MultiArray, '/waypoint', qos)
        
        # Create subscriber to receive messages
        received_messages = []
        
        def callback(msg):
            received_messages.append(msg.data)
        
        sub = test_node.create_subscription(
            Float32MultiArray, '/waypoint', callback, qos
        )
        
        # Publish a test waypoint
        test_waypoint = Float32MultiArray()
        test_waypoint.data = [1.0, 0.5]
        pub.publish(test_waypoint)
        
        # Give some time for message to be processed
        time.sleep(0.1)
        
        # Spin once to process callbacks
        rclpy.spin_once(test_node, timeout_sec=0.1)
        
        # Check that message was received
        assert len(received_messages) > 0
        assert len(received_messages[0]) == 2
        assert received_messages[0][0] == 1.0
        assert received_messages[0][1] == 0.5
        
        test_node.destroy_node()


if __name__ == '__main__':
    pytest.main([__file__]) 