# Button Implementation for AstraPedalController

## Overview

The AstraPedalController can be easily modified to support digital buttons instead of analog pedals. This allows for binary on/off inputs like gear shift buttons, handbrake toggle, horn, etc.

## Button vs Analog Comparison

| Feature | Analog Pedals | Digital Buttons |
|---------|---------------|-----------------|
| **Input Type** | Continuous (0-4095) | Binary (0/1) |
| **Use Cases** | Gas, Brake, Clutch | Gear shifts, Handbrake, Horn, Lights |
| **Precision** | 12-bit (4096 levels) | 1-bit (2 levels) |
| **Hardware** | Potentiometers | Push buttons, switches |
| **Data Size** | 16 bytes (8 × 2 bytes) | 1 byte (8 bits) |

## Hardware Setup

### Button Wiring
```
Button 1: Pin 36 (with 10kΩ pull-down resistor)
Button 2: Pin 39 (with 10kΩ pull-down resistor)
Button 3: Pin 34 (with 10kΩ pull-down resistor)
Button 4: Pin 35 (with 10kΩ pull-down resistor)
Button 5: Pin 32 (with 10kΩ pull-down resistor)
Button 6: Pin 33 (with 10kΩ pull-down resistor)
Button 7: Pin 25 (with 10kΩ pull-down resistor)
Button 8: Pin 26 (with 10kΩ pull-down resistor)
```

### Circuit Diagram
```
VCC (3.3V)
    │
    ├─[Button]───[10kΩ Resistor]───GND
    │
    └─[GPIO Pin]
```

## Code Implementation

### Modified main.cpp for Buttons

```cpp
/*
# File: main.cpp (Button Version)

This version reads digital buttons instead of analog pedals.
Each button state is packed into a single byte for efficient transmission.
*/
#include <Arduino.h>
#include "main.h"
#include "comm.h"

// Button pin definitions
const int BUTTON_PINS[8] = {36, 39, 34, 35, 32, 33, 25, 26};

void setup() {
  // Initialize all button pins as inputs with pull-down resistors
  for (int i = 0; i < 8; i++) {
    pinMode(BUTTON_PINS[i], INPUT);
  }

  comm_init();
}

void loop() {
  // Read all button states
  uint8_t button_states = 0;
  
  for (int i = 0; i < 8; i++) {
    // Read button state (HIGH = pressed, LOW = not pressed)
    bool button_pressed = digitalRead(BUTTON_PINS[i]) == HIGH;
    
    // Set corresponding bit in button_states
    if (button_pressed) {
      button_states |= (1 << i);
    }
  }

  // Send button states as feedback packet
  comm_send_blocking(COMM_TYPE_FEEDBACK, &button_states);

  delay(50); // 20Hz update rate for buttons (faster than pedals)
}
```

### Alternative: Mixed Analog + Digital

```cpp
/*
# File: main.cpp (Mixed Version)

This version supports both analog pedals and digital buttons.
Uses first 4 channels for analog, last 4 for digital.
*/
#include <Arduino.h>
#include "main.h"
#include "comm.h"

// Pin definitions
const int ANALOG_PINS[4] = {36, 39, 34, 35};  // First 4 pins for analog
const int BUTTON_PINS[4] = {32, 33, 25, 26};  // Last 4 pins for buttons

void setup() {
  // Set analog resolution
  analogReadResolution(12);
  
  // Initialize button pins
  for (int i = 0; i < 4; i++) {
    pinMode(BUTTON_PINS[i], INPUT);
  }

  comm_init();
}

void loop() {
  // Read analog values (first 4 channels)
  uint16_t analog[4];
  for (int i = 0; i < 4; i++) {
    analog[i] = analogRead(ANALOG_PINS[i]);
    analog[i] = htons(analog[i]); // Convert to network byte order
  }

  // Read button states (last 4 channels)
  uint8_t button_states = 0;
  for (int i = 0; i < 4; i++) {
    bool button_pressed = digitalRead(BUTTON_PINS[i]) == HIGH;
    if (button_pressed) {
      button_states |= (1 << i);
    }
  }

  // Create mixed payload: 8 bytes analog + 1 byte buttons
  uint8_t payload[9];
  memcpy(payload, analog, 8);           // First 8 bytes: analog data
  payload[8] = button_states;           // Last byte: button states

  comm_send_blocking(COMM_TYPE_FEEDBACK, payload);

  delay(100);
}
```

## Communication Protocol for Buttons

### Button-Only Protocol
```cpp
// Packet structure for buttons only
Header:    0x5A
Type:      0x02 (COMM_TYPE_FEEDBACK)
Payload:   1 byte (8 button states)
```

### Example Button Packet
```
Scenario: Buttons 1, 3, and 7 are pressed
Binary:   10100101 (0xA5 in hex)
Packet:   5A 02 A5
```

### Mixed Protocol
```cpp
// Packet structure for mixed analog + buttons
Header:    0x5A
Type:      0x02 (COMM_TYPE_FEEDBACK)
Payload:   9 bytes (8 bytes analog + 1 byte buttons)
```

## Button Mapping Examples

### Racing Simulator Setup
```cpp
Button 0: Gear 1
Button 1: Gear 2  
Button 2: Gear 3
Button 3: Gear 4
Button 4: Gear 5
Button 5: Gear 6
Button 6: Reverse
Button 7: Neutral
```

### Flight Simulator Setup
```cpp
Button 0: Landing Gear
Button 1: Flaps
Button 2: Spoilers
Button 3: Brakes
Button 4: Lights
Button 5: Horn
Button 6: Radio
Button 7: Autopilot
```

