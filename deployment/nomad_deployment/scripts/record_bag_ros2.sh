#!/usr/bin/env bash
set -e

# Usage: ./record_bag_ros2.sh <bag_name>

if [ -z "$1" ]; then
  echo "Usage: $0 <bag_name>"
  exit 1
fi

bag_name="$1"

echo "Recording /usb_cam/image_raw to $bag_name"
ros2 bag record /usb_cam/image_raw -o "$bag_name"


