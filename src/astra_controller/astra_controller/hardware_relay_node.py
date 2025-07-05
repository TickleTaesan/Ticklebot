import rclpy
import rclpy.node
import rclpy.qos

import sensor_msgs.msg
import astra_controller_interfaces.msg

def main(args=None):
    rclpy.init(args=args)

    node = rclpy.node.Node('hardware_relay_node')

    # Publisher: arm joint command
    arm_joint_command_publisher = node.create_publisher(
        astra_controller_interfaces.msg.JointCommand, 
        "arm/joint_command", 
        10
    )
    
    # 현재 joint positions 저장
    current_joint_positions = {}
    
    # 관심 있는 joint들 (arm joints만)
    arm_joints = [
        "joint_r2", "joint_r3", "joint_r4", "joint_r5", "joint_r6",  # 오른팔
        "joint_l2", "joint_l3", "joint_l4", "joint_l5", "joint_l6"   # 왼팔
    ]

    def joint_states_callback(msg: sensor_msgs.msg.JointState):
        """joint_states를 받아서 JointCommand로 변환"""
        
        # joint_states에서 arm joints만 추출
        updated_joints = []
        updated_positions = []
        
        for i, joint_name in enumerate(msg.name):
            if joint_name in arm_joints:
                current_joint_positions[joint_name] = msg.position[i]
                updated_joints.append(joint_name)
                updated_positions.append(msg.position[i])
        
        # 업데이트된 joint가 있으면 JointCommand 발행
        if updated_joints:
            joint_command = astra_controller_interfaces.msg.JointCommand(
                name=updated_joints,
                position_cmd=updated_positions
            )
            arm_joint_command_publisher.publish(joint_command)
            
            node.get_logger().debug(f'Hardware relay: {len(updated_joints)} joints updated')

    # joint_states 구독
    node.create_subscription(
        sensor_msgs.msg.JointState,
        '/joint_states',
        joint_states_callback,
        rclpy.qos.qos_profile_sensor_data
    )
    
    node.get_logger().info('Hardware Relay Node started')
    node.get_logger().info('- Input: /joint_states')
    node.get_logger().info('- Output: arm/joint_command (arm joints only)')
    node.get_logger().info(f'- Monitoring joints: {arm_joints}')

    rclpy.spin(node)

    # 정리
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main() 