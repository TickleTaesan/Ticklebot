from setuptools import setup
import os
from glob import glob

package_name = 'nomad_ros2'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.py')),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Your Name',
    maintainer_email='your-email@example.com',
    description='General Navigation Models (GNM, ViNT, NoMaD) for ROS2',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'navigate_node = nomad_ros2.navigate_node:main',
            'pd_controller_node = nomad_ros2.pd_controller_node:main',
            'joy_teleop_node = nomad_ros2.joy_teleop_node:main',
            'explore_node = nomad_ros2.explore_node:main',
            'create_topomap_node = nomad_ros2.create_topomap_node:main',
        ],
    },
) 