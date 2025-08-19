import os
from pathlib import Path
from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, SetEnvironmentVariable
from launch.substitutions import Command, LaunchConfiguration
from launch.launch_description_sources import PythonLaunchDescriptionSource

from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    lerobot_description = get_package_share_directory("lerobot_description")

    model_arg = DeclareLaunchArgument(name="model", default_value=os.path.join(
                                        lerobot_description, "urdf", "so101.urdf.xacro"
                                        ),
                                      description="Absolute path to robot urdf file"
    )

    gazebo_resource_path = SetEnvironmentVariable(
        name="IGN_GAZEBO_RESOURCE_PATH",
        value=[
            str(Path(lerobot_description).parent.resolve())
            ]
        )
    
    robot_description = ParameterValue(Command([
            "xacro ",
            LaunchConfiguration("model"),
        ]),
        value_type=str
    )

    robot_state_publisher_node = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        parameters=[{"robot_description": robot_description,
                     "use_sim_time": True}]
    )

    gazebo = IncludeLaunchDescription(
                PythonLaunchDescriptionSource([os.path.join(
                    get_package_share_directory("ros_ign_gazebo"), "launch"), "/ign_gazebo.launch.py"]),
                launch_arguments=[
                    ("ign_args", [" -v 4 -r empty.sdf "]
                    )
                ]
             )

    ign_spawn_entity = Node(
        package="ros_ign_gazebo",
        executable="create",
        output="screen",
        arguments=["-topic", "robot_description",
                   "-name", "so101"],
    )

    ign_ros2_bridge = Node(
        package="ros_ign_bridge",
        executable="parameter_bridge",
        arguments=[
            "/clock@rosgraph_msgs/msg/Clock[ignition.msgs.Clock",
        ]
    )

    return LaunchDescription([
        model_arg,
        gazebo_resource_path,
        robot_state_publisher_node,
        gazebo,
        ign_spawn_entity,
        ign_ros2_bridge
    ])