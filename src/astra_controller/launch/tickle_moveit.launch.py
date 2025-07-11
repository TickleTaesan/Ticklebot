from moveit_configs_utils import MoveItConfigsBuilder
from moveit_configs_utils.launches import generate_spawn_controllers_launch

from launch import LaunchDescription
from launch.actions import (
    IncludeLaunchDescription,
    TimerAction,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import PathJoinSubstitution

from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare

def generate_launch_description():
    moveit_config = MoveItConfigsBuilder("astra_dual_so_arm", package_name="tickle_taesan_moveit").to_moveit_configs()
    
    # ================================================================
    # 시뮬레이션 모드 (현재 활성화)
    # ================================================================
    dry_run_node = Node(
        package="astra_controller",
        executable="dry_run_node",
        parameters=[{
            'actively_send_joint_state': True,
            'joint_names': [
                # 오른팔 joints
                "joint_r2", "joint_r3", "joint_r4", "joint_r5", "joint_r6", "joint_r7r",
                # 왼팔 joints  
                "joint_l2", "joint_l3", "joint_l4", "joint_l5", "joint_l6", "joint_l7l"
            ]
        }],
        output="screen",
    )

    # ================================================================
    # 하드웨어 모드 (현재 비활성화)
    # ================================================================
    # arm_node를 사용하여 실제 하드웨어 제어
    # arm_node = Node(
    #     package="astra_controller",
    #     executable="arm_node",
    #     output="screen",
    # )

    # Robot State Publisher
    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        name="robot_state_publisher",
        parameters=[moveit_config.robot_description],
        output="screen",
    )

    # Launch MoveIt
    move_group = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            str(moveit_config.package_path / "launch/move_group.launch.py")
        ),
        launch_arguments={
            "moveit_controller_manager": "moveit_simple_controller_manager/MoveItSimpleControllerManager",
            "moveit_controller_manager_yaml": str(moveit_config.package_path / "config/moveit_controllers.yaml"),
        }.items()
    )

    # Launch RViz
    rviz = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            str(moveit_config.package_path / "launch/moveit_rviz.launch.py")
        ),
    )

    # Add moveit pose bridge node
    moveit_pose_bridge_node = Node(
        package="astra_controller",
        executable="moveit_pose_bridge",
        output="screen",
    )

    # Add tickle moveit relay node
    tickle_moveit_relay_node = Node(
        package="astra_controller",
        executable="tickle_moveit_relay_node",
        output="screen",
    )

    return LaunchDescription([
        robot_state_publisher,
        dry_run_node,  # 시뮬레이션 모드용 (현재 활성화)
        #arm_node,        # 하드웨어 모드용 (현재 비활성화)
        TimerAction(period=5.0, actions=[move_group]),
        TimerAction(period=7.0, actions=[rviz]),
        TimerAction(period=10.0, actions=[moveit_pose_bridge_node]),
        TimerAction(period=10.0, actions=[tickle_moveit_relay_node]),
    ])