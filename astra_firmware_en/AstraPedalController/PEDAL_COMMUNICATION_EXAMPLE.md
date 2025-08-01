# Four Pedal Communication Example with Dummy Data

## Overview

This document demonstrates how the AstraPedalController reads four pedals and communicates their values using realistic dummy data. The system reads 8 analog channels (4 pedals × 2 channels each) and sends them as feedback packets.

## Pedal Configuration

### Physical Setup
The system uses **4 pedals**, each with **2 analog channels**:
- **Pedal 1**: Channels 0 & 1 (Pins 36 & 39)
- **Pedal 2**: Channels 2 & 3 (Pins 34 & 35) 
- **Pedal 3**: Channels 4 & 5 (Pins 32 & 33)
- **Pedal 4**: Channels 6 & 7 (Pins 25 & 26)

### Channel Mapping
```
Pedal 1: analog[0] = Pin 36 (VP), analog[1] = Pin 39 (VN)
Pedal 2: analog[2] = Pin 34 (VP), analog[3] = Pin 35 (VN)
Pedal 3: analog[4] = Pin 32 (VP), analog[5] = Pin 33 (VN)
Pedal 4: analog[6] = Pin 25 (VP), analog[7] = Pin 26 (VN)
```

## Dummy Data Example

### Scenario: Driving Simulation
Let's simulate a driving scenario where:
- **Pedal 1**: Gas pedal (accelerator) - 75% pressed
- **Pedal 2**: Brake pedal - 30% pressed  
- **Pedal 3**: Clutch pedal - 0% pressed (not used)
- **Pedal 4**: Handbrake - 100% engaged

### Raw ADC Values (12-bit: 0-4095)
```
analog[0] = 3072  // Gas pedal: 75% of 4095
analog[1] = 1024  // Gas pedal secondary sensor
analog[2] = 1229  // Brake pedal: 30% of 4095
analog[3] = 819   // Brake pedal secondary sensor
analog[4] = 0     // Clutch pedal: not pressed
analog[5] = 0     // Clutch pedal secondary sensor
analog[6] = 4095  // Handbrake: fully engaged
analog[7] = 4095  // Handbrake secondary sensor
```

### Network Byte Order Conversion
The ESP32 converts these values to network byte order (big-endian) using `htons()`:

```cpp
// Before htons() (little-endian on ESP32)
analog[0] = 3072  // 0x0C00
analog[1] = 1024  // 0x0400
analog[2] = 1229  // 0x04CD
analog[3] = 819   // 0x0333
analog[4] = 0     // 0x0000
analog[5] = 0     // 0x0000
analog[6] = 4095  // 0x0FFF
analog[7] = 4095  // 0x0FFF

// After htons() (network byte order)
analog[0] = 0x000C  // 3072 in big-endian
analog[1] = 0x0004  // 1024 in big-endian
analog[2] = 0x00CD  // 1229 in big-endian
analog[3] = 0x0033  // 819 in big-endian
analog[4] = 0x0000  // 0 in big-endian
analog[5] = 0x0000  // 0 in big-endian
analog[6] = 0x0FFF  // 4095 in big-endian
analog[7] = 0x0FFF  // 4095 in big-endian
```

## Communication Packet Structure

### Complete Packet Example
```
Header:    0x5A (01011010 binary)
Type:      0x02 (COMM_TYPE_FEEDBACK)
Payload:   16 bytes of pedal data
```

### Raw Packet Data (Hex)
```
5A 02 00 0C 00 04 00 CD 00 33 00 00 00 00 0F FF 0F FF
│  │  │  │  │  │  │  │  │  │  │  │  │  │  │  │  │  │
│  │  │  │  │  │  │  │  │  │  │  │  │  │  │  │  │  │  └─ Handbrake 2: 4095
│  │  │  │  │  │  │  │  │  │  │  │  │  │  │  │  │  └─── Handbrake 1: 4095
│  │  │  │  │  │  │  │  │  │  │  │  │  │  │  │  └────── Clutch 2: 0
│  │  │  │  │  │  │  │  │  │  │  │  │  │  │  └───────── Clutch 1: 0
│  │  │  │  │  │  │  │  │  │  │  │  │  │  └──────────── Brake 2: 819
│  │  │  │  │  │  │  │  │  │  │  │  │  └─────────────── Brake 1: 1229
│  │  │  │  │  │  │  │  │  │  │  │  └────────────────── Gas 2: 1024
│  │  │  │  │  │  │  │  │  │  │  └───────────────────── Gas 1: 3072
│  │  │  │  │  │  │  │  │  │  └───────────────────────── Type: FEEDBACK
│  │  │  │  │  │  │  │  │  └──────────────────────────── Header: 0x5A
│  │  │  │  │  │  │  │  └─────────────────────────────────
│  │  │  │  │  │  │  └────────────────────────────────────
│  │  │  │  │  │  └───────────────────────────────────────
│  │  │  │  │  └──────────────────────────────────────────
│  │  │  │  └─────────────────────────────────────────────
│  │  │  └─────────────────────────────────────────────────
│  │  └────────────────────────────────────────────────────
│  └───────────────────────────────────────────────────────
```

