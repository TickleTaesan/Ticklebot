# COMM_TYPE_CONFIG_WRITE (0x05) Communication Scenario

## Overview
Updates configuration parameters in the controller's memory and persistent storage.

## Command Structure
- **Command ID**: 0x05
- **Payload**: Two uint32_t values [parameter_id, value]
- **Direction**: Host → Controller

## Parameter IDs
| ID    | Parameter              | Type    | Description                    |
|-------|------------------------|---------|--------------------------------|
| 0x01  | EIShaper_enabled      | bool    | Enable/disable EIShaper filter |
| 0x02  | EIShaper_freq         | float   | EIShaper frequency            |
| 0x03  | EIShaper_V            | float   | EIShaper velocity             |
| 0x04  | EIShaper_ctrl_freq    | float   | Control frequency             |
| 0x05  | joint_vel_max         | float   | Maximum joint velocity         |
| 0x06  | joint_acc             | float   | Joint acceleration            |

## Processing Sequence
```cpp
uint32_t cmd[2];
memcpy(cmd, buf, sizeof cmd);
for (int i = 0; i < 2; ++i) cmd[i] = ntohl(cmd[i]);

// Handle parameter update
if (cmd[0] == 0x01) {
    config.EIShaper_enabled = (bool)cmd[1];
    write_config();
    // Reinitialize if needed
    if (config.EIShaper_enabled) {
        EIShaperInit(pos);
    }
}
```

## Example Usage
```cpp
// Enable EIShaper
uint32_t command[2] = {
    htonl(0x01),  // Parameter ID: EIShaper_enabled
    htonl(1)      // Value: true
};
comm_send_blocking(COMM_TYPE_CONFIG_WRITE, (uint8_t*)command);
```