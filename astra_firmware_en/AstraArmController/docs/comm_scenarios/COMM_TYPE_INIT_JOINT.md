# COMM_TYPE_INIT_JOINT (0x09) Communication Scenario

## Overview
Initializes or calibrates a specific joint with offset values.

## Command Structure
- **Command ID**: 0x09
- **Payload**: Four uint32_t values [joint_id, offset, reserved, reserved]
- **Direction**: Host → Controller

## Parameters
| Parameter    | Type     | Description                          |
|-------------|----------|--------------------------------------|
| joint_id    | uint32_t | ID of joint to initialize (0-5)      |
| offset      | int32_t  | Joint offset value                   |
| reserved    | uint32_t | Reserved for future use              |
| reserved    | uint32_t | Reserved for future use              |

## Processing Sequence
```cpp
void handleInitJoint(uint32_t* cmd) {
    int id = cmd[0];
    int offset = U32_TO_I32(cmd[1]);
    
    // Initialize joint with offset
    initJoint(id, offset);
    
    // Send confirmation
    cmd[1] = I32_TO_U32(offset);
    comm_send_blocking(COMM_TYPE_INIT_JOINT_FEEDBACK, (uint8_t*)cmd);
}
```