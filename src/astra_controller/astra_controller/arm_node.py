import rclpy
import rclpy.node
import rclpy.qos
import rclpy.action

import sensor_msgs.msg
import std_msgs.msg
import astra_controller_interfaces.msg
import struct
import numpy as np

from .arm_controller import ArmController

def main(args=None):
    rclpy.init(args=args)

    node = rclpy.node.Node('arm_node')

    logger = node.get_logger()
    
    # 왼쪽 팔 파라미터
    node.declare_parameter('left_device', '/dev/tty_puppet_left')
    node.declare_parameter('left_joint_names', [ "joint_l2", "joint_l3", "joint_l4", "joint_l5", "joint_l6" ])
    node.declare_parameter('left_gripper_joint_names', [ "joint_l7l", "joint_l7r" ])
    
    # 오른쪽 팔 파라미터
    node.declare_parameter('right_device', '/dev/tty_puppet_right')
    node.declare_parameter('right_joint_names', [ "joint_r2", "joint_r3", "joint_r4", "joint_r5", "joint_r6" ])
    node.declare_parameter('right_gripper_joint_names', [ "joint_r7l", "joint_r7r" ])

    # 왼쪽 팔 설정
    left_device = node.get_parameter('left_device').value
    left_joint_names = node.get_parameter('left_joint_names').value
    left_gripper_joint_names = node.get_parameter('left_gripper_joint_names').value
    
    # 오른쪽 팔 설정
    right_device = node.get_parameter('right_device').value
    right_joint_names = node.get_parameter('right_joint_names').value
    right_gripper_joint_names = node.get_parameter('right_gripper_joint_names').value
    
    assert len(left_joint_names) == 5
    assert len(left_gripper_joint_names) == 2
    assert len(right_joint_names) == 5
    assert len(right_gripper_joint_names) == 2

    # 왼쪽 팔 컨트롤러
    left_arm_controller = ArmController(left_device)
    # 오른쪽 팔 컨트롤러
    right_arm_controller = ArmController(right_device)
    
    # 통합된 Joint States 퍼블리셔 (dry_run_node와 동일한 방식)
    joint_state_publisher = node.create_publisher(sensor_msgs.msg.JointState, "joint_states", 10)
    left_gripper_joint_state_publisher = node.create_publisher(sensor_msgs.msg.JointState, "left/gripper_joint_states", 10)
    right_gripper_joint_state_publisher = node.create_publisher(sensor_msgs.msg.JointState, "right/gripper_joint_states", 10)
    
    # 양쪽 팔 상태 저장용 (초기값)
    left_arm_state = {
        'position': [0.0, 0.0, 0.0, 0.0, 0.0],
        'velocity': [0.0, 0.0, 0.0, 0.0, 0.0],
        'effort': [0.0, 0.0, 0.0, 0.0, 0.0]
    }
    right_arm_state = {
        'position': [0.0, 0.0, 0.0, 0.0, 0.0],
        'velocity': [0.0, 0.0, 0.0, 0.0, 0.0],
        'effort': [0.0, 0.0, 0.0, 0.0, 0.0]
    }
    
    def left_state_cb(position, velocity, effort, this_time):
        nonlocal left_arm_state
        left_arm_state = {
            'position': [ float(p) for p in position[:5] ],
            'velocity': [ float(v) for v in velocity[:5] ],
            'effort': [ float(e) for e in effort[:5] ]
        }
        
        # 통합된 Joint States 메시지 발행 (항상 발행)
        msg = sensor_msgs.msg.JointState()
        msg.header.stamp = node.get_clock().now().to_msg()
        msg.header.frame_id = "base_link"
        msg.name = left_joint_names + right_joint_names
        msg.position = left_arm_state['position'] + right_arm_state['position']
        msg.velocity = left_arm_state['velocity'] + right_arm_state['velocity']
        msg.effort = left_arm_state['effort'] + right_arm_state['effort']
        joint_state_publisher.publish(msg)
        
        # 왼쪽 그리퍼 상태 발행
        msg = sensor_msgs.msg.JointState()
        msg.header.stamp = node.get_clock().now().to_msg()
        msg.name = left_gripper_joint_names
        msg.position = [ -float(position[5]), float(position[5]) ]
        msg.velocity = [ -float(velocity[5]), float(velocity[5]) ]
        msg.effort = [ -float(effort[5]), float(effort[5]) ]
        left_gripper_joint_state_publisher.publish(msg)
    left_arm_controller.state_cb = left_state_cb

    def right_state_cb(position, velocity, effort, this_time):
        nonlocal right_arm_state
        right_arm_state = {
            'position': [ float(p) for p in position[:5] ],
            'velocity': [ float(v) for v in velocity[:5] ],
            'effort': [ float(e) for e in effort[:5] ]
        }
        
        # 통합된 Joint States 메시지 발행 (항상 발행)
        msg = sensor_msgs.msg.JointState()
        msg.header.stamp = node.get_clock().now().to_msg()
        msg.header.frame_id = "base_link"
        msg.name = left_joint_names + right_joint_names
        msg.position = left_arm_state['position'] + right_arm_state['position']
        msg.velocity = left_arm_state['velocity'] + right_arm_state['velocity']
        msg.effort = left_arm_state['effort'] + right_arm_state['effort']
        joint_state_publisher.publish(msg)
        
        # 오른쪽 그리퍼 상태 발행
        msg = sensor_msgs.msg.JointState()
        msg.header.stamp = node.get_clock().now().to_msg()
        msg.name = right_gripper_joint_names
        msg.position = [ -float(position[5]), float(position[5]) ]
        msg.velocity = [ -float(velocity[5]), float(velocity[5]) ]
        msg.effort = [ -float(effort[5]), float(effort[5]) ]
        right_gripper_joint_state_publisher.publish(msg)
    right_arm_controller.state_cb = right_state_cb

    # 디버그 퍼블리셔
    left_debug_publisher = node.create_publisher(std_msgs.msg.Float32MultiArray, 'debug', 10)
    def left_debug_cb(data):
        msg = std_msgs.msg.Float32MultiArray()
        msg.data = data
        left_debug_publisher.publish(msg)
    left_arm_controller.debug_cb = left_debug_cb
    
    right_debug_publisher = node.create_publisher(std_msgs.msg.Float32MultiArray, 'debug', 10)
    def right_debug_cb(data):
        msg = std_msgs.msg.Float32MultiArray()
        msg.data = data
        right_debug_publisher.publish(msg)
    right_arm_controller.debug_cb = right_debug_cb

    # 에러 퍼블리셔
    error_publisher = node.create_publisher(std_msgs.msg.String, 'error', 10)
    def left_error_cb(data):
        error_publisher.publish(std_msgs.msg.String(data="left: " + data))
    left_arm_controller.error_cb = left_error_cb
    
    def right_error_cb(data):
        error_publisher.publish(std_msgs.msg.String(data="right: " + data))
    right_arm_controller.error_cb = right_error_cb
    
    # Pong 퍼블리셔
    pong_publisher = node.create_publisher(std_msgs.msg.UInt16MultiArray, 'pong', 10)
    def left_pong_cb(data):
        logger.info(f'left pong: {data}')
        pong_publisher.publish(std_msgs.msg.UInt16MultiArray(data=data))
    left_arm_controller.pong_cb = left_pong_cb
    
    def right_pong_cb(data):
        logger.info(f'right pong: {data}')
        pong_publisher.publish(std_msgs.msg.UInt16MultiArray(data=data))
    right_arm_controller.pong_cb = right_pong_cb
    
    # 안전한 초기화 함수
    def get_safe_position(controller, default_pos):
        try:
            pos, vel, effort, time = controller.get_pos()
            if pos is not None:
                return pos
            else:
                logger.warning("Controller position is None, using default")
                return default_pos
        except Exception as e:
            logger.warning(f"Failed to get position: {e}, using default")
            return default_pos
    
    # 기본 위치 설정
    default_position = np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    
    # 초기 위치 설정 - 안전한 방식으로 변경
    left_last_position_cmd = get_safe_position(left_arm_controller, default_position)
    logger.info(f"using initial left state {left_last_position_cmd}")
    
    right_last_position_cmd = get_safe_position(right_arm_controller, default_position)
    logger.info(f"using initial right state {right_last_position_cmd}")
    
    # 초기 Joint States 발행
    def publish_initial_joint_states():
        # 통합된 초기 상태 (dry_run_node 방식)
        msg = sensor_msgs.msg.JointState()
        msg.header.stamp = node.get_clock().now().to_msg()
        msg.header.frame_id = "base_link"
        msg.name = left_joint_names + right_joint_names
        msg.position = [0.0] * 10  # 왼쪽 5개 + 오른쪽 5개
        msg.velocity = [0.0] * 10
        msg.effort = [0.0] * 10
        joint_state_publisher.publish(msg)
        
        logger.info("통합된 초기 Joint States 발행됨 (dry_run_node 방식)")
    
    # 1초 후 초기 상태 발행
    node.create_timer(1.0, lambda: publish_initial_joint_states())
    
    # Joint Command 구독
    def cb(msg: astra_controller_interfaces.msg.JointCommand):
        nonlocal left_last_position_cmd, right_last_position_cmd
        
        if len(msg.name) >= 5:
            # 메시지의 첫 번째 관절 이름으로 왼쪽/오른쪽 팔 구분
            if msg.name[0].startswith("joint_l"):  # 왼쪽 팔
                if msg.name[:5] == left_joint_names:  # 처음 5개 관절 확인
                    position_cmd = [*msg.position_cmd[:5], left_last_position_cmd[5]]
                    left_arm_controller.set_pos(position_cmd)
                    left_last_position_cmd = position_cmd
                    logger.debug(f"Set left arm position: {position_cmd}")
            elif msg.name[0].startswith("joint_r"):  # 오른쪽 팔
                if msg.name[:5] == right_joint_names:  # 처음 5개 관절 확인
                    position_cmd = [*msg.position_cmd[:5], right_last_position_cmd[5]]
                    right_arm_controller.set_pos(position_cmd)
                    right_last_position_cmd = position_cmd
                    logger.debug(f"Set right arm position: {position_cmd}")
    
    # arm/joint_command 토픽 구독 (tickle_moveit_relay_node에서 발행)
    node.create_subscription(astra_controller_interfaces.msg.JointCommand, 'arm/joint_command', cb, rclpy.qos.qos_profile_sensor_data)
    logger.info("구독 토픽: 'arm/joint_command'")
    
    # Gripper Joint Command 구독
    def left_gripper_cb(msg: astra_controller_interfaces.msg.JointCommand):
        nonlocal left_last_position_cmd
        if msg.name == left_gripper_joint_names[1:2]:
            position_cmd = [*left_last_position_cmd[:5], msg.position_cmd[0]]
            left_arm_controller.set_pos(position_cmd)
            left_last_position_cmd = position_cmd
    
    def right_gripper_cb(msg: astra_controller_interfaces.msg.JointCommand):
        nonlocal right_last_position_cmd
        if msg.name == right_gripper_joint_names[1:2]:
            position_cmd = [*right_last_position_cmd[:5], msg.position_cmd[0]]
            right_arm_controller.set_pos(position_cmd)
            right_last_position_cmd = position_cmd
    
    node.create_subscription(astra_controller_interfaces.msg.JointCommand, 'gripper_joint_command', left_gripper_cb, rclpy.qos.qos_profile_sensor_data)
    node.create_subscription(astra_controller_interfaces.msg.JointCommand, 'gripper_joint_command', right_gripper_cb, rclpy.qos.qos_profile_sensor_data)
    
    # Torque Enable 구독
    def torque_enable_cb(msg: std_msgs.msg.UInt8):
        logger.info(f'torque_enable: {msg.data}')
        left_arm_controller.set_torque(msg.data)
        right_arm_controller.set_torque(msg.data)
    
    node.create_subscription(std_msgs.msg.UInt8, 'torque_enable', torque_enable_cb, rclpy.qos.qos_profile_sensor_data)
    
    # Ping 구독
    def ping_cb(msg: std_msgs.msg.UInt16MultiArray):
        logger.info(f'ping: {msg.data}')
        left_arm_controller.write(struct.pack('>BBHHHHHHHH', left_arm_controller.COMM_HEAD, left_arm_controller.COMM_TYPE_PING, *msg.data))
        right_arm_controller.write(struct.pack('>BBHHHHHHHH', right_arm_controller.COMM_HEAD, right_arm_controller.COMM_TYPE_PING, *msg.data))
    
    node.create_subscription(std_msgs.msg.UInt16MultiArray, 'ping', ping_cb, rclpy.qos.qos_profile_sensor_data)
    
    # PID 설정 구독
    def set_pid_cb(msg: std_msgs.msg.Float32MultiArray):
        logger.info(f'set_pid: {msg.data}')
        left_arm_controller.set_pid(*msg.data)
        right_arm_controller.set_pid(*msg.data)
    
    node.create_subscription(std_msgs.msg.Float32MultiArray, 'set_pid', set_pid_cb, rclpy.qos.qos_profile_sensor_data)

    try:
        rclpy.spin(node)
    except KeyboardInterrupt as err:
        left_arm_controller.stop()
        right_arm_controller.stop()
        raise err

    # Destroy the node explicitly
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
