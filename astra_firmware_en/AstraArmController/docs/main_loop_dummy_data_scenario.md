# AstraArmController Main Loop: Dummy Data Handling Scenario

This document explains in detail how the `main.cpp` loop of the AstraArmController firmware works, especially when it receives dummy (test) data. It includes a scenario with code snippets to illustrate the process.

---

## 1. Main Loop Overview

The main loop (`void loop()`) is responsible for:
- Polling for incoming communication commands
- Handling different command types (control, torque, config, etc.)
- Updating motor positions and sending feedback
- Managing periodic status updates and display

### Key Communication Types
- `COMM_TYPE_CTRL`: Main control command (e.g., joint positions)
- `COMM_TYPE_TORQUE`: Enable/disable torque
- `COMM_TYPE_CONFIG_WRITE`/`READ`: Update/read configuration
- `COMM_TYPE_PIDTUNE`: Update PID parameters
- `COMM_TYPE_INIT_JOINT`: Initialize joint offset

---

## 2. Dummy Data Scenario: Receiving a Control Command

Suppose the controller receives a dummy `COMM_TYPE_CTRL` command with test joint positions. Here is how the main loop processes it:

### Example Dummy Data
```cpp
// Simulated incoming buffer (dummy data for 6 joints)
uint8_t buf[COMM_PAYLOAD_SIZE_MAX] = {0x08, 0x00, 0x10, 0x00, 0x20, 0x00, 0x30, 0x00, 0x40, 0x00, 0x50, 0x00};
comm_type_t type = COMM_TYPE_CTRL;
```

### Main Loop Handling
```cpp
void loop() {
    comm_type_t type;
    uint8_t buf[COMM_PAYLOAD_SIZE_MAX];
    bool ret = comm_recv_poll_last(&type, buf);

    if (!ret) {
        if (type == COMM_TYPE_CTRL) {
            last_action_time = millis();

            uint16_t pos[8];
            memcpy(pos, buf, sizeof pos); // Copy received positions
            for (int i = 0; i < 6; ++i) pos[i] = ntohs(pos[i]); // Convert to host byte order

            // EIShaper (if enabled)
            if (config.EIShaper_enabled) {
                EIShaperApply(pos);
            }

            ++ctrl_cnt;
            dualMotorUpdatePos(pos); // Plan new trajectory for motors

            ++feedback_cnt;
            dualMotorReadPos(pos); // Read back actual positions

            for (int i = 0; i < 6; ++i) pos[i] = htons(pos[i]); // Convert back to network order
            comm_send_blocking(COMM_TYPE_FEEDBACK, (uint8_t *)pos); // Send feedback
        }
        // ... other command types ...
    }
    // ... periodic feedback and display update ...
}
```

### Step-by-Step Breakdown
1. **Receive Command:**
   - `comm_recv_poll_last` fetches the latest command and payload (dummy data in this case).
2. **Check Command Type:**
   - If `type == COMM_TYPE_CTRL`, proceed with control logic.
3. **Extract Joint Positions:**
   - Copy the buffer into a `uint16_t pos[8]` array.
   - Convert the first 6 positions from network to host byte order.
4. **Apply EIShaper (Optional):**
   - If enabled in config, filter the positions for vibration reduction.
5. **Update Motor Trajectories:**
   - Call `dualMotorUpdatePos(pos)` to plan new trajectories for each joint.
6. **Read Back Actual Positions:**
   - `dualMotorReadPos(pos)` fetches the current joint positions.
7. **Send Feedback:**
   - Convert positions back to network order and send as feedback.

---

## 3. Related Code Snippets

### dualMotorUpdatePos
```cpp
void dualMotorUpdatePos(uint16_t pos[]) {
    if (!torque_enabled) {
        setupTorque(1);
    }
    for (int i = 0; i < JOINT_NUM; ++i) {
        traj[i].planTrapezoidal(pos[i], traj[i].pos_setpoint_, traj[i].vel_setpoint_);
    }
}
```

### dualMotorReadPos
```cpp
void dualMotorReadPos(uint16_t read_pos[]) {
    for (int i = 0; i < JOINT_NUM; ++i) {
        read_pos[i] = last_pos[i];
    }
}
```

---

## 4. Summary Table: Main Loop Command Handling

| Command Type              | Action Summary                                      |
|--------------------------|-----------------------------------------------------|
| COMM_TYPE_CTRL           | Update joint positions, send feedback                |
| COMM_TYPE_TORQUE         | Enable/disable torque                               |
| COMM_TYPE_CONFIG_WRITE   | Update configuration, send config feedback           |
| COMM_TYPE_CONFIG_READ    | Read configuration, send config feedback             |
| COMM_TYPE_PIDTUNE        | Update PID parameters                               |
| COMM_TYPE_INIT_JOINT     | Initialize joint offset                             |
| COMM_TYPE_PING/PONG      | Ping-pong for connection check                      |

---

