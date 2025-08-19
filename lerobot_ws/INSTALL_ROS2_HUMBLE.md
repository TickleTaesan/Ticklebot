# Installation Guide for ROS2 Humble with Gazebo Fortress

This guide will help you set up ROS2 Humble with Gazebo Fortress for the LeRobot workspace.

## Prerequisites

- Ubuntu 22.04 (Jammy Jellyfish)
- ROS2 Humble installed
- Gazebo Fortress installed

## Install ROS2 Humble

If you haven't installed ROS2 Humble yet, follow the official installation guide:

```bash
# Add ROS2 Humble repository
sudo apt update && sudo apt install software-properties-common
sudo add-apt-repository universe
sudo apt update && sudo apt install curl
sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) & signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) main" | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null

# Install ROS2 Humble
sudo apt update
sudo apt install ros-humble-desktop
```

## Install Gazebo Fortress

Install Gazebo Fortress (the successor to Gazebo Classic):

```bash
# Add Gazebo Fortress repository
sudo apt update && sudo apt install wget lsb-release gnupg
sudo wget https://packages.osrfoundation.org/gazebo.gpg -O /usr/share/keyrings/pkgs-osrf-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/pkgs-osrf-archive-keyring.gpg] http://packages.osrfoundation.org/gazebo/ubuntu-stable $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/gazebo-stable.list > /dev/null

# Install Gazebo Fortress
sudo apt update
sudo apt install gz-fortress
```

## Install ROS2-Gazebo Bridge (Fortress)

Install the ROS2-Gazebo Fortress bridge packages:

```bash
sudo apt install ros-humble-ros-ign
```

## Source ROS2 and Gazebo

Add these lines to your `~/.bashrc`:

```bash
# Source ROS2 Humble
source /opt/ros/humble/setup.bash

# Source Gazebo Fortress
source /usr/share/gz-fortress/setup.sh
```

Then reload your bashrc:

```bash
source ~/.bashrc
```

## Build the Workspace

```bash
cd ~/ros2_robot/lerobot_ws
colcon build
source install/setup.bash
```

## Test Installation

Run the version check script:

```bash
./check_versions.sh
```

## Launch Commands

- **Rviz Visualization**: `ros2 launch lerobot_description so101_display.launch.py`
- **Gazebo Simulation**: `ros2 launch lerobot_description so101_gazebo.launch.py`
- **Controller**: `ros2 launch lerobot_controller so101_controller.launch.py`
- **MoveIt**: `ros2 launch lerobot_moveit so101_moveit.launch.py`

## Troubleshooting

### Common Issues

1. **Gazebo not found**: Make sure you've sourced the Gazebo Fortress setup script
2. **ROS2 packages not found**: Ensure ROS2 Humble is properly sourced
3. **Build errors**: Check that all dependencies are installed with `rosdep install --from-paths src --ignore-src -r -y`
4. **Plugin not found**: Ensure you have `ros-humble-ros-ign` installed for Fortress compatibility

### Verify Versions

- ROS2: `ros2 --version` (should show Humble)
- Gazebo: `ign gazebo --version` (should show Fortress)
- ROS2-Gazebo: `ros2 pkg list | grep ros_ign`

### Key Differences from Garden

- **Gazebo Garden**: Uses `gz` commands and `ros_gz_*` packages
- **Gazebo Fortress**: Uses `ign` commands and `ros_ign_*` packages
- **Plugin names**: Garden uses `gz_ros2_control`, Fortress uses `ign_ros2_control`
