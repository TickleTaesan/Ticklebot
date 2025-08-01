# COMM_TYPE_TORQUE (0x04) Communication Scenario

## Overview
Enables or disables motor torque for all joints.

## Command Structure
- **Command ID**: 0x04
- **Payload**: Single uint8_t value
- **Direction**: Host → Controller

## Data Format
```cpp
uint8_t enable;  // 0 = disable, 1 = enable
```

## Processing Sequence
```cpp
void setupTorque(uint8_t enable) {
    torque_enabled = enable;
    for (int i = 0; i < JOINT_NUM; ++i) {
        motors[i].setTorque(enable);
    }
}
```

## Safety Considerations
- Disabling torque allows free movement of joints
- Should be enabled before sending position commands
- Emergency stop will automatically disable torque

## Example Usage
```cpp
// Enable torque
uint8_t enable_cmd = 1;
comm_send_blocking(COMM_TYPE_TORQUE, &enable_cmd);

// Disable torque
uint8_t disable_cmd = 0;
comm_send_blocking(COMM_TYPE_TORQUE, &disable_cmd);
```