import rclpy
import rclpy.node
import rclpy.qos

import sensor_msgs.msg
import astra_controller_interfaces.msg
import geometry_msgs.msg
import nav_msgs.msg
import numpy as np
import threading
import time
import math
import sys # sys.exit를 위해 추가

import logging

logger = logging.getLogger(__name__)

np.set_printoptions(precision=4, suppress=True)

class DryRunNode(rclpy.node.Node):
    def __init__(self):
        super().__init__("dry_run_node")

        self.joint_state_publisher = self.create_publisher(sensor_msgs.msg.JointState, "joint_states", 10)
        self.odom_publisher = self.create_publisher(nav_msgs.msg.Odometry, "odom", 10)

        self.declare_parameter('actively_send_joint_state', True)
        self.declare_parameter('joint_names', [ "joint_l1", "joint_l2", "joint_l3", "joint_l4", "joint_l5", "joint_l6", "joint_l7l" ])

        # self.declare_parameter('joint_names', [ "joint_r1", "joint_r2", "joint_r3", "joint_r4", "joint_r5", "joint_r6", "joint_r7l", "joint_r7r" ])

        self.actively_send_joint_state = self.get_parameter('actively_send_joint_state').value
        self.joint_names = self.get_parameter('joint_names').value
        
        # 설정된 joint들 로깅
        self.get_logger().info(f"DRY RUN node started with joints: {self.joint_names}")
        self.get_logger().info(f"Actively send joint state: {self.actively_send_joint_state}")
        
        # assert len(self.joint_names) == 8  # 제한 제거 - 유연한 joint 개수 허용

        self.joint_states = { joint_name: 0.0 for joint_name in self.joint_names }

        # Base Odometry Simulation Initialization
        self.current_x = 0.0
        self.current_y = 0.0
        self.current_theta = 0.0
        self.last_base_cmd_time = self.get_clock().now().nanoseconds / 1e9
        self.last_linear_vel_x = 0.0 # 초기화 추가
        self.last_angular_vel_z = 0.0 # 초기화 추가

        if self.actively_send_joint_state:
            self.joint_state_thread = threading.Thread(target=self.publish_joint_states_loop, daemon=True)
            self.joint_state_thread.start()

        # Subscriptions for Joint Commands (Arm, Gripper, Lift)
        self.create_subscription(
            astra_controller_interfaces.msg.JointCommand, 
            "arm/joint_command", 
            self.arm_joint_command_cb, 
            rclpy.qos.qos_profile_sensor_data
        )
        self.create_subscription(
            astra_controller_interfaces.msg.JointCommand, 
            "arm/gripper_joint_command", 
            self.gripper_joint_command_cb, 
            rclpy.qos.qos_profile_sensor_data
        )
        self.create_subscription(
            astra_controller_interfaces.msg.JointCommand, 
            "lift/joint_command", 
            self.lift_joint_command_cb, 
            rclpy.qos.qos_profile_sensor_data
        )

        # Subscription for Base Velocity Commands
        self.create_subscription(
            geometry_msgs.msg.Twist,
            "cmd_vel",  # 일반적인 로봇 베이스 속도 명령 토픽
            self.cmd_vel_cb,
            10
        )

        # Timer for Odometry Publishing
        self.odom_timer = self.create_timer(0.05, self.publish_odom) # 20 Hz

    def publish_joint_states_loop(self):
        while rclpy.ok():
            msg = sensor_msgs.msg.JointState()
            msg.header.stamp = self.get_clock().now().to_msg()
            msg.header.frame_id = "base_link"  # 적절한 frame_id 설정
            msg.name = list(self.joint_states.keys())
            msg.position = [float(x) for x in self.joint_states.values()]
            msg.velocity = [0.0] * len(msg.position)  # velocity 추가
            msg.effort = [0.0] * len(msg.position)    # effort 추가
            self.joint_state_publisher.publish(msg)
            time.sleep(0.05)  # 더 빠른 주기 (20Hz)

    def arm_joint_command_cb(self, msg: astra_controller_interfaces.msg.JointCommand):
        
        send_msg = sensor_msgs.msg.JointState()
        send_msg.header.stamp = self.get_clock().now().to_msg()
        send_msg.name = msg.name
        send_msg.position = msg.position_cmd
        self.joint_state_publisher.publish(send_msg)

        if self.actively_send_joint_state:
            for i, name in enumerate(send_msg.name):
                self.joint_states[name] = send_msg.position[i]

    def gripper_joint_command_cb(self, msg: astra_controller_interfaces.msg.JointCommand):
        
        send_msg = sensor_msgs.msg.JointState()
        send_msg.header.stamp = self.get_clock().now().to_msg()
        
        # 그리퍼 joint가 설정되어 있는지 확인
        gripper_joints = []
        for joint_name in ["joint_l7l", "joint_r7r"]:
            if joint_name in self.joint_names:
                gripper_joints.append(joint_name)
        
        if len(gripper_joints) >= 2:
            # 기존 방식: 첫 번째 gripper command를 양쪽에 적용
            send_msg.name = gripper_joints[:2]
            send_msg.position = [ msg.position_cmd[0], -msg.position_cmd[0] ]
            self.joint_state_publisher.publish(send_msg)

            if self.actively_send_joint_state:
                self.joint_states[gripper_joints[0]] = send_msg.position[0]
                self.joint_states[gripper_joints[1]] = send_msg.position[1]
        else:
            # 그리퍼 joint가 없으면 로그만 출력하고 무시
            self.get_logger().debug(f"Gripper command received but no gripper joints configured: {msg.name}")
            self.get_logger().debug(f"Available joints: {self.joint_names}")

    def lift_joint_command_cb(self, msg: astra_controller_interfaces.msg.JointCommand):
        
        send_msg = sensor_msgs.msg.JointState()
        send_msg.header.stamp = self.get_clock().now().to_msg()
        send_msg.name = msg.name
        send_msg.position = msg.position_cmd
        self.joint_state_publisher.publish(send_msg)

        if self.actively_send_joint_state:
            for i, name in enumerate(send_msg.name):
                self.joint_states[name] = send_msg.position[i]

    def cmd_vel_cb(self, msg: geometry_msgs.msg.Twist):
        # Simulate base movement based on cmd_vel
        current_time = self.get_clock().now().nanoseconds / 1e9
        dt = current_time - self.last_base_cmd_time
        self.last_base_cmd_time = current_time

        linear_vel_x = msg.linear.x
        angular_vel_z = msg.angular.z

        # Update pose
        delta_x = linear_vel_x * math.cos(self.current_theta) * dt
        delta_y = linear_vel_x * math.sin(self.current_theta) * dt
        delta_theta = angular_vel_z * dt

        self.current_x += delta_x
        self.current_y += delta_y
        self.current_theta += delta_theta

        # Normalize theta to be within -pi to pi
        self.current_theta = math.atan2(math.sin(self.current_theta), math.cos(self.current_theta))

        self.last_linear_vel_x = linear_vel_x
        self.last_angular_vel_z = angular_vel_z

    def publish_odom(self):
        # Publish odometry message
        odom_msg = nav_msgs.msg.Odometry()
        odom_msg.header.stamp = self.get_clock().now().to_msg()
        odom_msg.header.frame_id = "odom"
        odom_msg.child_frame_id = "base_link" # or your robot's base frame

        odom_msg.pose.pose.position.x = self.current_x
        odom_msg.pose.pose.position.y = self.current_y
        odom_msg.pose.pose.position.z = 0.0

        # Convert yaw to quaternion
        quat_x = 0.0
        quat_y = 0.0
        quat_z = math.sin(self.current_theta / 2.0)
        quat_w = math.cos(self.current_theta / 2.0)
        odom_msg.pose.pose.orientation.x = quat_x
        odom_msg.pose.pose.orientation.y = quat_y
        odom_msg.pose.pose.orientation.z = quat_z
        odom_msg.pose.pose.orientation.w = quat_w

        odom_msg.twist.twist.linear.x = self.last_linear_vel_x
        odom_msg.twist.twist.angular.z = self.last_angular_vel_z

        self.odom_publisher.publish(odom_msg)

def main(args=None):
    rclpy.init(args=args)
    node = DryRunNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()