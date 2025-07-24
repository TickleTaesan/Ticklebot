#!/bin/bash

# ROS2 Nomad Package Build Script

echo "Building ROS2 Nomad package..."

# Check if we're in a ROS2 workspace
if [ ! -f "src/CMakeLists.txt" ]; then
    echo "Error: This script must be run from a ROS2 workspace root directory"
    echo "Please run: mkdir -p ~/ros2_ws/src && cd ~/ros2_ws/src"
    echo "Then copy this package to ~/ros2_ws/src/nomad_ros2"
    exit 1
fi

# Install dependencies
echo "Installing dependencies..."
sudo apt update
sudo apt install -y \
    python3-colcon-common-extensions \
    python3-pip \
    ros-humble-cv-bridge \
    ros-humble-image-transport \
    ros-humble-usb-cam \
    ros-humble-joy \
    ros-humble-tf2-ros \
    ros-humble-tf2-geometry-msgs

# Install Python dependencies
pip3 install torch torchvision torchaudio
pip3 install diffusers transformers
pip3 install opencv-python pillow matplotlib

# Build the package
echo "Building package with colcon..."
colcon build --packages-select nomad_ros2

if [ $? -eq 0 ]; then
    echo "Build successful!"
    echo "To run the package:"
    echo "1. Source the workspace: source install/setup.bash"
    echo "2. Run the launch file: ros2 launch nomad_ros2 nomad_launch.py"
else
    echo "Build failed!"
    exit 1
fi 