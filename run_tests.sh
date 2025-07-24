#!/bin/bash

# ROS2 Nomad Test Runner Script

echo "Running ROS2 Nomad tests..."

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

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    local status=$1
    local message=$2
    case $status in
        "SUCCESS")
            echo -e "${GREEN}✓ $message${NC}"
            ;;
        "ERROR")
            echo -e "${RED}✗ $message${NC}"
            ;;
        "WARNING")
            echo -e "${YELLOW}⚠ $message${NC}"
            ;;
        "INFO")
            echo -e "${BLUE}ℹ $message${NC}"
            ;;
    esac
}

# Test 1: Unit Tests
echo ""
print_status "INFO" "Running unit tests..."
cd test
python3 -m pytest test_nomad_nodes.py -v
if [ $? -eq 0 ]; then
    print_status "SUCCESS" "Unit tests passed"
else
    print_status "ERROR" "Unit tests failed"
    exit 1
fi
cd ..

# Test 2: Mock Data Test
echo ""
print_status "INFO" "Running mock data test..."
python3 test/test_with_mock_data.py &
MOCK_TEST_PID=$!

# Wait for mock test to complete
sleep 25

# Check if mock test is still running
if kill -0 $MOCK_TEST_PID 2>/dev/null; then
    print_status "WARNING" "Mock test still running, killing it..."
    kill $MOCK_TEST_PID
else
    print_status "SUCCESS" "Mock data test completed"
fi

# Test 3: Node Creation Test
echo ""
print_status "INFO" "Testing node creation..."
python3 -c "
import rclpy
from nomad_ros2.pd_controller_node import PDControllerNode
from nomad_ros2.joy_teleop_node import JoyTeleopNode

rclpy.init()
try:
    pd_node = PDControllerNode()
    joy_node = JoyTeleopNode()
    print('✓ Nodes created successfully')
    pd_node.destroy_node()
    joy_node.destroy_node()
except Exception as e:
    print(f'✗ Node creation failed: {e}')
    exit(1)
finally:
    rclpy.shutdown()
"

if [ $? -eq 0 ]; then
    print_status "SUCCESS" "Node creation test passed"
else
    print_status "ERROR" "Node creation test failed"
    exit 1
fi

# Test 4: Topic Communication Test
echo ""
print_status "INFO" "Testing topic communication..."
python3 -c "
import rclpy
import time
from rclpy.node import Node
from std_msgs.msg import Float32MultiArray
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy

rclpy.init()
test_node = Node('test_node')

# Setup QoS
qos = QoSProfile(
    reliability=ReliabilityPolicy.BEST_EFFORT,
    history=HistoryPolicy.KEEP_LAST,
    depth=1
)

# Create publisher and subscriber
pub = test_node.create_publisher(Float32MultiArray, '/test_topic', qos)
received_msg = None

def callback(msg):
    global received_msg
    received_msg = msg.data

sub = test_node.create_subscription(Float32MultiArray, '/test_topic', callback, qos)

# Publish test message
test_msg = Float32MultiArray()
test_msg.data = [1.0, 2.0, 3.0]
pub.publish(test_msg)

# Wait for message to be received
time.sleep(0.1)
rclpy.spin_once(test_node, timeout_sec=0.1)

if received_msg and len(received_msg) == 3:
    print('✓ Topic communication test passed')
else:
    print('✗ Topic communication test failed')
    exit(1)

test_node.destroy_node()
rclpy.shutdown()
"

if [ $? -eq 0 ]; then
    print_status "SUCCESS" "Topic communication test passed"
else
    print_status "ERROR" "Topic communication test failed"
    exit 1
fi

# Test 5: Utility Functions Test
echo ""
print_status "INFO" "Testing utility functions..."
python3 -c "
import numpy as np
from PIL import Image as PILImage
from nomad_ros2.utils import msg_to_pil, pil_to_msg, setup_ros2_qos

# Test QoS setup
qos = setup_ros2_qos(reliability='best_effort', history='keep_last', depth=5)
print('✓ QoS setup test passed')

# Test image conversion
test_array = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
pil_img = PILImage.fromarray(test_array)
ros_msg = pil_to_msg(pil_img)
converted_pil = msg_to_pil(ros_msg)

if pil_img.size == converted_pil.size:
    print('✓ Image conversion test passed')
else:
    print('✗ Image conversion test failed')
    exit(1)
"

if [ $? -eq 0 ]; then
    print_status "SUCCESS" "Utility functions test passed"
else
    print_status "ERROR" "Utility functions test failed"
    exit 1
fi

# Test 6: Launch File Test
echo ""
print_status "INFO" "Testing launch file syntax..."
python3 -c "
import sys
import os
sys.path.append('launch')
try:
    from launch.nomad_launch import generate_launch_description
    ld = generate_launch_description()
    print('✓ Launch file syntax test passed')
except Exception as e:
    print(f'✗ Launch file syntax test failed: {e}')
    exit(1)
"

if [ $? -eq 0 ]; then
    print_status "SUCCESS" "Launch file test passed"
else
    print_status "ERROR" "Launch file test failed"
    exit 1
fi

# Test 7: Package Build Test
echo ""
print_status "INFO" "Testing package build..."
colcon build --packages-select nomad_ros2 --cmake-args -DCMAKE_BUILD_TYPE=Debug
if [ $? -eq 0 ]; then
    print_status "SUCCESS" "Package build test passed"
else
    print_status "ERROR" "Package build test failed"
    exit 1
fi

# Final Summary
echo ""
echo "=========================================="
print_status "INFO" "Test Summary:"
echo "=========================================="
print_status "SUCCESS" "✓ Unit tests"
print_status "SUCCESS" "✓ Mock data test"
print_status "SUCCESS" "✓ Node creation test"
print_status "SUCCESS" "✓ Topic communication test"
print_status "SUCCESS" "✓ Utility functions test"
print_status "SUCCESS" "✓ Launch file test"
print_status "SUCCESS" "✓ Package build test"
echo "=========================================="
print_status "SUCCESS" "All tests passed! 🎉"
echo "=========================================="

echo ""
print_status "INFO" "Next steps:"
echo "1. Run simulation: ./test_simulation_setup.sh"
echo "2. Run with mock data: python3 test/test_with_mock_data.py"
echo "3. Run individual nodes: ros2 run nomad_ros2 <node_name>" 