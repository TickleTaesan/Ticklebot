#!/usr/bin/env bash
set -e

# Usage: ./create_topomap_ros2.sh <topomap_name> <bag_path> [rate]

if [ -z "$1" ] || [ -z "$2" ]; then
  echo "Usage: $0 <topomap_name> <bag_path> [rate]"
  exit 1
fi

name="$1"
bag="$2"
rate="${3:-1.5}"

echo "Creating topomap '$name' from bag '$bag' at rate $rate"

# Start the saver
ros2 run nomad_deployment create_topomap --ros-args -p dir:="$name" &
saver_pid=$!

sleep 1

# Play the bag
ros2 bag play "$bag" --rate "$rate"

# Stop saver
kill $saver_pid || true

echo "Topomap saved under deployment/topomaps/images/$name"


