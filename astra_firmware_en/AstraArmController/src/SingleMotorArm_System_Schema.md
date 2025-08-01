# AstraArmController: Single-Motor Arm System Schema

## Overview

The AstraArmController firmware now supports a 6-DOF robotic arm, with each joint actuated by a single servo motor. The system is designed for precise, real-time control and seamless integration with ROS2 via a serial protocol. All dual-motor and non-joint logic has been removed for simplicity and maintainability.

---

## System Architecture

```
┌─────────────────┐    Serial Communication    ┌──────────────────┐
│   arm_node.py   │ ←────────────────────────→ │ AstraArmController│
│   (ROS2 Node)   │    (921600 baud)           │   (ESP32)        │
│                 │                            │                  │
│ - Command       │                            │ - Motor Control  │
│ - Feedback      │                            │ - PID Control    │
│ - Configuration │                            │ - Trajectory     │
└─────────────────┘                            └──────────────────┘
```

- **ESP32**: Main controller, runs firmware and handles all 6 joints
- **SC/ST Servos**: 6 servos, one per joint (IDs 4-9)
- **Serial**: High-speed UART for host communication
- **OLED Display**: Status and debug info

---

## Data Flow

### 1. Initialization
- Firmware initializes serial, configuration, and motor control subsystems
- All joints are set up as single-motor actuators

### 2. Position Control
- ROS2 node sends position commands for 6 joints
- Firmware receives, optionally filters (EIShaper), and plans trapezoidal trajectories
- PID control loop runs at 66.67Hz, updating each joint's setpoint and output
- Feedback is sent back to the host

### 3. Configuration
- Parameters (velocity, acceleration, PID, EIShaper) can be updated at runtime
- Configuration is stored persistently in ESP32's LittleFS

---

## Key Features

- **Single-motor-per-joint**: Each of the 6 joints is controlled by a single servo, simplifying hardware and software
- **Trapezoidal Trajectory Planning**: Smooth, kinematically-constrained motion for each joint
- **PID Control**: Advanced PID with anti-windup, dual-gain, and stiction compensation
- **EIShaper Filtering**: Optional vibration suppression filter for position commands
- **Real-time Feedback**: Joint positions are read and reported at high frequency
- **ROS2 Integration**: Standardized interface for commands and feedback
- **Configuration Persistence**: All parameters are saved and loaded automatically

---

## Example Control Loop

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Timer     │───▶│   Read      │───▶│   PID       │
│ (66.67Hz)   │    │  Encoders   │    │  Control    │
└─────────────┘    └─────────────┘    └─────────────┘
                           │                   │
                           ▼                   ▼
                    ┌─────────────┐    ┌─────────────┐
                    │  Trajectory │    │   PWM       │
                    │  Planning   │    │  Output     │
                    └─────────────┘    └─────────────┘
```

---

## Differences from Previous (Dual Motor) System

- **No dual-motor logic**: All averaging, feedforward, and backlash compensation for dual motors are removed
- **No non-joint actuators**: Only 6 main joints are supported
- **Simplified configuration**: Only joint parameters are present

---

## Integration Points

- **ROS2 Node**: Sends/receives joint commands and feedback
- **Serial Protocol**: Efficient, robust communication for real-time control
- **OLED Display**: Visual status for debugging and monitoring

---

## File Revision
- This schema reflects the firmware as of the single-motor-per-joint refactor (Spring 2024) 