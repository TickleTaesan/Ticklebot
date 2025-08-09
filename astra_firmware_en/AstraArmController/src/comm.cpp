/*
# File: comm.cpp

This file implements the communication protocol for the AstraArmController firmware. 
It provides functions for serial initialization, sending and receiving data packets, and handling various communication types, including configuration, torque, and PID tuning.
The protocol is designed for robust, real-time data exchange between the arm controller and other system components, with support for packet validation and buffer management.
*/
#include "comm.h"
#include <string.h>
#include <Arduino.h>
#include "main.h"

// Initialize serial port
// Returns true on error
bool serial_init(void) {
  Serial.begin(921600);
  while (!Serial) delay(1);
  return false;
}

// Blocking send a character
// c is the character to send
// Returns true on error
bool serial_send_blocking(uint8_t c) {
  Serial.write(c);
  return false;
}

// Non-blocking poll for a character
// c is a pointer to store the received character
// Returns true on error (e.g. no data)
bool serial_recv_poll(uint8_t *c) {
  // Not thread-safe!!!
  if (Serial.available()) {
    *c = Serial.read();
    return false;
  } else {
    return true;
  }
}

// Payload size for different packet types
int comm_payload_size[] = {
  16, // COMM_TYPE_PING
  16, // COMM_TYPE_PONG
  16, // COMM_TYPE_CTRL
  16, // COMM_TYPE_FEEDBACK
  16, // COMM_TYPE_TORQUE
  16, // COMM_TYPE_CONFIG_WRITE
  16, // COMM_TYPE_CONFIG_READ
  16, // COMM_TYPE_CONFIG_FEEDBACK
  32, // COMM_TYPE_PIDTUNE
  16, // COMM_TYPE_INIT_JOINT
};

// Packets that cannot be ignored
// Setting to true will cause comm_recv_poll_last not to skip this packet
bool comm_type_importance[] = {
  false, // COMM_TYPE_PING
  false, // COMM_TYPE_PONG
  false, // COMM_TYPE_CTRL
  false, // COMM_TYPE_FEEDBACK
  true,  // COMM_TYPE_TORQUE
  true,  // COMM_TYPE_CONFIG_WRITE
  true,  // COMM_TYPE_CONFIG_READ
  true,  // COMM_TYPE_CONFIG_FEEDBACK
  true,  // COMM_TYPE_PIDTUNE
  true, // COMM_TYPE_INIT_JOINT
};

// Blocking send a packet
// type specifies the data type, payload carries the actual data
// Returns true on error
bool comm_send_blocking(comm_type_t type, const uint8_t payload[]) {
  bool ret;
  ret = serial_send_blocking(0x5A); // 0b01011010 as header
  if (ret) return true;
  uint8_t checksum = 0;
  checksum += (uint8_t)type;
  ret = serial_send_blocking((uint8_t)type); // 0b01011010 as header
  if (ret) return true;
  for (int i = 0; i < comm_payload_size[type]; ++i) {
    checksum += payload[i];
    ret = serial_send_blocking(payload[i]);
    if (ret) return true;
  }
  ret = serial_send_blocking(checksum);
  if (ret) return true;
  return false;
}

static uint8_t recv_buf[2 + COMM_PAYLOAD_SIZE_MAX];
static int recv_buf_p;

// Attempt to receive a packet
// If no error, *type will contain the received packet type, and payload will contain the actual data
// Returns true on error
// It is normal for this function to return an error when no data is received (non-blocking)
bool comm_recv_poll(comm_type_t *type, uint8_t payload[]) {
  bool ret;
  while (true) {
    uint8_t buf;
    ret = serial_recv_poll(&buf);
    if (ret) return true; // No new data

    // Invalid data
    if (recv_buf_p == 0 && buf != 0x5A) {
      Serial.println("comm: warning: Received wrong byte!");
      continue;
    }
    recv_buf[recv_buf_p++] = buf;

    // Buffer too small to hold a complete packet
    assert(recv_buf_p <= sizeof recv_buf);

    // Received a packet of unknown type
    // assert(recv_buf_p != 2 || recv_buf[1] < (sizeof comm_payload_size) / (sizeof comm_payload_size[0]));
    if (recv_buf_p == 2 && recv_buf[1] >= (sizeof comm_payload_size) / (sizeof comm_payload_size[0])) {
      Serial.println("comm: warning: Received wrong type!");
      recv_buf_p = 0; // Reset state
      continue;
    }

    // Packet has reached the end
    if (recv_buf_p >= 2 && recv_buf_p == 2 + comm_payload_size[recv_buf[1]]) {
      // Copy data to output
      *type = (comm_type_t)recv_buf[1];
      memcpy(payload, recv_buf + 2, comm_payload_size[recv_buf[1]]);
      // Clear buffer
      recv_buf_p = 0;
      break;
    }
    // TODO: Add timeout mechanism
  }
  return false;
}

// Clear the read buffer as much as possible (to synchronize cycles of two devices) and return the last data packet
// If no error, *type will contain the received packet type, and payload will contain the actual data
// Returns true on error
// It is normal for this function to return an error when no data is received (non-blocking)
// Note: This function may cause some packets to be dropped if processing cannot keep up
// However, necessary packet dropping is worthwhile, otherwise the buffer will accumulate and real-time performance cannot be guaranteed
bool comm_recv_poll_last(comm_type_t *type, uint8_t payload[]) {
  bool last_ret = true; // Default to no data (error)
  
  bool ret = comm_recv_poll(type, payload);
  while (!ret) {
    if (comm_type_importance[*type]) { // Packet that cannot be ignored
      return ret;
    }
    last_ret = ret;
    ret = comm_recv_poll(type, payload);
  }
  return ret = last_ret;
}

// Returns true on error
bool comm_init(void) {
  bool ret = serial_init();
  if (ret) return true; // Propagate error
  recv_buf_p = 0;
  return false;
}