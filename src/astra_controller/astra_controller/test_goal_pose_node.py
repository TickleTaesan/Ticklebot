#!/usr/bin/env python3
"""
test_goal_pose_node.py
간단한 테스트 자세를 발행하는 노드
"""

import rclpy
import rclpy.node
from geometry_msgs.msg import PoseStamped
import math
import time

def main(args=None):
    rclpy.init(args=args)
    node = rclpy.node.Node('test_goal_pose_node')
    
    # Publishers for left and right arms
    left_pub = node.create_publisher(PoseStamped, 'left/goal_pose', 10)
    right_pub = node.create_publisher(PoseStamped, 'right/goal_pose', 10)
    
    def publish_test_pose():
        # Create test pose message for left arm
        left_msg = PoseStamped()
        left_msg.header.stamp = node.get_clock().now().to_msg()
        left_msg.header.frame_id = 'base_link'  # Planning frame
        
        # Set position for left arm (initial + 1cm forward only)
        left_msg.pose.position.x = 0.249  # 0.239 + 0.01 (forward)
        left_msg.pose.position.y = 0.130  # same Y position
        left_msg.pose.position.z = 0.324  # same height
        
        # Set orientation same as initial state (exact match)
        left_msg.pose.orientation.w = 0.5
        left_msg.pose.orientation.x = 0.5
        left_msg.pose.orientation.y = -0.5
        left_msg.pose.orientation.z = -0.5
        
        # Create test pose message for right arm
        right_msg = PoseStamped()
        right_msg.header.stamp = node.get_clock().now().to_msg()
        right_msg.header.frame_id = 'base_link'  # Planning frame
        
        # Set position for right arm (initial + 1cm forward only)
        right_msg.pose.position.x = 0.249  # 0.239 + 0.01 (forward)
        right_msg.pose.position.y = -0.170  # same Y position
        right_msg.pose.position.z = 0.324  # same height
        
        # Set orientation same as initial state (exact match)
        right_msg.pose.orientation.w = 0.5
        right_msg.pose.orientation.x = 0.5
        right_msg.pose.orientation.y = -0.5
        right_msg.pose.orientation.z = -0.5
        
        # Publish to both arms
        left_pub.publish(left_msg)
        right_pub.publish(right_msg)
        
        node.get_logger().info('Published test goal poses')
    
    # Create timer to publish poses periodically
    timer = node.create_timer(5.0, publish_test_pose)  # Publish every 5 seconds
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
