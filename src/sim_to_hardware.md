# 시뮬레이션에서 하드웨어로 전환하기

이 문서는 현재 시뮬레이션 모드에서 실제 하드웨어 제어로 전환하기 위해 필요한 코드 변경 사항을 설명합니다.

## 1. Launch 파일 수정

### tickle_moveit.launch.py 수정
파일 위치: `src/astra_controller/launch/tickle_moveit.launch.py`

1. dry_run_node를 arm_node로 교체:
```python
# dry_run_node 비활성화
# dry_run_node = Node(
#     package="astra_controller",
#     executable="dry_run_node",
#     parameters=[{
#         'actively_send_joint_state': True,
#         'joint_names': [
#             # 오른팔 joints
#             "joint_r2", "joint_r3", "joint_r4", "joint_r5", "joint_r6", "joint_r7r",
#             # 왼팔 joints  
#             "joint_l2", "joint_l3", "joint_l4", "joint_l5", "joint_l6", "joint_l7l"
#         ]
#     }],
#     output="screen",
# )

# arm_node 활성화 (하드웨어 제어용 노드)
arm_node = Node(
    package='astra_controller',
    executable='arm_node',
    name='arm_node',
    parameters=[{
        'device': '/dev/tty_puppet_right',  # 하드웨어 통신 포트
        'joint_names': [
            "joint_r2", "joint_r3", "joint_r4", "joint_r5", "joint_r6"
        ],
        'gripper_joint_names': [
            "joint_r7l", "joint_r7r"
        ]
    }],
    output="screen",
)
```

2. ros2_control_node 활성화:
```python
# ros2_control_node 주석 해제
ros2_control_node = Node(
    package="controller_manager",
    executable="ros2_control_node",
    parameters=[
        moveit_config.robot_description,
        str(moveit_config.package_path / "config/ros2_controllers.yaml"),
    ],
    output="screen",
)
```

3. LaunchDescription 수정:
```python
return LaunchDescription([
    robot_state_publisher,
    # dry_run_node,  # 제거
    arm_node,        # 추가
    ros2_control_node,  # 주석 해제
    TimerAction(period=5.0, actions=[move_group]),
    TimerAction(period=7.0, actions=[rviz]),
    TimerAction(period=10.0, actions=[moveit_pose_bridge_node]),
    TimerAction(period=10.0, actions=[tickle_moveit_relay_node]),
])
```

## 2. 하드웨어 설정 확인사항

1. 통신 포트 설정
   - 로봇 팔 제어기: `/dev/tty_puppet_right` (기본값)
   - 포트가 다른 경우 launch 파일의 `device` 파라미터 수정
   
2. 하드웨어 초기화
   ```bash
   # 하드웨어 초기화 명령어
   ros2 run astra_controller init_hardware
   ```

## 3. 주의사항

1. 하드웨어 전환 전 반드시 다음을 확인:
   - 통신 포트가 정상적으로 연결됨
   - 하드웨어 초기화가 완료됨
   - E-stop이 접근 가능한 위치에 있음

2. 처음 실행 시:
   - 낮은 속도로 시작
   - 작은 움직임부터 테스트
   - 비상 정지 준비

## 4. 디버깅

문제 발생 시 다시 시뮬레이션 모드로 전환하려면:
1. launch 파일에서 `arm_node` 대신 `dry_run_node` 사용
2. ros2_control_node 다시 주석 처리
``` 