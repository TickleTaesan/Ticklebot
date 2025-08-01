/*
# File: comm.cpp

This file implements the communication protocol for the AstraHeadController firmware. It provides functions for serial initialization, sending and receiving data packets, and handling various communication types, including configuration and torque commands. The protocol is designed for robust, real-time data exchange between the head controller and other system components, with support for packet validation and buffer management.
*/
#include "comm.h"
#include <string.h>
#include <Arduino.h>
#include "main.h"

// Initialize serial port
// Return whether an error occurred
bool serial_init(void) {
  Serial.begin(921600);
  while (!Serial) delay(1);
  return false;
}

// Blocking output of a character
// c is the character to be sent
// Return whether an error occurred
bool serial_send_blocking(uint8_t c) {
  Serial.write(c);
  return false;
}

// Non-blocking polling for a character
// c is the character to be received
// Return whether an error occurred
bool serial_recv_poll(uint8_t *c) {
  // Not thread safe!!!
  if (Serial.available()) {
    *c = Serial.read();
    return false;
  } else {
    return true;
  }
}

// Packet sizes for different types
int comm_payload_size[] = {
  16, // COMM_TYPE_PING
  16, // COMM_TYPE_PONG
  16, // COMM_TYPE_CTRL
  16, // COMM_TYPE_FEEDBACK
  16, // COMM_TYPE_TORQUE
  16, // COMM_TYPE_CONFIG_WRITE
  16, // COMM_TYPE_CONFIG_READ
  16, // COMM_TYPE_CONFIG_FEEDBACK
};

// Packets that cannot be ignored
// Setting to true will cause comm_recv_poll_last to not skip this packet
// However, setting it to true will not
bool comm_type_importance[] = {
  false, // COMM_TYPE_PING
  false, // COMM_TYPE_PONG
  false, // COMM_TYPE_CTRL
  false, // COMM_TYPE_FEEDBACK
  true,  // COMM_TYPE_TORQUE
  true,  // COMM_TYPE_CONFIG_WRITE
  true,  // COMM_TYPE_CONFIG_READ
  true,  // COMM_TYPE_CONFIG_FEEDBACK
};

// Blocking send a data packet
// type passes data type, payload passes actual data
// Return whether an error occurred
bool comm_send_blocking(comm_type_t type, const uint8_t payload[]) {
  bool ret;
  ret = serial_send_blocking(0x5A); // 0b01011010 as header
  if (ret) return true;
  ret = serial_send_blocking((uint8_t)type); // 0b01011010 as header
  if (ret) return true;
  for (int i = 0; i < comm_payload_size[type]; ++i) {
    ret = serial_send_blocking(payload[i]);
    if (ret) return true;
  }
  return false;
}

static uint8_t recv_buf[2 + COMM_PAYLOAD_SIZE_MAX];
static int recv_buf_p;

// Try to receive a data packet
// If no error occurs, *type inside is the received data packet type, payload is the received actual data
// Return whether an error occurred
// This function occurs error very normally, if no data is received, it will return error (non-blocking)
bool comm_recv_poll(comm_type_t *type, uint8_t payload[]) {
  bool ret;
  while (true) {
    uint8_t buf;
    ret = serial_recv_poll(&buf);
    if (ret) return true; // No new data

    // Invalid data
    if (recv_buf_p == 0 && buf != 0x5A) {
      err_cnt[0] += 1;
      // fprintf(stderr, "comm: warning: Received wrong byte!");
      continue;
    }
    recv_buf[recv_buf_p++] = buf;

    // Buffer too small to store complete data packet
    assert(recv_buf_p <= sizeof recv_buf);

    // Received unknown type data packet
    // assert(recv_buf_p != 2 || recv_buf[1] < (sizeof comm_payload_size) / (sizeof comm_payload_size[0]));
    if (recv_buf_p == 2 && recv_buf[1] >= (sizeof comm_payload_size) / (sizeof comm_payload_size[0])) {
      err_cnt[1] += 1;
      // fprintf(stderr, "comm: warning: Received wrong type!");
      recv_buf_p = 0; // Reset state
      continue;
    }

    // Data packet ends
    if (recv_buf_p >= 2 && recv_buf_p == 2 + comm_payload_size[recv_buf[1]]) {
      // Copy data output
      *type = (comm_type_t)recv_buf[1];
      memcpy(payload, recv_buf + 2, comm_payload_size[recv_buf[1]]);
      // Clear buffer
      recv_buf_p = 0;
      break;
    }
    // TODO Add timeout mechanism
  }
  return false;
}

// Try to empty read buffer (synchronize two devices' cycle) and return the last group of data
// If no error occurs, *type inside is the received data packet type, payload is the received actual data
// Return whether an error occurred
// This function occurs error very normally, if no data is received, it will return error (non-blocking)
// Note: This function will cause some returned data packets to be lost (if the processing rhythm does not keep up)
// But necessary lost packets are worth it, otherwise the buffer will be accumulated, and the real-time cannot be guaranteed
bool comm_recv_poll_last(comm_type_t *type, uint8_t payload[]) {
  bool last_ret = true; // Default is no data (error)
  
  bool ret = comm_recv_poll(type, payload);
  while (!ret) {
    if (comm_type_importance[*type]) { // Packets that cannot be ignored
      return ret;
    }
    last_ret = ret;
    ret = comm_recv_poll(type, payload);
  }
  return ret = last_ret;
}

// Return whether an error occurred
bool comm_init(void) {
  bool ret = serial_init();
  if (ret) return true; // No new data
  recv_buf_p = 0;
  return false;
}