 # AstraHeadController and head_node.py Integration

This document explains how the `head_node.py` ROS2 node interacts with the `AstraHeadController` ESP32 firmware to control the robot's head.

## System Architecture and Data Flow

The `AstraHeadController` system is a classic example of a host-controller architecture. The `head_node.py` script runs on a host computer (like a PC or Jetson) and communicates with the `AstraHeadController` firmware on an ESP32 via a serial connection.

The data flow can be visualized as follows:

```mermaid
graph TD
    subgraph Host Computer (ROS2)
        A["astra_controller_interfaces/JointCommand<br>(/head/joint_command Topic)"] --> B[head_node.py];
        B --> C["astra_controller.head_controller<br>(Python Class)"];
        C -- "Sends COMM_TYPE_CTRL Packet" --> D{Serial Port<br>e.g., /dev/tty_head};
        D -- "Receives COMM_TYPE_FEEDBACK" --> C;
        C -- "Invokes state_cb" --> B;
        B --> E["sensor_msgs/JointState<br>(/joint_states Topic)"];
    end

    subgraph ESP32 Firmware
        F[AstraHeadController/src/main.cpp] -- "Receives Serial Data" --> D;
        F -- "Parses Packets" --> G[AstraHeadController/src/comm.cpp];
        G -- "Executes Commands" --> H["SCServo Library<br>(Servo Communication)"];
        H -- "Reads Position" --> F;
        F -- "Sends Feedback" --> D;
    end

    subgraph Hardware
        H --> I[Physical Servos];
    end
```

### Key Components

1.  **`head_node.py`**:
    *   A ROS2 node that acts as the bridge between the ROS2 ecosystem and the physical head controller.
    *   **Subscribes** to the `/head/joint_command` topic to receive desired positions for the head's pan and tilt joints.
    *   **Publishes** the current state (position, velocity, effort) of the head joints to the `/joint_states` topic.
    *   Instantiates the `HeadController` Python class, which abstracts away the low-level serial communication.

2.  **`astra_controller.head_controller` (Python Class, inferred)**:
    *   This class (not shown, but its usage is clear in `head_node.py`) is responsible for the direct serial communication with the ESP32.
    *   **`set_pos(positions)`**: Takes an array of joint positions, formats them into a `COMM_TYPE_CTRL` byte packet according to the protocol in `comm.h`, and writes it to the serial port specified by the `device` parameter (e.g., `/dev/tty_head`).
    *   **`set_torque(enable)`**: Formats and sends a `COMM_TYPE_TORQUE` packet.
    *   It runs a background thread to continuously read from the serial port, parse incoming `COMM_TYPE_FEEDBACK` packets, and then calls the `state_cb` function that was registered by `head_node.py`.

3.  **`AstraHeadController` Firmware (`main.cpp`, `comm.cpp`)**:
    *   The firmware runs on an ESP32 and its main purpose is to listen for serial commands and translate them into actions for the pan and tilt servos.
    *   **`setup()`**: Initializes the serial port at 921600 baud, sets up the servo control library (`SCServo`), and disables motor torque by default.
    *   **`loop()`**: The heart of the firmware.
        *   It continuously calls **`comm_recv_poll_last()`**. This function from `comm.cpp` reads all available data from the serial buffer but only processes the *most recent* command packet. This is a critical design choice for real-time systems, as it prevents a backlog of old commands from being executed, ensuring the robot is always responding to the latest instruction.
        *   Based on the packet `type`, it executes the corresponding action.

## Function-Level Connection

### Command Flow (Host -> ESP32)

1.  A high-level controller (like `astra_controller.py`) publishes a `JointCommand` message to the `/head/joint_command` topic.
2.  The subscription callback in `head_node.py` is triggered.
    ```python
    # head_node.py
    def cb(msg: astra_controller_interfaces.msg.JointCommand):
        # ... assertions ...
        head_controller.set_pos(np.array(msg.position_cmd, dtype=np.float32))
    ```
3.  The `head_controller.set_pos()` method takes the position array, creates a `COMM_TYPE_CTRL` packet, and sends it over the serial port.
4.  In the firmware, the `loop()` function in `main.cpp` detects the new packet.
    ```cpp
    // AstraHeadController/src/main.cpp
    bool ret = comm_recv_poll_last(&type, buf);
    if (!ret) {
        if (type == COMM_TYPE_CTRL) {
            // ... unpacks data from buf into `pos` array ...
            doPose(pos);
            // ... sends feedback ...
        }
    }
    ```
5.  The `doPose()` function is called, which uses the `SCServo` library to send the final command to the servos.
    ```cpp
    // AstraHeadController/src/main.cpp
    void doPose(uint16_t pos[]) {
      int servo_vel = config.servo_vel;
      int servo_acc = config.servo_acc;

      sts.WritePosEx(12, pos[0], servo_vel, servo_acc); // Pan servo
      sts.WritePosEx(13, pos[1], servo_vel, servo_acc); // Tilt servo
    }
    ```

### Feedback Flow (ESP32 -> Host)

1.  After executing a command, or if no command is received for 10ms, the firmware's `loop()` sends back the current state.
2.  It calls `readPose(pos)` to get the current servo positions from the `SCServo` library.
    ```cpp
    // AstraHeadController/src/main.cpp
    void readPose(uint16_t pos[]) {
      pos[0] = sts.ReadPos(12);
      pos[1] = sts.ReadPos(13);
    }
    ```
3.  This position data is packed into a `COMM_TYPE_FEEDBACK` packet and sent back to the host via `comm_send_blocking()`.
4.  The background thread in the `head_controller` Python class reads and parses this packet.
5.  It then calls the `state_cb` callback that was registered in `head_node.py`, passing the new position data.
6.  This callback in `head_node.py` constructs a `sensor_msgs.msg.JointState` message and publishes it to the `/joint_states` topic for the rest of the ROS system to use.
    ```python
    # head_node.py
    def cb(position, velocity, effort, this_time):
        msg = sensor_msgs.msg.JointState()
        # ... populates msg fields ...
        joint_state_publisher.publish(msg)
    head_controller.state_cb = cb
    ```