import rclpy
import rclpy.node
import rclpy.qos
import rclpy.action

import astra_controller_interfaces.msg
import control_msgs.action
import astra_controller_interfaces.srv

def main(args=None):
    rclpy.init(args=args)

    node = rclpy.node.Node('moveit_relay_node')

    # Publishers for hardware commands
    right_arm_joint_command_publisher = node.create_publisher(astra_controller_interfaces.msg.JointCommand, "right/arm/joint_command", 10)
    left_arm_joint_command_publisher = node.create_publisher(astra_controller_interfaces.msg.JointCommand, "left/arm/joint_command", 10)
    
    right_gripper_joint_command_publisher = node.create_publisher(astra_controller_interfaces.msg.JointCommand, "right/arm/gripper_joint_command", 10)
    left_gripper_joint_command_publisher = node.create_publisher(astra_controller_interfaces.msg.JointCommand, "left/arm/gripper_joint_command", 10)

    lift_joint_command_publisher = node.create_publisher(astra_controller_interfaces.msg.JointCommand, "lift/joint_command", 10)
    
    # Joint positions storage
    joint_pos = {
        # Right arm joints
        "joint_r1": 0, "joint_r2": 0, "joint_r3": 0, "joint_r4": 0, "joint_r5": 0, "joint_r6": 0, "joint_r7r": 0,
        # Left arm joints  
        "joint_l1": 0, "joint_l2": 0, "joint_l3": 0, "joint_l4": 0, "joint_l5": 0, "joint_l6": 0, "joint_l7l": 0
    }

    def right_arm_execute_callback(goal_handle: rclpy.action.server.ServerGoalHandle):
        node.get_logger().info('Executing right arm goal...')
        
        # Update joint positions
        for joint_name, position in zip(
            goal_handle.request.trajectory.joint_names, 
            goal_handle.request.trajectory.points[-1].positions
        ):
            joint_pos[joint_name] = position

        # Publish arm joints (r2~r6)
        arm_msg = astra_controller_interfaces.msg.JointCommand(
            name=["joint_r2", "joint_r3", "joint_r4", "joint_r5", "joint_r6"],
            position_cmd=[
                joint_pos["joint_r2"], joint_pos["joint_r3"], joint_pos["joint_r4"],
                joint_pos["joint_r5"], joint_pos["joint_r6"]
            ]
        )
        right_arm_joint_command_publisher.publish(arm_msg)

        # Publish gripper joint (r7r) if included
        if "joint_r7r" in goal_handle.request.trajectory.joint_names:
            gripper_msg = astra_controller_interfaces.msg.JointCommand(
                name=["joint_r7r"],
                position_cmd=[joint_pos["joint_r7r"]]
            )
            right_gripper_joint_command_publisher.publish(gripper_msg)

        # Publish lift joint (r1) if included
        if "joint_r1" in goal_handle.request.trajectory.joint_names:
            lift_msg = astra_controller_interfaces.msg.JointCommand(
                name=["joint_r1"],
                position_cmd=[joint_pos["joint_r1"]]
            )
            lift_joint_command_publisher.publish(lift_msg)
        
        goal_handle.succeed()

        result = control_msgs.action.FollowJointTrajectory.Result()
        result.error_code = control_msgs.action.FollowJointTrajectory.Result.SUCCESSFUL
        result.error_string = "SUCC"
        return result

    def left_arm_execute_callback(goal_handle: rclpy.action.server.ServerGoalHandle):
        node.get_logger().info('Executing left arm goal...')
        
        # Update joint positions
        for joint_name, position in zip(
            goal_handle.request.trajectory.joint_names, 
            goal_handle.request.trajectory.points[-1].positions
        ):
            joint_pos[joint_name] = position

        # Publish arm joints (l2~l6)
        arm_msg = astra_controller_interfaces.msg.JointCommand(
            name=["joint_l2", "joint_l3", "joint_l4", "joint_l5", "joint_l6"],
            position_cmd=[
                joint_pos["joint_l2"], joint_pos["joint_l3"], joint_pos["joint_l4"],
                joint_pos["joint_l5"], joint_pos["joint_l6"]
            ]
        )
        left_arm_joint_command_publisher.publish(arm_msg)

        # Publish gripper joint (l7l) if included
        if "joint_l7l" in goal_handle.request.trajectory.joint_names:
            gripper_msg = astra_controller_interfaces.msg.JointCommand(
                name=["joint_l7l"],
                position_cmd=[joint_pos["joint_l7l"]]
            )
            left_gripper_joint_command_publisher.publish(gripper_msg)

        # Publish lift joint (l1) if included
        if "joint_l1" in goal_handle.request.trajectory.joint_names:
            lift_msg = astra_controller_interfaces.msg.JointCommand(
                name=["joint_l1"],
                position_cmd=[joint_pos["joint_l1"]]
            )
            lift_joint_command_publisher.publish(lift_msg)
        
        goal_handle.succeed()

        result = control_msgs.action.FollowJointTrajectory.Result()
        result.error_code = control_msgs.action.FollowJointTrajectory.Result.SUCCESSFUL
        result.error_string = "SUCC"
        return result

    # Create action servers for both arms
    right_arm_action_server = rclpy.action.ActionServer(
        node,
        control_msgs.action.FollowJointTrajectory,
        '/right_arm_gripper_group_controller/follow_joint_trajectory',
        right_arm_execute_callback
    )

    left_arm_action_server = rclpy.action.ActionServer(
        node,
        control_msgs.action.FollowJointTrajectory,
        '/left_arm_gripper_group_controller/follow_joint_trajectory',
        left_arm_execute_callback
    )

    node.get_logger().info('MoveIt Relay Node ready!')
    node.get_logger().info('Action servers:')
    node.get_logger().info('  - /right_arm_gripper_group_controller/follow_joint_trajectory')
    node.get_logger().info('  - /left_arm_gripper_group_controller/follow_joint_trajectory')

    rclpy.spin(node)

    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
