from setuptools import setup

package_name = 'nomad_deployment'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name, f'{package_name}.nodes'],
    data_files=[
        ('share/ament_index/resource_index/packages', [f'resource/{package_name}']),
        (f'share/{package_name}', ['package.xml']),
        (f'share/{package_name}/launch', [
            'launch/vint_locobot.launch.py',
            'launch/explore.launch.py',
            'launch/navigate.launch.py',
        ]),
        (f'share/{package_name}/config', [
            'config/twist_mux.yaml',
            'config/joystick.yaml',
            'config/camera_front.yaml',
        ]),
        (f'share/{package_name}/scripts', [
            'scripts/record_bag_ros2.sh',
            'scripts/create_topomap_ros2.sh',
        ]),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='maintainer',
    maintainer_email='user@example.com',
    description='ROS2 deployment nodes for NoMaD/ViNT navigation',
    license='MIT',
    entry_points={
        'console_scripts': [
            'joy_teleop = nomad_deployment.nodes.joy_teleop:main',
            'pd_controller = nomad_deployment.nodes.pd_controller:main',
            'explore = nomad_deployment.nodes.explore:main',
            'explore_dummy = nomad_deployment.nodes.explore_dummy:main',
            'image_dir_player = nomad_deployment.nodes.image_dir_player:main',
            'create_topomap = nomad_deployment.nodes.create_topomap:main',
            'path_viz = nomad_deployment.nodes.path_viz:main',
            'navigate = nomad_deployment.nodes.navigate:main',
        ],
    },
)


