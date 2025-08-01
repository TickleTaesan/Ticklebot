# COMM_TYPE_CTRL (0x02) Communication Scenario

## Overview
Controls the robot arm by sending target positions for all joints.

## Command Structure
- **Command ID**: 0x02
- **Payload**: Array of 8 uint16_t values (6 used)
- **Direction**: Host → Controller

## Data Format
```cpp
uint16_t joint_positions[8];  // Network byte order (big-endian)
```

## Processing Sequence
1. **Update Timestamp**
   ```cpp
   last_action_time = millis();
   ```

2. **Parse Joint Positions**
   ```cpp
   uint16_t pos[8];
   memcpy(pos, buf, sizeof pos);
   for (int i = 0; i < 6; ++i) pos[i] = ntohs(pos[i]);
   ```

3. **Apply EIShaper Filter** (if enabled)
   ```cpp
   if (config.EIShaper_enabled) {
       EIShaperApply(pos);
   }
   ```

4. **Update Motors**
   ```cpp
   dualMotorUpdatePos(pos);
   ```

## Example Usage
```cpp
// Example: Set joint 1 to 45°, joint 2 to 90°
uint16_t positions[8] = {
    htons(450),   // Joint 1: 45.0°
    htons(900),   // Joint 2: 90.0°
    0, 0, 0, 0, 0, 0
};
comm_send_blocking(COMM_TYPE_CTRL, (uint8_t*)positions);
```