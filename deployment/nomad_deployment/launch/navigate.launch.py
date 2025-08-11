from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration


def generate_launch_description() -> LaunchDescription:
    use_camera = LaunchConfiguration('use_camera', default='false')
    model = LaunchConfiguration('model', default='nomad')
    config = LaunchConfiguration('config', default='')
    topomap_dir = LaunchConfiguration('dir', default='topomap')
    goal_node = LaunchConfiguration('goal_node', default='-1')
    waypoint = LaunchConfiguration('waypoint', default='2')
    close_threshold = LaunchConfiguration('close_threshold', default='3')
    radius = LaunchConfiguration('radius', default='4')

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

    # Navigate node
    nodes.append(
        Node(
            package='nomad_deployment',
            executable='navigate',
            name='navigate',
            parameters=[{
                'model': model,
                'config': config,
                'dir': topomap_dir,
                'goal_node': goal_node,
                'waypoint': waypoint,
                'close_threshold': close_threshold,
                'radius': radius,
            }],
            output='screen',
        )
    )

    return LaunchDescription([
        DeclareLaunchArgument('use_camera', default_value='false'),
        DeclareLaunchArgument('model', default_value='nomad'),
        DeclareLaunchArgument('config', default_value=''),
        DeclareLaunchArgument('dir', default_value='topomap'),
        DeclareLaunchArgument('goal_node', default_value='-1'),
        DeclareLaunchArgument('waypoint', default_value='2'),
        DeclareLaunchArgument('close_threshold', default_value='3'),
        DeclareLaunchArgument('radius', default_value='4'),
        *nodes,
    ])


