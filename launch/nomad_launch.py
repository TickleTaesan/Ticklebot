#!/usr/bin/env python3

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    # Get package directory
    pkg_share = FindPackageShare('nomad_ros2')
    
    # Launch arguments
    model_arg = DeclareLaunchArgument(
        'model',
        default_value='nomad',
        description='Model name (nomad, vint, gnm)'
    )
    
    topomap_dir_arg = DeclareLaunchArgument(
        'topomap_dir',
        default_value='topomap',
        description='Topomap directory name'
    )
    
    goal_node_arg = DeclareLaunchArgument(
        'goal_node',
        default_value='-1',
        description='Goal node index (-1 for last node)'
    )
    
    mode_arg = DeclareLaunchArgument(
        'mode',
        default_value='navigate',
        description='Operation mode (navigate, explore)'
    )
    
    # Configuration files
    camera_config = PathJoinSubstitution([
        pkg_share, 'config', 'camera_front.yaml'
    ])
    
    joystick_config = PathJoinSubstitution([
        pkg_share, 'config', 'joystick.yaml'
    ])
    
    robot_config = PathJoinSubstitution([
        pkg_share, 'config', 'robot.yaml'
    ])
    
    models_config = PathJoinSubstitution([
        pkg_share, 'config', 'models.yaml'
    ])
    
    # USB Camera node
    usb_cam_node = Node(
        package='usb_cam',
        executable='usb_cam_node_exe',
        name='usb_cam',
        output='screen',
        parameters=[camera_config]
    )
    
    # Joystick node
    joy_node = Node(
        package='joy',
        executable='joy_node',
        name='joy_node',
        parameters=[joystick_config]
    )
    
    # PD Controller node (always needed)
    pd_controller_node = Node(
        package='nomad_ros2',
        executable='pd_controller_node',
        name='pd_controller_node',
        output='screen',
        parameters=[robot_config]
    )
    
    # Joy Teleop node (always needed for manual control)
    joy_teleop_node = Node(
        package='nomad_ros2',
        executable='joy_teleop_node',
        name='joy_teleop_node',
        output='screen',
        parameters=[robot_config]
    )
    
    # Conditional nodes based on mode
    navigate_node = Node(
        package='nomad_ros2',
        executable='navigate_node',
        name='navigate_node',
        output='screen',
        parameters=[
            {'model': LaunchConfiguration('model')},
            {'topomap_dir': LaunchConfiguration('topomap_dir')},
            {'goal_node': LaunchConfiguration('goal_node')},
            {'waypoint': 2},
            {'close_threshold': 3},
            {'radius': 4},
            {'num_samples': 8}
        ],
        condition=LaunchConfiguration('mode').equals('navigate')
    )
    
    explore_node = Node(
        package='nomad_ros2',
        executable='explore_node',
        name='explore_node',
        output='screen',
        parameters=[
            {'model': LaunchConfiguration('model')},
            {'waypoint': 2},
            {'num_samples': 8}
        ],
        condition=LaunchConfiguration('mode').equals('explore')
    )
    
    # Create launch description
    return LaunchDescription([
        model_arg,
        topomap_dir_arg,
        goal_node_arg,
        mode_arg,
        usb_cam_node,
        joy_node,
        pd_controller_node,
        joy_teleop_node,
        navigate_node,
        explore_node
    ]) 