## 5. Notes
- Dummy data is handled the same as real data: the main loop does not distinguish between test and real commands.
- The feedback mechanism ensures that the sender receives the actual joint positions after each control command.
- The code is robust to missing or malformed commands, printing "Unknown comm type" for unrecognized types.

---

*Generated automatically for AstraArmController firmware documentation.*

---

## 6. Detailed Roles of Major Functions in the Main Loop

### comm_recv_poll_last
- **Purpose:** Polls for the latest received command and its payload from the communication interface.
- **Role in Loop:** Determines if a new command (real or dummy) has arrived and what type it is, so the loop can process it accordingly.

### setupTorque
- **Purpose:** Enables or disables the torque on all joints.
- **Role in Loop:** Called when a `COMM_TYPE_TORQUE` command is received, or automatically by `dualMotorUpdatePos` if torque is not already enabled. Ensures motors are ready to move.

### EIShaperApply
- **Purpose:** Applies an EI (Extra Input) Shaper filter to the target joint positions to reduce vibration.
- **Role in Loop:** If enabled in the config, this function is called before updating motor trajectories, modifying the target positions for smoother motion.

### dualMotorUpdatePos
- **Purpose:** Plans new trapezoidal trajectories for each joint based on the received (or filtered) positions.
- **Role in Loop:** Called after receiving a control command to update the setpoints for each joint, ensuring coordinated and smooth movement.

### dualMotorReadPos
- **Purpose:** Reads the most recent positions of all joints from the controller's memory.
- **Role in Loop:** Used to provide feedback to the sender after a control command, or periodically if no command is received.

### comm_send_blocking
- **Purpose:** Sends a response or feedback message with a specified command type and payload.
- **Role in Loop:** Used to send feedback after processing a command, or to acknowledge ping/pong/config requests.

---

## 7. In-Depth Dummy Data Walkthrough

Let's walk through what happens, step by step, when the main loop receives a dummy `COMM_TYPE_CTRL` command with the following payload:

```cpp
// Dummy data: 6 joint positions (hex values)
uint8_t buf[COMM_PAYLOAD_SIZE_MAX] = {0x08, 0x00, 0x10, 0x00, 0x20, 0x00, 0x30, 0x00, 0x40, 0x00, 0x50, 0x00};
// This represents: [0x0008, 0x0010, 0x0020, 0x0030, 0x0040, 0x0050] = [8, 16, 32, 48, 64, 80]
```

### Step 1: Receive and Parse Command
- `comm_recv_poll_last` sets `type = COMM_TYPE_CTRL` and fills `buf` with the above data.
- The loop checks `if (type == COMM_TYPE_CTRL)` and proceeds.

### Step 2: Extract and Convert Positions
```cpp
uint16_t pos[8];
memcpy(pos, buf, sizeof pos); // Copy first 16 bytes (8 positions, but only 6 used)
for (int i = 0; i < 6; ++i) pos[i] = ntohs(pos[i]); // Convert from network to host order
```
- After conversion, `pos = [8, 16, 32, 48, 64, 80, ?, ?]` (last two unused).

### Step 3: (Optional) Apply EIShaper
- If `config.EIShaper_enabled` is true, `EIShaperApply(pos)` may modify the positions for vibration reduction.
- For dummy data, assume EIShaper is off (positions remain unchanged).

### Step 4: Update Motor Trajectories
- `dualMotorUpdatePos(pos)` is called:
  - If torque is not enabled, `setupTorque(1)` is called to enable it.
  - For each joint, `traj[i].planTrapezoidal(pos[i], traj[i].pos_setpoint_, traj[i].vel_setpoint_)` plans a new trajectory from the current setpoint to the new position.

### Step 5: Read Back Actual Positions
- `dualMotorReadPos(pos)` fills `pos` with the most recent joint positions (could be the same as commanded, or lagging if motors are still moving).

### Step 6: Prepare and Send Feedback
- Each position is converted back to network order: `for (int i = 0; i < 6; ++i) pos[i] = htons(pos[i]);`
- `comm_send_blocking(COMM_TYPE_FEEDBACK, (uint8_t *)pos);` sends the feedback to the sender.

### Example Timeline Table
| Step | Function                | Input/Output Example                | Description                                 |
|------|-------------------------|-------------------------------------|---------------------------------------------|
| 1    | comm_recv_poll_last     | type=COMM_TYPE_CTRL, buf=dummy data | Receives dummy command                      |
| 2    | memcpy/ntohs            | pos=[8,16,32,48,64,80]              | Extracts and converts positions              |
| 3    | EIShaperApply (optional)| pos (possibly modified)             | Applies vibration filter if enabled          |
| 4    | dualMotorUpdatePos      | pos                                 | Plans new trajectories for each joint        |
| 5    | dualMotorReadPos        | pos=actual positions                 | Reads back current joint positions           |
| 6    | htons/comm_send_blocking| pos (network order)                 | Sends feedback to sender                     |

---

*This expanded section provides deeper insight into the function roles and a step-by-step walkthrough of dummy data handling in the AstraArmController main loop.*
