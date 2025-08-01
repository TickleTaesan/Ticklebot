# AstraPedalController Communication Protocol

## Overview

The AstraPedalController is an ESP32-based firmware that reads analog pedal inputs and communicates with external systems using a custom serial protocol. This document explains the communication architecture, protocol details, and data flow.

## Communication Interface

### Hardware Interface
- **Platform**: ESP32 microcontroller
- **Interface**: Serial communication over USB
- **Baud Rate**: 921,600 bps (high-speed for real-time data)
- **Connection**: USB serial connection to host computer or other devices

### Who It Communicates With

The AstraPedalController communicates with:

1. **Host Computer/System**: Primary communication partner that receives pedal feedback data
2. **Other Astra System Components**: Potentially other devices in the Astra ecosystem
3. **Debug/Development Tools**: Serial monitors and debugging interfaces

## Communication Protocol

### Packet Structure

Each communication packet follows this structure:

```
[Header Byte] [Type Byte] [Payload Data...]
    0x5A        0-2        16 bytes max
```

- **Header Byte (0x5A)**: Fixed synchronization byte (binary: 01011010)
- **Type Byte**: Identifies the packet type (0-2)
- **Payload**: Variable-length data (maximum 100 bytes, typically 16 bytes)

### Packet Types

| Type | Name | Purpose | Payload Size |
|------|------|---------|--------------|
| 0 | `COMM_TYPE_PING` | Keep-alive/connectivity test | 16 bytes |
| 1 | `COMM_TYPE_PONG` | Response to ping | 16 bytes |
| 2 | `COMM_TYPE_FEEDBACK` | Pedal analog data | 16 bytes |

### Data Flow

#### Outgoing Data (Pedal Controller → Host)
1. **Analog Reading**: Reads 8 analog channels (pins 36, 39, 34, 35, 32, 33, 25, 26)
2. **Data Processing**: Converts 12-bit ADC values (0-4095) to network byte order
3. **Packet Creation**: Wraps data in `COMM_TYPE_FEEDBACK` packet
4. **Transmission**: Sends packet every 100ms via blocking serial transmission

#### Incoming Data (Host → Pedal Controller)
- **Ping/Pong**: Handles connectivity testing
- **Command Processing**: Can receive commands (though not currently implemented in main loop)
- **Buffer Management**: Non-blocking reception with packet validation

## Main Loop Operation

```cpp
void loop() {
  // Read 8 analog channels
  uint16_t analog[8];
  analog[0] = analogRead(36);  // VP
  analog[1] = analogRead(39);  // VN
  analog[2] = analogRead(34);  // VP
  analog[3] = analogRead(35);  // VN
  analog[4] = analogRead(32);  // VP
  analog[5] = analogRead(33);  // VN
  analog[6] = analogRead(25);  // VP
  analog[7] = analogRead(26);  // VN

  // Convert to network byte order
  for (int i = 0; i < 8; ++i) analog[i] = htons(analog[i]);
  
  // Send feedback packet
  comm_send_blocking(COMM_TYPE_FEEDBACK, (uint8_t *)analog);
  
  delay(100);  // 10Hz update rate
}
```

## Communication Functions

### Core Functions

#### `comm_init()`
- Initializes serial communication at 921,600 bps
- Sets up receive buffer
- Returns false on success

#### `comm_send_blocking(comm_type_t type, const uint8_t payload[])`
- Sends a complete packet with header, type, and payload
- Blocking operation (waits for transmission completion)
- Returns false on success

#### `comm_recv_poll(comm_type_t *type, uint8_t payload[])`
- Non-blocking packet reception
- Validates packet structure and type
- Returns false when packet is successfully received

#### `comm_recv_poll_last(comm_type_t *type, uint8_t payload[])`
- Empties receive buffer and returns the last valid packet
- Skips non-important packets to prevent buffer overflow
- Ensures real-time performance

## Error Handling

### Packet Validation
- **Header Validation**: Checks for correct 0x5A header byte
- **Type Validation**: Verifies packet type is within valid range
- **Length Validation**: Ensures payload size matches expected size
- **Buffer Protection**: Prevents buffer overflow with assertions

### Error Recovery
- **Invalid Header**: Skips bytes until valid header found
- **Invalid Type**: Resets receive buffer and continues
- **Buffer Overflow**: Assertion failure (development protection)

## Performance Characteristics

- **Update Rate**: 10Hz (100ms intervals)
- **Data Rate**: ~1.6 kbps (16 bytes × 10Hz)
- **Latency**: <1ms for packet transmission
- **Reliability**: High-speed serial with error checking

## Integration Points

### Host System Requirements
To communicate with the AstraPedalController, the host system must:

1. **Serial Interface**: Connect via USB serial at 921,600 bps
2. **Protocol Implementation**: Implement the same packet structure
3. **Data Processing**: Handle 8 analog values in network byte order
4. **Real-time Handling**: Process data at 10Hz or higher

### Example Host Code Structure
```cpp
// Receive pedal data
uint8_t payload[16];
comm_type_t type;
if (!comm_recv_poll(&type, payload)) {
    if (type == COMM_TYPE_FEEDBACK) {
        uint16_t analog[8];
        memcpy(analog, payload, 16);
        // Process analog values...
    }
}
```

## Development Notes

### ADC Considerations
- **ADC2 Limitation**: ADC2 channels are used by WiFi, so only ADC1 channels are used
- **Resolution**: 12-bit ADC (0-4095 range)
- **Channel Mapping**: Carefully selected to avoid WiFi conflicts

### Future Enhancements
- **Timeout Mechanism**: TODO comment indicates planned timeout for packet reception
- **Command Processing**: Main loop could be extended to handle incoming commands
- **Error Reporting**: Enhanced error reporting and recovery mechanisms

## Troubleshooting

### Common Issues
1. **Wrong Baud Rate**: Ensure host system uses 921,600 bps
2. **Packet Corruption**: Check for electrical interference or cable issues
3. **Buffer Overflow**: Reduce host processing time or increase buffer size
4. **ADC Noise**: Ensure proper grounding and shielding for analog inputs

### Debug Output
The firmware includes debug messages for:
- Invalid header bytes
- Unknown packet types
- Communication errors

These messages are sent via Serial.println() for development debugging. 