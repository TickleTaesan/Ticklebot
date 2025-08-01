# COMM_TYPE_CONFIG_READ (0x06) Communication Scenario

## Overview
Reads current configuration parameters from the controller.

## Command Structure
- **Command ID**: 0x06
- **Payload**: Two uint32_t values [parameter_id, 0]
- **Direction**: Host → Controller, Controller → Host (response)

## Parameter IDs
| ID    | Parameter              | Type    | Returns                         |
|-------|------------------------|---------|----------------------------------|
| 0x01  | EIShaper_enabled      | bool    | Current EIShaper enable state   |
| 0x02  | EIShaper_freq         | float   | Current EIShaper frequency      |
| 0x03  | EIShaper_V            | float   | Current EIShaper velocity       |
| 0x04  | EIShaper_ctrl_freq    | float   | Current control frequency       |
| 0x05  | joint_vel_max         | float   | Current maximum joint velocity  |
| 0x06  | joint_acc             | float   | Current joint acceleration      |

## Example Usage
```cpp
// Read EIShaper frequency
uint32_t request[2] = {
    htonl(0x02),  // Parameter ID: EIShaper_freq
    htonl(0)      // Placeholder
};
comm_send_blocking(COMM_TYPE_CONFIG_READ, (uint8_t*)request);

// Response will contain:
// cmd[0] = 0x02 (parameter ID)
// cmd[1] = FLOAT_TO_U32(current_frequency)
```