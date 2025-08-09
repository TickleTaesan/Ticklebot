# Astra Control System: Python & Firmware Integration

This document outlines the architecture and data flow between the central ROS2 Python controller (`astra_controller.py`) and the distributed ESP32-based firmware modules (`AstraArmController`, `AstraHeadController`, `AstraLiftController`, etc.).

## 1. System Architecture

The system is designed with a **centralized controller** and **distributed, specialized microcontrollers**.

-   **`astra_controller.py` (The Brain)**: This is a high-level ROS2 node that serves as the main interface for the robot. It aggregates all sensor data (camera images, joint states, odometry) into a unified observation space and dispatches high-level commands (e.g., "set all joint angles") to the appropriate hardware controllers. It communicates with other parts of the system using ROS2 topics.

-   **Hardware-Specific Nodes (e.g., `arm_node.py`)**: These are intermediate ROS2 nodes (one for each physical controller) that bridge the gap between the ROS2 network and the physical hardware. They subscribe to command topics from `astra_controller.py` and translate them into serial packets for the ESP32 firmware. They also listen for serial data from the firmware, parse it, and publish it onto ROS2 topics like `/joint_states`.

-   **Firmware (`AstraFirmwares`)**: Each major component of the robot (Arm, Head, Lift) has its own ESP32 microcontroller running dedicated firmware. This modular approach offloads real-time tasks like PID control and trajectory execution from the main computer. The `.gitmodules` file confirms this structure with separate submodules for `AstraArmController`, `AstraLiftController`, and `AstraHeadController`.

The overall data flow is as follows:

```mermaid
graph TD
    subgraph ROS2 Domain
        A[astra_controller.py]
        B[arm_node.py]
        C[head_node.py]
        D[lift_node.py]
    end

    subgraph Firmware Domain (ESP32)
        E[AstraArmController]
        F[AstraHeadController]
        G[AstraLiftController]
    end

    subgraph Physical Hardware
        H[Arm Motors]
        I[Head Servos]
        J[Lift Stepper]
    end

    A -- ROS Topic<br>right/arm/joint_command --> B
    B -- Serial<br>(/dev/tty_puppet_right) --> E
    E -- PWM/Serial --> H

    A -- ROS Topic<br>head/joint_command --> C
    C -- Serial<br>(/dev/tty_head) --> F
    F -- PWM/Serial --> I

    A -- ROS Topic<br>right/lift/joint_command --> D
    D -- Serial<br>(/dev/tty_puppet_lift_right) --> G
    G -- Step/Dir --> J

    H -- Encoder Feedback --> E
    I -- Position Feedback --> F
    J -- Position Feedback --> G

    E -- Serial Feedback --> B
    F -- Serial Feedback --> C
    G -- Serial Feedback --> D

    B -- ROS Topic<br>/joint_states --> A
    C -- ROS Topic<br>/joint_states --> A
    D -- ROS Topic<br>/joint_states --> A
```

## 2. Communication Protocol (`comm.cpp` & `comm.h`)

All firmware modules share a standardized serial communication protocol defined in their respective `comm.cpp` files. This ensures that the Python-side controllers can communicate with any module using the same packet structure.

-   **Packet Structure**: A simple format of `[Header (0x5A)][Type][Payload][Checksum]`.
-   **`comm_type_t`**: An enum defines the message types, which are the core of the command system (e.g., `COMM_TYPE_CTRL`, `COMM_TYPE_TORQUE`).
-   **Key Functions**:
    -   `comm_recv_poll_last()`: This is the primary function used in the `loop()` of each firmware's `main.cpp`. It continuously checks the serial buffer for the latest complete packet, discarding older ones to ensure real-time responsiveness.
    -   `comm_send_blocking()`: Used by the firmware to send feedback packets (`COMM_TYPE_FEEDBACK`) back to the host computer.

## 3. Python Orchestrator (`astra_controller.py`)

This class is the central hub of the entire system.

-   **`__init__(self, space=None)`**:
    -   Initializes the ROS2 node (`arm_node`).
    -   **Subscribers**: It subscribes to a wide range of topics to gather a complete state of the robot.
        -   `sensor_msgs.msg.Image`: Listens to three camera topics to get visual feedback.
        -   `sensor_msgs.msg.JointState`: Aggregates position data from all joints.
        -   `nav_msgs.msg.Odometry`: Gets the base's position and velocity.
        -   `astra_controller_interfaces.msg.JointCommand` & `geometry_msgs.msg.PoseStamped`: Listens to command topics from a teleoperation source (the "leader" robot).
    -   **Publishers**: It creates publishers for each hardware controller. These are used to dispatch commands.
        -   `left_arm_joint_command_publisher`, `right_arm_joint_command_publisher`, etc.

-   **`write_goal_position(self, goal_pos)`**:
    -   **Connection**: This is the primary action-issuing function. It takes a list of target joint positions.
    -   It de-multiplexes this list and publishes smaller, targeted `JointCommand` messages to the specific topics for the arm, lift, and gripper controllers (e.g., `left/arm/joint_command`).
    -   The hardware-specific nodes (like `arm_node.py`) are listening on these topics.

-   **`read_present_position(self)`** and **`read_cameras(self)`**:
    -   **Connection**: These are the primary state-gathering functions.
    -   They read the latest data stored by the subscriber callbacks (`self.joint_states`, `self.images`).
    -   This provides a complete, time-synchronized snapshot of the robot's state (all joint angles, end-effector poses, camera images) for use by a higher-level policy (e.g., an RL agent).

## 4. Firmware Modules (Examples)

### `AstraArmController` (Complex, Real-Time Control)

-   **`main.cpp` -> `loop()`**:
    -   **Connection**: Receives `COMM_TYPE_CTRL` packets sent by `arm_node.py`.
    -   The payload (target positions) is extracted from the packet.
    -   If `EIShaper_enabled` is true, it calls **`EIShaperApply()`** to filter the target positions for smoother motion.
    -   It then calls **`dualMotorUpdatePos(pos)`** to pass the setpoints to the motor control module.

-   **`dualMotor.cpp` -> `dualMotorUpdatePos(pos[])`**:
    -   **Connection**: This function receives the desired joint positions from `main.cpp`.
    -   For each joint, it calls **`traj[i].planTrapezoidal(...)`** to generate a smooth trajectory from the current position to the new goal.

-   **`dualMotor.cpp` -> `timer_callback()`**:
    -   This is a high-frequency hardware timer interrupt (approx. 66.7 Hz). This is where the time-critical control happens, independent of the main `loop()`.
    -   It calls `traj[i].update()` which gets the next step from the trapezoidal trajectory planner (`trapTraj.cpp`).
    -   It performs the PID control calculations (P, I, and D terms, plus friction and backlash compensation).
    -   It directly commands the servos using `sts.writeWord()`.
    -   It calls `read_pos()` to get feedback from the encoders for the next PID cycle.