### Mixed Setup (Analog + Buttons)
```cpp
Analog 0: Gas Pedal
Analog 1: Brake Pedal
Analog 2: Clutch Pedal
Analog 3: Steering Wheel
Button 0: Handbrake
Button 1: Horn
Button 2: Lights
Button 3: Wipers
```

## Host System Processing

### Button-Only Processing
```cpp
// Receive button packet
uint8_t payload[1];
comm_type_t type;
if (!comm_recv_poll(&type, payload)) {
    if (type == COMM_TYPE_FEEDBACK) {
        uint8_t button_states = payload[0];
        
        // Check individual button states
        bool button0 = (button_states & 0x01) != 0;  // Bit 0
        bool button1 = (button_states & 0x02) != 0;  // Bit 1
        bool button2 = (button_states & 0x04) != 0;  // Bit 2
        bool button3 = (button_states & 0x08) != 0;  // Bit 3
        bool button4 = (button_states & 0x10) != 0;  // Bit 4
        bool button5 = (button_states & 0x20) != 0;  // Bit 5
        bool button6 = (button_states & 0x40) != 0;  // Bit 6
        bool button7 = (button_states & 0x80) != 0;  // Bit 7
        
        printf("Buttons: %d%d%d%d %d%d%d%d\n", 
               button7, button6, button5, button4, 
               button3, button2, button1, button0);
    }
}
```

### Mixed Processing
```cpp
// Receive mixed packet
uint8_t payload[9];
comm_type_t type;
if (!comm_recv_poll(&type, payload)) {
    if (type == COMM_TYPE_FEEDBACK) {
        // Extract analog values
        uint16_t analog[4];
        memcpy(analog, payload, 8);
        for (int i = 0; i < 4; i++) {
            analog[i] = ntohs(analog[i]);
        }
        
        // Extract button states
        uint8_t button_states = payload[8];
        
        // Process analog values (0-100%)
        float gas_percent = (analog[0] / 4095.0f) * 100.0f;
        float brake_percent = (analog[1] / 4095.0f) * 100.0f;
        float clutch_percent = (analog[2] / 4095.0f) * 100.0f;
        float steering_percent = (analog[3] / 4095.0f) * 100.0f;
        
        // Process button states
        bool handbrake = (button_states & 0x01) != 0;
        bool horn = (button_states & 0x02) != 0;
        bool lights = (button_states & 0x04) != 0;
        bool wipers = (button_states & 0x08) != 0;
        
        printf("Gas: %.1f%%, Brake: %.1f%%, Handbrake: %s\n",
               gas_percent, brake_percent, handbrake ? "ON" : "OFF");
    }
}
```

## Advanced Button Features

### Debouncing
```cpp
// Add debouncing to prevent false triggers
unsigned long lastDebounceTime[8] = {0};
unsigned long debounceDelay = 50; // 50ms debounce

bool readButtonWithDebounce(int buttonIndex) {
    bool reading = digitalRead(BUTTON_PINS[buttonIndex]) == HIGH;
    
    if (reading != lastButtonState[buttonIndex]) {
        lastDebounceTime[buttonIndex] = millis();
    }
    
    if ((millis() - lastDebounceTime[buttonIndex]) > debounceDelay) {
        if (reading != buttonState[buttonIndex]) {
            buttonState[buttonIndex] = reading;
        }
    }
    
    lastButtonState[buttonIndex] = reading;
    return buttonState[buttonIndex];
}
```

### Button Events (Press/Release Detection)
```cpp
// Track button state changes
bool lastButtonStates[8] = {false};
bool buttonPressed[8] = {false};
bool buttonReleased[8] = {false};

void updateButtonEvents(uint8_t currentStates) {
    for (int i = 0; i < 8; i++) {
        bool currentState = (currentStates & (1 << i)) != 0;
        
        // Detect press (rising edge)
        if (currentState && !lastButtonStates[i]) {
            buttonPressed[i] = true;
        } else {
            buttonPressed[i] = false;
        }
        
        // Detect release (falling edge)
        if (!currentState && lastButtonStates[i]) {
            buttonReleased[i] = true;
        } else {
            buttonReleased[i] = false;
        }
        
        lastButtonStates[i] = currentState;
    }
}
```

## Performance Comparison

| Metric | Analog Pedals | Digital Buttons | Mixed |
|--------|---------------|-----------------|-------|
| **Update Rate** | 10Hz | 20Hz | 10Hz |
| **Packet Size** | 18 bytes | 3 bytes | 11 bytes |
| **Bandwidth** | 1.6 kbps | 0.5 kbps | 0.9 kbps |
| **Latency** | 101ms | 51ms | 101ms |
| **Precision** | 4096 levels | 2 levels | Mixed |

## Configuration Options

### PlatformIO Configuration
```ini
[env:esp32dev]
platform = espressif32
board = esp32dev
framework = arduino
monitor_speed = 921600
build_flags = 
    -D BUTTON_MODE=1
    -D MIXED_MODE=0
    -D DEBOUNCE_DELAY=50
```

### Compile-Time Options
```cpp
// Choose mode at compile time
#define BUTTON_MODE 1      // 1 = buttons only, 0 = analog only
#define MIXED_MODE 0       // 1 = mixed analog + buttons
#define DEBOUNCE_DELAY 50  // milliseconds

#if BUTTON_MODE
    // Button-only implementation
#elif MIXED_MODE
    // Mixed implementation
#else
    // Original analog-only implementation
#endif
```

This implementation shows how easily the AstraPedalController can be adapted for buttons, providing binary inputs for gear shifts, toggles, and other digital controls while maintaining the same communication protocol structure. 