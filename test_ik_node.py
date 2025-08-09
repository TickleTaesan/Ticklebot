#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
import geometry_msgs.msg
import time

class IKTester(Node):
    def __init__(self):
        super().__init__('ik_tester')
        
        # Publishers for both arms
        self.right_pub = self.create_publisher(
            geometry_msgs.msg.PoseStamped, 
            '/right/goal_pose', 
            10
        )
        self.left_pub = self.create_publisher(
            geometry_msgs.msg.PoseStamped, 
            '/left/goal_pose', 
            10
        )
        
        # Wait for publishers to be ready
        time.sleep(1)
        
        self.get_logger().info('IK Tester ready. Testing both arms...')
        
        # Test poses within conservative workspace bounds
        self.test_poses()
        
    def test_poses(self):
        """Test with safe poses within workspace bounds"""
        
        test_poses = [
            # Conservative poses within bounds: x=[-0.4, 0.4], y=[-0.4, 0.4], z=[0.15, 0.8]
            {"name": "Center Low", "x": 0.0, "y": 0.0, "z": 0.3},
            {"name": "Center Mid", "x": 0.0, "y": 0.0, "z": 0.5},
            {"name": "Right Side", "x": 0.2, "y": 0.2, "z": 0.4},
            {"name": "Left Side", "x": 0.2, "y": -0.2, "z": 0.4},
            {"name": "Forward", "x": 0.3, "y": 0.0, "z": 0.4},
        ]
        
        for i, pose_data in enumerate(test_poses):
            self.get_logger().info(f'Testing pose {i+1}: {pose_data["name"]}')
            
            # Create pose message
            pose_msg = geometry_msgs.msg.PoseStamped()
            pose_msg.header.frame_id = "base_link"
            pose_msg.header.stamp = self.get_clock().now().to_msg()
            
            # Position
            pose_msg.pose.position.x = pose_data["x"]
            pose_msg.pose.position.y = pose_data["y"] 
            pose_msg.pose.position.z = pose_data["z"]
            
            # Simple downward orientation (gripper pointing down)
            pose_msg.pose.orientation.x = 0.0
            pose_msg.pose.orientation.y = 0.707  # 90 degrees around Y axis
            pose_msg.pose.orientation.z = 0.0
            pose_msg.pose.orientation.w = 0.707
            
            # Test right arm
            self.get_logger().info(f'  → Testing RIGHT arm with pose: ({pose_data["x"]}, {pose_data["y"]}, {pose_data["z"]})')
            self.right_pub.publish(pose_msg)
            time.sleep(3)  # Wait for IK processing
            
            # Test left arm (mirror Y coordinate)
            pose_msg.pose.position.y = -pose_data["y"]  # Mirror for left arm
            self.get_logger().info(f'  → Testing LEFT arm with pose: ({pose_data["x"]}, {-pose_data["y"]}, {pose_data["z"]})')
            self.left_pub.publish(pose_msg)
            time.sleep(3)  # Wait for IK processing
            
        self.get_logger().info('All test poses completed!')

def main():
    rclpy.init()
    
    tester = IKTester()
    
    # Keep the node alive for a bit
    rclpy.spin_once(tester, timeout_sec=1.0)
    
    tester.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main() 