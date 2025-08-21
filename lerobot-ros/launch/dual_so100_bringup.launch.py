#!/usr/bin/env python

import os
from pathlib import Path
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, GroupAction, IncludeLaunchDescription, SetEnvironmentVariable
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution, Command
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node, PushRosNamespace
from ament_index_python.packages import get_package_share_directory
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    """Launch dual SO-100 robots with separate namespaces."""

    use_sim_time_arg = DeclareLaunchArgument(
        "use_sim_time",
        default_value="true",
        description="Use simulation time",
    )

    # Package directories
    lerobot_description_dir = get_package_share_directory("lerobot_description")
    lerobot_controller_dir = get_package_share_directory("lerobot_controller")
    lerobot_moveit_dir = get_package_share_directory("lerobot_moveit")

    # Gazebo resource path
    gazebo_resource_path = SetEnvironmentVariable(
        name="GZ_SIM_RESOURCE_PATH",
        value=[str(Path(lerobot_description_dir).parent.resolve())],
    )

    # URDF/xacro model and robot_description
    model_arg = DeclareLaunchArgument(
        name="model",
        default_value=os.path.join(lerobot_description_dir, "urdf", "so101_gazebo.xacro"),
        description="Absolute path to robot xacro file",
    )
    robot_description = ParameterValue(Command(["xacro ", LaunchConfiguration("model")]), value_type=str)

    # Left arm group
    left_arm_group = GroupAction(
        [
            PushRosNamespace("left_arm"),
            Node(
                package="ros_gz_sim",
                executable="create",
                name="spawn_left_arm",
                arguments=[
                    "-topic",
                    "/left_arm/robot_description",
                    "-name",
                    "left_so101",
                    "-x",
                    "-0.3",
                    "-y",
                    "0.0",
                    "-z",
                    "0.0",
                ],
                output="screen",
            ),
            Node(
                package="robot_state_publisher",
                executable="robot_state_publisher",
                name="robot_state_publisher",
                parameters=[
                    {"robot_description": robot_description},
                    {"use_sim_time": LaunchConfiguration("use_sim_time")},
                ],
            ),
            Node(
                package="controller_manager",
                executable="ros2_control_node",
                name="controller_manager",
                parameters=[
                    {"robot_description": robot_description},
                    {"use_sim_time": LaunchConfiguration("use_sim_time")},
                    PathJoinSubstitution([lerobot_controller_dir, "config", "so101_controllers.yaml"]),
                ],
            ),
            Node(
                package="controller_manager",
                executable="spawner",
                name="arm_controller_spawner",
                arguments=["arm_controller", "gripper_controller", "joint_state_broadcaster"],
            ),
        ]
    )

    # Right arm group
    right_arm_group = GroupAction(
        [
            PushRosNamespace("right_arm"),
            Node(
                package="ros_gz_sim",
                executable="create",
                name="spawn_right_arm",
                arguments=[
                    "-topic",
                    "/right_arm/robot_description",
                    "-name",
                    "right_so101",
                    "-x",
                    "0.3",
                    "-y",
                    "0.0",
                    "-z",
                    "0.0",
                ],
                output="screen",
            ),
            Node(
                package="robot_state_publisher",
                executable="robot_state_publisher",
                name="robot_state_publisher",
                parameters=[
                    {"robot_description": robot_description},
                    {"use_sim_time": LaunchConfiguration("use_sim_time")},
                ],
            ),
            Node(
                package="controller_manager",
                executable="ros2_control_node",
                name="controller_manager",
                parameters=[
                    {"robot_description": robot_description},
                    {"use_sim_time": LaunchConfiguration("use_sim_time")},
                    PathJoinSubstitution([lerobot_controller_dir, "config", "so101_controllers.yaml"]),
                ],
            ),
            Node(
                package="controller_manager",
                executable="spawner",
                name="arm_controller_spawner",
                arguments=["arm_controller", "gripper_controller", "joint_state_broadcaster"],
            ),
        ]
    )

    # Gazebo
    gazebo_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            [
                PathJoinSubstitution(
                    [get_package_share_directory("ros_gz_sim"), "launch", "gz_sim.launch.py"]
                )
            ]
        ),
        launch_arguments=[("gz_args", ["-v 4 -r empty.sdf"])],
    )

    # Clock bridge
    clock_bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        name="clock_bridge",
        arguments=["/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock"],
        output="screen",
    )

    return LaunchDescription(
        [
            model_arg,
            gazebo_resource_path,
            use_sim_time_arg,
            gazebo_launch,
            left_arm_group,
            right_arm_group,
            clock_bridge,
        ]
    )


