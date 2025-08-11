from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration


def generate_launch_description() -> LaunchDescription:
    use_camera = LaunchConfiguration('use_camera', default='false')
    model = LaunchConfiguration('model', default='nomad')
    config = LaunchConfiguration('config', default='')
    num_samples = LaunchConfiguration('num_samples', default='8')
    waypoint_index = LaunchConfiguration('waypoint', default='2')

    nodes = []

    # Optional camera
    nodes.append(
        Node(
            package='v4l2_camera',
            executable='v4l2_camera_node',
            name='camera',
            output='screen',
            parameters=[{'image_size': [640, 480]}],
            condition=IfCondition(use_camera),
        )
    )

    # twist_mux
    nodes.append(
        Node(
            package='twist_mux',
            executable='twist_mux',
            name='twist_mux',
            remappings=[('/cmd_vel_out', '/cmd_vel')],
            output='screen',
        )
    )

    # PD controller
    nodes.append(
        Node(
            package='nomad_deployment',
            executable='pd_controller',
            name='pd_controller',
            parameters=[{'vel_topic': '/cmd_vel/nav', 'waypoint_topic': '/waypoint', 'use_serial': False}],
            output='screen',
        )
    )

    # Path viz (optional but useful)
    nodes.append(
        Node(
            package='nomad_deployment',
            executable='path_viz',
            name='path_viz',
            output='screen',
        )
    )

    # Explore node
    nodes.append(
        Node(
            package='nomad_deployment',
            executable='explore',
            name='explore',
            parameters=[{
                'model': model,
                'config': config,
                'num_samples': num_samples,
                'waypoint_index': waypoint_index,
            }],
            output='screen',
        )
    )

    return LaunchDescription([
        DeclareLaunchArgument('use_camera', default_value='false'),
        DeclareLaunchArgument('model', default_value='nomad'),
        DeclareLaunchArgument('config', default_value=''),
        DeclareLaunchArgument('num_samples', default_value='8'),
        DeclareLaunchArgument('waypoint', default_value='2'),
        *nodes,
    ])


