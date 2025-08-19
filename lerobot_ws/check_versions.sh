#!/bin/bash

echo "=== ROS2 and Gazebo Version Check ==="
echo ""

echo "ROS2 Version:"
ros2 --version
echo ""

echo "Gazebo Version:"
gz version
echo ""

echo "ROS2 Packages:"
ros2 pkg list | grep -E "(gazebo|gz|ros_gz)"
echo ""

echo "Gazebo Worlds Available:"
ls /usr/share/gz-sim/worlds/ 2>/dev/null || echo "No Gazebo Fortress worlds found in /usr/share/gz-sim/worlds/"
echo ""

echo "ROS2 Launch Files:"
find src/ -name "*.launch.py" -type f
echo ""

echo "=== Check Complete ==="
