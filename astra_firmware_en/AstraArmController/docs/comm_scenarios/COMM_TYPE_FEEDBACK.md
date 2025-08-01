# COMM_TYPE_FEEDBACK (0x03) Communication Scenario

## Overview
Sends feedback about current joint positions back to the host.

## Command Structure
- **Command ID**: 0x03
- **Payload**: Array of 8 uint16_t values (6 used)
- **Direction**: Controller → Host

## Data Format
```cpp
uint16_t current_positions[8];  // Network byte order (big-endian)
```

## When Feedback is Sent
1. After each COMM_TYPE_CTRL command execution
2. Periodically (every 10ms) if no commands received

## Example Implementation
```cpp
void sendFeedback() {
    uint16_t pos[8];
    dualMotorReadPos(pos);
    
    // Convert to network byte order
    for (int i = 0; i < 6; ++i) {
        pos[i] = htons(pos[i]);
    }
    
    comm_send_blocking(COMM_TYPE_FEEDBACK, (uint8_t *)pos);
}
```