## Data Flow Timeline

### At t=0ms (Start of loop)
```
1. Read analog values from all 8 channels
2. Convert to network byte order
3. Create feedback packet
4. Send packet via serial
5. Wait 100ms
```

### At t=100ms (Next iteration)
```
1. Read new analog values
2. Convert to network byte order  
3. Create new feedback packet
4. Send packet via serial
5. Wait 100ms
```

## Host System Processing

### Receiving the Data
```cpp
// Host receives the packet
uint8_t packet[] = {0x5A, 0x02, 0x00, 0x0C, 0x00, 0x04, 0x00, 0xCD, 
                    0x00, 0x33, 0x00, 0x00, 0x00, 0x00, 0x0F, 0xFF, 0x0F, 0xFF};

// Extract pedal values
uint16_t analog[8];
memcpy(analog, &packet[2], 16);

// Convert back from network byte order
for (int i = 0; i < 8; i++) {
    analog[i] = ntohs(analog[i]);
}

// Now analog[] contains the original values:
// analog[0] = 3072 (Gas pedal 1: 75%)
// analog[1] = 1024 (Gas pedal 2)
// analog[2] = 1229 (Brake pedal 1: 30%)
// analog[3] = 819  (Brake pedal 2)
// analog[4] = 0    (Clutch pedal 1: 0%)
// analog[5] = 0    (Clutch pedal 2)
// analog[6] = 4095 (Handbrake 1: 100%)
// analog[7] = 4095 (Handbrake 2)
```

### Interpreting Pedal Values
```cpp
// Convert to percentage (0-100%)
float gas_percent = (analog[0] / 4095.0f) * 100.0f;    // 75.0%
float brake_percent = (analog[2] / 4095.0f) * 100.0f;  // 30.0%
float clutch_percent = (analog[4] / 4095.0f) * 100.0f; // 0.0%
float handbrake_percent = (analog[6] / 4095.0f) * 100.0f; // 100.0%

printf("Gas: %.1f%%, Brake: %.1f%%, Clutch: %.1f%%, Handbrake: %.1f%%\n",
       gas_percent, brake_percent, clutch_percent, handbrake_percent);
// Output: Gas: 75.0%, Brake: 30.0%, Clutch: 0.0%, Handbrake: 100.0%
```

## Multiple Scenarios

### Scenario 1: Normal Driving
```
Gas: 50% (2048), Brake: 0% (0), Clutch: 20% (819), Handbrake: 0% (0)
Packet: 5A 02 08 00 02 00 00 00 03 33 00 00 00 00 00 00 00 00
```

### Scenario 2: Emergency Braking
```
Gas: 0% (0), Brake: 100% (4095), Clutch: 0% (0), Handbrake: 0% (0)
Packet: 5A 02 00 00 00 00 0F FF 00 00 00 00 00 00 00 00 00 00
```

### Scenario 3: Starting from Stop
```
Gas: 25% (1024), Brake: 0% (0), Clutch: 80% (3276), Handbrake: 0% (0)
Packet: 5A 02 04 00 00 00 0C CC 00 00 00 00 00 00 00 00 00 00
```

## Real-time Characteristics

### Update Frequency
- **Rate**: 10Hz (every 100ms)
- **Data per second**: 160 bytes (16 bytes × 10 packets)
- **Bandwidth**: ~1.6 kbps

### Latency
- **Transmission time**: <1ms for 18-byte packet at 921,600 bps
- **Total latency**: ~101ms (100ms loop + <1ms transmission)
- **Jitter**: Minimal (deterministic loop timing)

### Reliability
- **Error detection**: Header validation, type checking, length verification
- **Recovery**: Automatic resynchronization on invalid packets
- **Buffer management**: Overflow protection with packet dropping

## Troubleshooting Examples

### Corrupted Packet Detection
```
Received: 5A 02 00 0C 00 04 00 CD 00 33 00 00 00 00 0F FF 0F
Expected: 5A 02 00 0C 00 04 00 CD 00 33 00 00 00 00 0F FF 0F FF
Issue: Missing last byte, packet will be rejected
```

### Wrong Header Detection
```
Received: 5B 02 00 0C 00 04 00 CD 00 33 00 00 00 00 0F FF 0F FF
Expected: 5A 02 00 0C 00 04 00 CD 00 33 00 00 00 00 0F FF 0F FF
Issue: Wrong header (0x5B instead of 0x5A), packet will be ignored
```

This example shows how the four pedals communicate in real-time, with the ESP32 continuously reading analog values, converting them to network format, and transmitting them as structured packets that the host system can interpret and use for driving simulation or other applications. 