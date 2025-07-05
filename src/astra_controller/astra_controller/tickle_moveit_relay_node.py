import rclpy
import rclpy.node
import rclpy.qos
import rclpy.action

import astra_controller_interfaces.msg
import control_msgs.action
import controller_manager_msgs.srv

def main(args=None):
    rclpy.init(args=args)

    node = rclpy.node.Node('tickle_moveit_relay_node')

    # Publisher: arm joint command만 (gripper는 pedal 제어, lift는 고정)
    arm_joint_command_publisher = node.create_publisher(
        astra_controller_interfaces.msg.JointCommand, 
        "arm/joint_command", 
        10
    )
    
    # Joint position tracking (양팔 arm joints만)
    joint_pos = {
        # 오른팔 arm joints
        "joint_r2": 0.0, 
        "joint_r3": 0.0, 
        "joint_r4": 0.0, 
        "joint_r5": 0.0, 
        "joint_r6": 0.0,
        # 왼팔 arm joints  
        "joint_l2": 0.0,
        "joint_l3": 0.0,
        "joint_l4": 0.0,
        "joint_l5": 0.0,
        "joint_l6": 0.0
    }

    # ================================================================
    # 🔄 모드 전환 블록: Controller Manager 서비스
    # ================================================================
    # 시뮬레이션 모드 (현재 활성화): 아래 블록 활성화
    # 하드웨어 모드: 아래 블록 전체 주석 처리
    # ================================================================
    
    def list_controllers_callback(request, response):
        """가짜 컨트롤러 목록 반환"""
        node.get_logger().info(" Controller Manager: list_controllers service called")
        
        # 오른팔 컨트롤러
        right_controller = controller_manager_msgs.srv.ListControllers.Response.ControllerState()
        right_controller.name = "right_arm_gripper_group_controller"
        right_controller.state = "active"
        right_controller.type = "joint_trajectory_controller/JointTrajectoryController"
        right_controller.claimed_interfaces = [
            "joint_r2/position", "joint_r3/position", "joint_r4/position", 
            "joint_r5/position", "joint_r6/position", "joint_r7r/position"
        ]
        
        # 왼팔 컨트롤러
        left_controller = controller_manager_msgs.srv.ListControllers.Response.ControllerState()
        left_controller.name = "left_arm_gripper_group_controller"  
        left_controller.state = "active"
        left_controller.type = "joint_trajectory_controller/JointTrajectoryController"
        left_controller.claimed_interfaces = [
            "joint_l2/position", "joint_l3/position", "joint_l4/position",
            "joint_l5/position", "joint_l6/position", "joint_l7l/position"
        ]
        
        response.controller = [right_controller, left_controller]
        node.get_logger().info(f"🔧 Controller Manager: {len(response.controller)}개 컨트롤러 반환")
        return response
    
    def list_controller_types_callback(request, response):
        """사용 가능한 컨트롤러 타입 반환"""
        node.get_logger().info("🔧 Controller Manager: list_controller_types 서비스 호출됨!")
        
        controller_type = controller_manager_msgs.srv.ListControllerTypes.Response.ControllerType()
        controller_type.name = "joint_trajectory_controller/JointTrajectoryController"
        controller_type.base_class = "controller_interface::ControllerInterface"
        response.types = [controller_type]
        return response
    
    # Controller Manager 서비스 생성
    node.create_service(
        controller_manager_msgs.srv.ListControllers,
        '/controller_manager/list_controllers',
        list_controllers_callback
    )
    node.get_logger().info("🔧 Controller Manager: /controller_manager/list_controllers 서비스 생성됨")
    
    node.create_service(
        controller_manager_msgs.srv.ListControllerTypes,
        '/controller_manager/list_controller_types', 
        list_controller_types_callback
    )
    node.get_logger().info("🔧 Controller Manager: /controller_manager/list_controller_types 서비스 생성됨")
    
    # ================================================================
    # 🔄 모드 전환 블록 끝
    # ================================================================

    def right_arm_execute_trajectory(goal_handle):
        """오른팔 trajectory 실행"""
        node.get_logger().info(f"🤖 오른팔 trajectory 수신! {len(goal_handle.request.trajectory.points)} 포인트")
        
        # Trajectory points를 joint commands로 변환
        trajectory = goal_handle.request.trajectory
        joint_names = trajectory.joint_names
        
        node.get_logger().info(f"🎯 Joint names: {joint_names}")
        
        if len(trajectory.points) > 0:
            # 마지막 포인트의 목표 위치 사용
            target_point = trajectory.points[-1]
            
            # Joint command 메시지 생성 (arm joints만)
            arm_command = astra_controller_interfaces.msg.JointCommand()
            arm_command.name = []
            arm_command.position_cmd = []
            
            for i, joint_name in enumerate(joint_names):
                if joint_name in ["joint_r2", "joint_r3", "joint_r4", "joint_r5", "joint_r6", "joint_r7r"]:
                    arm_command.name.append(joint_name)
                    arm_command.position_cmd.append(target_point.positions[i])
                    # Joint position 업데이트
                    joint_pos[joint_name] = target_point.positions[i]
            
            # Joint command 발행
            if len(arm_command.name) > 0:
                node.get_logger().info(f"📤 오른팔 Joint command 발행: {dict(zip(arm_command.name, arm_command.position_cmd))}")
                arm_joint_command_publisher.publish(arm_command)
        
        # 즉시 성공으로 응답
        goal_handle.succeed()
        result = control_msgs.action.FollowJointTrajectory.Result()
        result.error_code = control_msgs.action.FollowJointTrajectory.Result.SUCCESSFUL
        node.get_logger().info("✅ 오른팔 trajectory 실행 완료!")
        return result

    def left_arm_execute_trajectory(goal_handle):
        """왼팔 trajectory 실행"""
        node.get_logger().info(f"🤖 왼팔 trajectory 수신! {len(goal_handle.request.trajectory.points)} 포인트")
        
        # Trajectory points를 joint commands로 변환
        trajectory = goal_handle.request.trajectory
        joint_names = trajectory.joint_names
        
        node.get_logger().info(f"🎯 Joint names: {joint_names}")
        
        if len(trajectory.points) > 0:
            # 마지막 포인트의 목표 위치 사용
            target_point = trajectory.points[-1]
            
            # Joint command 메시지 생성 (arm joints만)
            arm_command = astra_controller_interfaces.msg.JointCommand()
            arm_command.name = []
            arm_command.position_cmd = []
            
            for i, joint_name in enumerate(joint_names):
                if joint_name in ["joint_l2", "joint_l3", "joint_l4", "joint_l5", "joint_l6", "joint_l7l"]:
                    arm_command.name.append(joint_name)
                    arm_command.position_cmd.append(target_point.positions[i])
                    # Joint position 업데이트
                    joint_pos[joint_name] = target_point.positions[i]
            
            # Joint command 발행
            if len(arm_command.name) > 0:
                node.get_logger().info(f"📤 왼팔 Joint command 발행: {dict(zip(arm_command.name, arm_command.position_cmd))}")
                arm_joint_command_publisher.publish(arm_command)
        
        # 즉시 성공으로 응답
        goal_handle.succeed()
        result = control_msgs.action.FollowJointTrajectory.Result()
        result.error_code = control_msgs.action.FollowJointTrajectory.Result.SUCCESSFUL
        node.get_logger().info("✅ 왼팔 trajectory 실행 완료!")
        return result

    # 오른팔 Action Server
    right_arm_action_server = rclpy.action.ActionServer(
        node,
        control_msgs.action.FollowJointTrajectory,
        '/right_arm_gripper_group_controller/follow_joint_trajectory',
        right_arm_execute_trajectory
    )
    node.get_logger().info("🤖 오른팔 Action Server 시작됨")
    
    # 왼팔 Action Server
    left_arm_action_server = rclpy.action.ActionServer(
        node,
        control_msgs.action.FollowJointTrajectory,
        '/left_arm_gripper_group_controller/follow_joint_trajectory',
        left_arm_execute_trajectory
    )
    node.get_logger().info("🤖 왼팔 Action Server 시작됨")
    
    node.get_logger().info('Tickle MoveIt Relay Node started')
    node.get_logger().info('- Right arm: /right_arm_gripper_group_controller/follow_joint_trajectory')
    node.get_logger().info('- Left arm: /left_arm_gripper_group_controller/follow_joint_trajectory')
    node.get_logger().info('- Output: arm/joint_command (arm joints only)')
    node.get_logger().info('- Gripper: Controlled by pedal (excluded from MoveIt)')

    rclpy.spin(node)

    # 정리
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main() 