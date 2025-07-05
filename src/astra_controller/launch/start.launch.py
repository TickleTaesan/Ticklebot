from pathlib import Path
from ament_index_python import get_package_share_directory

from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    GroupAction
)
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, Command

from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue

from srdfdom.srdf import SRDF

def generate_launch_description():
    ld = LaunchDescription()
    
    package_name = 'astra_controller'
    package_path = Path(get_package_share_directory(package_name))
    
    ld.add_action(
        DeclareLaunchArgument(
            "rviz_config",
            default_value=str(package_path / "config/default.rviz"),
        )
    )
    
    # # Cameras
    # ld.add_action(
    #     Node(
    #         package='usb_cam', executable='usb_cam_node_exe',
    #         namespace='cam_head',
    #         parameters=[{
    #             'video_device': '/dev/video_head',
    #             'pixel_format': 'mjpeg2rgb',
    #             'image_width': 640,
    #             'image_height': 360,
    #             'framerate': 30.0,
    #         }],
    #         output={'both': 'log'},
    #     )
    # )
    # ld.add_action(
    #     Node(
    #         package='usb_cam', executable='usb_cam_node_exe',
    #         namespace='left/cam_wrist',
    #         parameters=[{
    #             'video_device': '/dev/video_wrist_left',
    #             'pixel_format': 'mjpeg2rgb',
    #             'image_width': 640,
    #             'image_height': 360,
    #             'framerate': 30.0,
    #         }],
    #         output={'both': 'log'},
    #     )
    # )
    # ld.add_action(
    #     Node(
    #         package='usb_cam', executable='usb_cam_node_exe',
    #         namespace='right/cam_wrist',
    #         parameters=[{
    #             'video_device': '/dev/video_wrist_right',
    #             'pixel_format': 'mjpeg2rgb',
    #             'image_width': 640,
    #             'image_height': 360,
    #             'framerate': 30.0,
    #         }],
    #         output={'both': 'log'},
    #     )
    # )
    
    # Fake Arms
    ld.add_action(
        Node(
            package=package_name,
            executable="dry_run_node",
            namespace='left',
            parameters=[{
                'joint_names': [ "joint_l2", "joint_l3", "joint_l4", "joint_l5", "joint_l6" ],
                'actively_send_joint_state': True
            }],
            remappings=[
                ('joint_states', '/joint_states'),
            ],
            output='screen',
        )
    )
    
    ld.add_action(
        Node(
            package=package_name,
            executable="dry_run_node",
            namespace='right',
            parameters=[{
                'joint_names': [ "joint_r2", "joint_r3", "joint_r4", "joint_r5", "joint_r6" ],
                'actively_send_joint_state': True
            }],
            remappings=[
                ('joint_states', '/joint_states'),
            ],
            output='screen',
        )
    )
    
    # IK
    ld.add_action(
        Node(
            package=package_name,
            executable="ik_node",
            namespace='left',
            parameters=[{
                'eef_link_name': 'l_wrist_2_link',
                'joint_names': ['joint_l2', 'joint_l3', 'joint_l4', 'joint_l5', 'joint_l6'],
            }],
            output='screen',
        )
    )
    
    ld.add_action(
        Node(
            package=package_name,
            executable="ik_node",
            namespace='right',
            parameters=[{
                'eef_link_name': 'r_wrist_2_link',
                'joint_names': ['joint_r2', 'joint_r3', 'joint_r4', 'joint_r5', 'joint_r6'],
            }],
            output='screen',
        )
    )
    
    # # Base
    # ld.add_action(
    #     Node(
    #         package=package_name,
    #         executable="base_node",
    #         parameters=[{
    #             'device': 'can0',
    #         }],
    #     )
    # )
    
    # # Head
    # ld.add_action(
    #     Node(
    #         package=package_name,
    #         executable="head_node",
    #         namespace='head',
    #         parameters=[{
    #             'device': '/dev/tty_head',
    #         }],
    #         remappings=[
    #             ('joint_states', '/joint_states'),
    #         ],
    #         output='screen',
    #         emulate_tty=True,
    #     )
    # )
    
    # Teleop (Web)
    ld.add_action(
        Node(
            package=package_name,
            executable="teleop_web_node",
            output='screen',
            emulate_tty=True,
        )
    )
    
    # Robot State Publisher
    ld.add_action(
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource([
                str(Path(get_package_share_directory('tickle_taesan_moveit'))
                    / 'launch' / 'rsp.launch.py')
            ])
        )
    )

    # Add test goal pose node
    test_goal_pose_node = Node(
        package='astra_controller',
        executable='test_goal_pose_node',
        name='test_goal_pose_node',
        output='screen'
    )
    ld.add_action(test_goal_pose_node)
    
    return ld
