#!/bin/bash

# ROS2 Nomad Package Run Script

echo "Starting ROS2 Nomad package..."

# Check if ROS2 is sourced
if [ -z "$ROS_DISTRO" ]; then
    echo "Error: ROS2 environment not sourced"
    echo "Please run: source /opt/ros/humble/setup.bash"
    exit 1
fi

# Check if workspace is sourced
if [ ! -d "install" ]; then
    echo "Error: ROS2 workspace not built or not sourced"
    echo "Please run: source install/setup.bash"
    exit 1
fi

# Parse command line arguments
MODE=${1:-"navigate"}
MODEL=${2:-"nomad"}
TOPOMAP_DIR=${3:-"topomap"}
GOAL_NODE=${4:-"-1"}

echo "Starting Nomad with:"
echo "  Mode: $MODE"
echo "  Model: $MODEL"
echo "  Topomap: $TOPOMAP_DIR"
echo "  Goal Node: $GOAL_NODE"

# Validate mode
if [ "$MODE" != "navigate" ] && [ "$MODE" != "explore" ]; then
    echo "Error: Invalid mode. Use 'navigate' or 'explore'"
    exit 1
fi

# Run the launch file
ros2 launch nomad_ros2 nomad_launch.py \
    mode:=$MODE \
    model:=$MODEL \
    topomap_dir:=$TOPOMAP_DIR \
    goal_node:=$GOAL_NODE 