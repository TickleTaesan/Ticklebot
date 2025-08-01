# AstraArmController Firmware Code Explanation (Single-Motor Version)

## 1. File/Module Overview

- **main.cpp**: Main entry point, handles setup, main loop, and command dispatch.
- **dualMotor.cpp / dualMotor.h**: (Now single-motor logic) Motor control, position update, PID loop, and trajectory planning.
- **comm.cpp / comm.h**: Serial communication protocol implementation.
- **config.cpp / config.h**: Configuration structure, persistent storage, and parameter management.
- **trapTraj.cpp / trapTraj.hpp**: Trapezoidal trajectory planning for smooth motion.
- **EIShaper.cpp**: Optional vibration suppression filter for position commands.

---

## 2. Initialization Flow

```cpp
void setup() {
    comm_init();           // Initialize serial communication
    configInit();          // Load configuration from flash
    dualMotorSetup();      // Setup single-motor joints
    setupTorque(0);        // Disable torque initially
}
```
- Serial port is initialized at 921600 baud.
- Configuration is loaded (or created with defaults if missing).
- Each joint (6 total) is initialized as a single-motor actuator.
- Torque is disabled for safety at startup.

---

## 3. Main Control Loop

- Runs at 66.67Hz (15ms timer interrupt)
- Reads joint positions from servos
- Updates trajectory and PID for each joint
- Sends PWM commands to servos
- Handles incoming serial commands (position, config, PID, etc.)

**Timer callback example:**
```cpp
void timer_callback(void *arg) {
    read_pos();  // Read encoder positions
    for (int i = 0; i < JOINT_NUM; ++i) {
        float err = goal_pos[i] - last_pos[i];
        float p_out = kp * err;
        // ... PID calculations
        out[i] = p_out + i_out[i] + d_out;
    }
    // Send PWM commands to servos
    for (int i = 0; i < JOINT_NUM; ++i) {
        sts.writeWord(4 + i, SCSCL_GOAL_TIME_L, ready_send);
    }
}
```

---

## 4. Communication Protocol

- **Serial protocol** with header, type, payload, and checksum
- Handles commands for position, feedback, torque, config, PID tuning, and initialization
- Example packet structure:
  - `[Header][Type][Payload][Checksum]`
  - Header: `0x5A`
  - Type: 1 byte
  - Payload: 16 or 32 bytes
  - Checksum: sum of type + payload

**Key packet types:**
- `COMM_TYPE_CTRL`: Position command for all joints
- `COMM_TYPE_FEEDBACK`: Position/velocity feedback
- `COMM_TYPE_TORQUE`: Enable/disable torque
- `COMM_TYPE_PIDTUNE`: Update PID parameters

---

## 5. Trajectory and PID Control

- **Trapezoidal Trajectory**: Plans smooth motion for each joint, respecting velocity and acceleration limits
- **PID Controller**: Advanced PID with anti-windup, dual-gain, and stiction compensation
- **EIShaper**: Optional filter for vibration suppression

**Trajectory planning example:**
```cpp
bool TrapezoidalTrajectory::planTrapezoidal(float Xf, float Xi, float Vi) {
    // Plans acceleration, cruise, and deceleration phases
    // Returns true if successful
}
```

**PID update example:**
```cpp
for (int i = 0; i < JOINT_NUM; ++i) {
    float err = goal_pos[i] - last_pos[i];
    float p_out = kp * err;
    // ... integral and derivative terms
    out[i] = p_out + i_out[i] + d_out;
}
```

---

## 6. Configuration Management

- All parameters (velocity, acceleration, PID, EIShaper, etc.) are stored in a `config_t` struct
- Configuration is saved/loaded from ESP32's LittleFS filesystem
- Parameters can be updated at runtime via serial commands

**Config struct example:**
```cpp
struct config_t {
  int version;
  int EIShaper_enabled;
  float joint_vel_max;
  float joint_acc;
  int init_pos[JOINT_NUM];
  // ...
};
```

---

## 7. Key Functions and Data Structures

- `dualMotorUpdatePos(uint16_t pos[])`: Updates target positions for all joints
- `dualMotorReadPos(uint16_t read_pos[])`: Reads current positions from all servos
- `setupTorque(int enable)`: Enables/disables torque for all joints
- `TrapezoidalTrajectory`: Class for planning and evaluating joint motion
- `comm_send_blocking()`, `comm_recv_poll()`: Serial communication helpers
- `configInit()`, `write_config()`, `read_config()`: Persistent config management

---

## Summary

The AstraArmController firmware is now streamlined for a 6-DOF single-motor arm, with robust real-time control, advanced motion planning, and easy integration with ROS2. All code is modular, with clear separation between communication, control, and configuration logic. 