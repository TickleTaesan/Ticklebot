# COMM_TYPE_PIDTUNE (0x08) Communication Scenario

## Overview
Updates PID control parameters for motor control system.

## Command Structure
- **Command ID**: 0x08
- **Payload**: Array of 8 float values (transmitted as uint32_t)
- **Direction**: Host → Controller

## Parameters
| Index | Parameter         | Type  | Description                      |
|-------|------------------|-------|----------------------------------|
| 0     | kp              | float | Proportional gain                |
| 1     | ki              | float | Integral gain                    |
| 2     | kd              | float | Derivative gain                  |
| 3     | ki_clip_thres   | float | Integral clip threshold          |
| 4     | ki_clip_coef    | float | Integral clip coefficient        |
| 5     | ki_max          | float | Maximum integral value           |
| 6     | kp2             | float | Secondary proportional gain      |
| 7     | kp2_err_point   | float | Error point for secondary gain   |

## Processing Sequence
```cpp
uint32_t cmd[8];
memcpy(cmd, buf, sizeof cmd);
for (int i = 0; i < 8; ++i) cmd[i] = ntohl(cmd[i]);

pidtune_kp = U32_TO_FLOAT(cmd[0]);
pidtune_ki = U32_TO_FLOAT(cmd[1]);
pidtune_kd = U32_TO_FLOAT(cmd[2]);
pidtune_ki_max = U32_TO_FLOAT(cmd[5]);
pidtune_kp2 = U32_TO_FLOAT(cmd[6]);
pidtune_kp2_err_point = U32_TO_FLOAT(cmd[7]);
pidtune_ki_clip_thres = U32_TO_FLOAT(cmd[3]);
pidtune_ki_clip_coef = U32_TO_FLOAT(cmd[4]);
```