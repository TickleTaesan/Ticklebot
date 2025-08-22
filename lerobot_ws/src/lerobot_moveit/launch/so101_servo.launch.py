import os
from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, Command
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from moveit_configs_utils import MoveItConfigsBuilder


def generate_launch_description():

    hardware_plugin_arg = DeclareLaunchArgument(
        name="hardware_plugin", default_value="ign_ros2_control/IgnitionSystem"
    )

    # Build MoveIt configs (URDF/SRDF/controllers)
    lerobot_description_dir = get_package_share_directory("lerobot_description")
    so101_urdf_path = os.path.join(lerobot_description_dir, "urdf", "so101.urdf.xacro")

    moveit_config = (
        MoveItConfigsBuilder("so101", package_name="lerobot_moveit")
        .robot_description(file_path=so101_urdf_path)
        .robot_description_semantic(file_path="config/so101.srdf")
        .trajectory_execution(file_path="config/moveit_controllers.yaml")
        .to_moveit_configs()
    )

    # MoveIt Servo parameters
    moveit_pkg = get_package_share_directory("lerobot_moveit")
    servo_yaml = os.path.join(moveit_pkg, "config", "servo.yaml")

    servo_node = Node(
        package="moveit_servo",
        executable="servo_node_main",
        name="servo_node",
        output="screen",
        parameters=[
            moveit_config.robot_description,
            moveit_config.robot_description_semantic,
            moveit_config.robot_description_kinematics,
            moveit_config.joint_limits,
            servo_yaml,
        ],
    )

    return LaunchDescription([
        hardware_plugin_arg,
        servo_node
    ])


