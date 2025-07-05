#!/usr/bin/env python3

import rclpy
import rclpy.node
from rclpy.action import ActionClient
from rclpy.action.client import ClientGoalHandle
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor

import geometry_msgs.msg
import moveit_msgs.action
import moveit_msgs.msg
import shape_msgs.msg

class MoveItPoseBridge(rclpy.node.Node):
    """
    Goal Pose → MoveIt Action 브리지 노드
    
    기존 teleop_web_node와 MoveIt 사이의 브리지 역할:
    - left/goal_pose, right/goal_pose 구독
    - MoveIt Action Client로 pose goal 전송
    - moveit_relay_node가 trajectory를 하드웨어로 변환
    """
    
    def __init__(self):
        super().__init__('moveit_pose_bridge')
        
        self.get_logger().info("MoveIt Pose Bridge 시작...")
        
        # Callback group 설정 (재진입 가능)
        self.callback_group = ReentrantCallbackGroup()
        
        # MoveGroup Action Client
        self.move_group_client = ActionClient(
            self, 
            moveit_msgs.action.MoveGroup, 
            '/move_action',
            callback_group=self.callback_group
        )
        
        # Action client 연결 대기
        self.get_logger().info("MoveGroup action server 연결 시도 중...")
        self.get_logger().info(f"Action 이름: {self.move_group_client._action_name}")
        self.get_logger().info(f"Action 타입: {self.move_group_client._action_type}")
        
        # Timer를 instance variable로 저장
        self.connection_timer = self.create_timer(1.0, self.check_action_server_status)
        self.is_connected = False
        
        # goal_pose 구독 - action server 연결과 무관하게 미리 설정
        self.create_subscription(
            geometry_msgs.msg.PoseStamped,
            'left/goal_pose',
            self.left_goal_pose_callback,
            10,
            callback_group=self.callback_group
        )
        
        self.create_subscription(
            geometry_msgs.msg.PoseStamped,
            'right/goal_pose', 
            self.right_goal_pose_callback,
            10,
            callback_group=self.callback_group
        )
        
        self.get_logger().info("MoveIt Pose Bridge 초기화 완료!")
        self.get_logger().info("구독 토픽:")
        self.get_logger().info("  - left/goal_pose")
        self.get_logger().info("  - right/goal_pose")
    
    def print_available_actions(self):
        """사용 가능한 action 목록 출력"""
        try:
            from rclpy.action import get_action_names_and_types
            actions = get_action_names_and_types(self)
            self.get_logger().info("=== 사용 가능한 Actions ===")
            for name, types in actions:
                self.get_logger().info(f"Action: {name}")
                self.get_logger().info(f"  Types: {types}")
            self.get_logger().info("========================")
        except Exception as e:
            self.get_logger().error(f"Action 목록 조회 실패: {str(e)}")
    
    def check_action_server_status(self):
        """Action server 상태 확인"""
        try:
            # server_is_ready()가 신뢰할 수 없으므로 실제 연결 시도
            if not self.is_connected:
                # 실제로 action server가 응답하는지 확인하기 위해 간단한 테스트
                # wait_for_server를 매우 짧은 시간으로 시도
                if self.move_group_client.wait_for_server(timeout_sec=0.1):
                    self.get_logger().info("✅ MoveGroup action server 연결 성공!")
                    self.is_connected = True
                    if self.connection_timer:
                        self.connection_timer.cancel()
                        self.connection_timer = None
                    return
                else:
                    self.get_logger().warn("⏳ MoveGroup action server 연결 대기 중...")
                    self.get_logger().info(f"  - Action 이름: {self.move_group_client._action_name}")
                    
        except Exception as e:
            self.get_logger().error(f"Action server 상태 확인 중 오류: {e}")
    
    def feedback_callback(self, feedback_msg):
        """MoveIt action feedback 콜백"""
        self.get_logger().info(f"MoveIt 진행 상태: {feedback_msg.feedback.state}")
    
    def left_goal_pose_callback(self, msg: geometry_msgs.msg.PoseStamped):
        """왼팔 goal_pose 처리"""
        self.get_logger().info(f"Left goal_pose 수신: ({msg.pose.position.x:.3f}, {msg.pose.position.y:.3f}, {msg.pose.position.z:.3f})")
        self.send_moveit_goal("left_arm_gripper_group", msg.pose, "l_jaw_link")
    
    def right_goal_pose_callback(self, msg: geometry_msgs.msg.PoseStamped):
        """오른팔 goal_pose 처리"""
        self.get_logger().info(f"Right goal_pose 수신: ({msg.pose.position.x:.3f}, {msg.pose.position.y:.3f}, {msg.pose.position.z:.3f})")
        self.send_moveit_goal("right_arm_gripper_group", msg.pose, "r_jaw_link")
    
    def send_moveit_goal(self, group_name: str, target_pose: geometry_msgs.msg.Pose, end_effector_link: str):
        """
        MoveIt action goal 전송
        
        Args:
            group_name: MoveIt planning group 이름
            target_pose: 목표 pose
            end_effector_link: end effector link 이름
        """
        try:
            self.get_logger().info(f"🎯 {group_name} MoveIt goal 전송 시도...")
            
            # MoveGroup Goal 생성
            goal = moveit_msgs.action.MoveGroup.Goal()
            
            # Basic request 설정
            goal.request.group_name = group_name
            goal.request.num_planning_attempts = 3
            goal.request.max_velocity_scaling_factor = 0.3
            goal.request.max_acceleration_scaling_factor = 0.3
            goal.request.allowed_planning_time = 5.0
            goal.request.planner_id = "RRTConnect"
            
            # Pose target 설정 (더 간단한 방법)
            pose_target = geometry_msgs.msg.PoseStamped()
            pose_target.header.frame_id = "base_link"
            pose_target.header.stamp = self.get_clock().now().to_msg()
            pose_target.pose = target_pose
            
            # Goal constraints 설정
            goal_constraint = moveit_msgs.msg.Constraints()
            goal_constraint.name = f"{group_name}_pose_constraint"
            
            # Position constraint 설정
            position_constraint = moveit_msgs.msg.PositionConstraint()
            position_constraint.header.frame_id = "base_link"
            position_constraint.link_name = end_effector_link
            
            # 목표 위치 설정 (offset이 아닌 실제 위치)
            position_constraint.constraint_region.primitives.append(
                shape_msgs.msg.SolidPrimitive()
            )
            position_constraint.constraint_region.primitives[0].type = shape_msgs.msg.SolidPrimitive.SPHERE
            position_constraint.constraint_region.primitives[0].dimensions = [0.01]  # 1cm 허용 오차
            
            position_constraint.constraint_region.primitive_poses.append(target_pose)
            position_constraint.weight = 1.0
            
            # Orientation constraint 설정
            orientation_constraint = moveit_msgs.msg.OrientationConstraint()
            orientation_constraint.header.frame_id = "base_link"
            orientation_constraint.link_name = end_effector_link
            orientation_constraint.orientation = target_pose.orientation
            orientation_constraint.absolute_x_axis_tolerance = 0.1
            orientation_constraint.absolute_y_axis_tolerance = 0.1
            orientation_constraint.absolute_z_axis_tolerance = 0.1
            orientation_constraint.weight = 1.0
            
            # Goal constraints에 추가
            goal_constraint.position_constraints = [position_constraint]
            goal_constraint.orientation_constraints = [orientation_constraint]
            goal.request.goal_constraints = [goal_constraint]
            
            # Goal 전송
            self.get_logger().info(f"📤 {group_name} goal 전송 중...")
            self.get_logger().info(f"  - 목표 위치: ({target_pose.position.x:.3f}, {target_pose.position.y:.3f}, {target_pose.position.z:.3f})")
            self.get_logger().info(f"  - End effector: {end_effector_link}")
            
            # 비동기로 goal 전송
            future = self.move_group_client.send_goal_async(
                goal,
                feedback_callback=self.feedback_callback
            )
            
            # 결과 콜백 설정
            future.add_done_callback(lambda fut: self.goal_response_callback(fut, group_name))
            
        except Exception as e:
            self.get_logger().error(f"❌ {group_name} MoveIt goal 전송 실패: {e}")
            import traceback
            self.get_logger().error(f"상세 오류: {traceback.format_exc()}")
    
    def goal_response_callback(self, future, group_name: str):
        """Action goal response 콜백"""
        try:
            goal_handle = future.result()
            if not goal_handle.accepted:
                self.get_logger().error(f"{group_name} goal 거부됨")
                return
                
            self.get_logger().info(f"{group_name} goal 수락됨, 실행 대기 중...")
            
            # Result 대기
            result_future = goal_handle.get_result_async()
            result_future.add_done_callback(
                lambda fut: self.result_callback(fut, group_name)
            )
            
        except Exception as e:
            self.get_logger().error(f"{group_name} goal response 처리 실패: {str(e)}")
            self.get_logger().error(f"상세 에러: {type(e).__name__}: {str(e)}")
            import traceback
            self.get_logger().error(f"스택 트레이스:\n{traceback.format_exc()}")
    
    def result_callback(self, future, group_name: str):
        """Action result 콜백"""
        try:
            result = future.result()
            error_code = result.result.error_code.val
            
            if error_code == 1:  # SUCCESS
                self.get_logger().info(f"✅ {group_name} 성공!")
            else:
                self.get_logger().error(f"❌ {group_name} 실패 (에러 코드: {error_code})")
                
        except Exception as e:
            self.get_logger().error(f"{group_name} result 처리 실패: {str(e)}")
            self.get_logger().error(f"상세 에러: {type(e).__name__}: {str(e)}")
            import traceback
            self.get_logger().error(f"스택 트레이스:\n{traceback.format_exc()}")

def main(args=None):
    rclpy.init(args=args)
    
    executor = MultiThreadedExecutor()
    node = MoveItPoseBridge()
    executor.add_node(node)
    
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        executor.shutdown()
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main() 