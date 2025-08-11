from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description() -> LaunchDescription:
    camera_type = LaunchConfiguration('camera', default='v4l2')
    run_explore = LaunchConfiguration('run_explore', default='false')

    ld = []

    # Joystick node (ROS2)
    ld.append(
        Node(
            package='joy',
            executable='joy_node',
            name='joy_node',
            parameters=[{'deadzone': 0.05, 'autorepeat_rate': 20.0}],
            output='screen',
        )
    )

    # Camera node (choose v4l2 by default) with YAML params
    ld.append(
        Node(
            package='v4l2_camera',
            executable='v4l2_camera_node',
            name='camera',
            output='screen',
            parameters=[
                os.path.join(get_package_share_directory('nomad_deployment'), 'config', 'camera_front.yaml')
            ],
        )
    )

    # twist_mux (ROS2 replacement of yocs_cmd_vel_mux)
    ld.append(
        Node(
            package='twist_mux',
            executable='twist_mux',
            name='twist_mux',
            parameters=[
                {'topics': {
                    'teleop': {'topic': '/cmd_vel/teleop', 'timeout': 0.5, 'priority': 100},
                    'nav': {'topic': '/cmd_vel/nav', 'timeout': 0.5, 'priority': 50},
                }, 'locks': {
                    'e_stop': {'topic': '/e_stop', 'timeout': 0.0, 'priority': 255}
                }}
            ],
            remappings=[('/cmd_vel_out', '/cmd_vel')],
            output='screen',
        )
    )

    # Joy teleop node
    ld.append(
        Node(
            package='nomad_deployment',
            executable='joy_teleop',
            name='joy_teleop',
            parameters=[
                {
                    'max_v': 0.4,
                    'max_w': 0.8,
                    'deadman_switch': 4,
                    'lin_vel_axis': 1,
                    'ang_vel_axis': 0,
                    'publish_rate': 9.0,
                    'vel_topic': '/cmd_vel/teleop',
                    'joy_bumper_topic': '/joy_bumper',
                }
            ],
            output='screen',
        )
    )

    # PD controller node (consumes /waypoint -> publishes /cmd_vel/nav)
    ld.append(
        Node(
            package='nomad_deployment',
            executable='pd_controller',
            name='pd_controller',
            parameters=[os.path.join(get_package_share_directory('nomad_deployment'), 'config', 'pd_controller.yaml')],
            output='screen',
        )
    )

    # Optional exploration node (disabled by default)
    ld.append(
        Node(
            package='nomad_deployment',
            executable='explore',
            name='explore',
            parameters=[{'model': 'nomad'}],
            output='screen',
            condition=None,  # can be toggled via a separate launch file
        )
    )

    return LaunchDescription([
        DeclareLaunchArgument('camera', default_value='v4l2'),
        DeclareLaunchArgument('run_explore', default_value='false'),
        *ld,
    ])


