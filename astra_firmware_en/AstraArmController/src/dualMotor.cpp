/*
# File: dualMotor.cpp

This file implements dual motor control logic for the AstraArmController firmware. It provides functions for reading and updating joint and non-joint positions, managing trapezoidal trajectories, and handling torque and initialization commands. The code ensures coordinated motion and feedback for multiple motors in real-time.
*/
#include <Arduino.h>
#include <SCServo.h>
#include "config.h"
#include "dualMotor.h"
#include "trapTraj.hpp"
#include <esp_task_wdt.h>

SMS_STS sts;

#define TIMER_TIMEOUT_US 15000 // change: current_meas_period
// velocity update in servo seems at 50Hz.

esp_timer_handle_t timer;

TrapezoidalTrajectory traj[JOINT_NUM];
float last_pos[JOINT_NUM] = { 2048, 2048, 2048, 2048, 2048, 2048 };
float last_vel[JOINT_NUM] = { 0 };

void read_pos() {
  int raw_pos[JOINT_NUM];
  for (int i = 0; i < JOINT_NUM; ++i) {
    raw_pos[i] = sts.ReadPos(4 + i);
    if (sts.Err == 1) {
      Serial.print("Error reading #"); Serial.print(4 + i); Serial.print(", checkout your wire connection"); Serial.println();
    }
  }
  // Zero offset
  for (int i = 0; i < JOINT_NUM; ++i) {
    raw_pos[i] -= config.init_pos[i];
    if (raw_pos[i] < 0) raw_pos[i] += 4096;
    raw_pos[i] += 2048;
    if (raw_pos[i] >= 4096) raw_pos[i] -= 4096;
  }
  float pos[JOINT_NUM];
  for (int i = 0; i < JOINT_NUM; ++i) {
    pos[i] = raw_pos[i];
  }
  float vel[JOINT_NUM];
  for (int i = 0; i < JOINT_NUM; ++i) {
    vel[i] = (pos[i] - last_pos[i]) / TIMER_TIMEOUT_US * 1000000;
    float filter_vel = 0.2;
    vel[i] = vel[i] * filter_vel + last_vel[i] * (1 - filter_vel);
    last_pos[i] = pos[i];
    last_vel[i] = vel[i];
  }
}

bool torque_enabled = false;
int setupTorque_enable = 0;
bool updateSetupTorque = false;

void doSetupTorque(int enable) {
  if (enable == 0) {
    torque_enabled = false;
  } else if (enable == 1) {
    torque_enabled = true;
  }
  for (int i = 0; i < JOINT_NUM; ++i) {
    sts.EnableTorque(4 + i, enable);
  }
  if (enable == 1) {
    for (int i = 0; i < JOINT_NUM; ++i) {
      last_vel[i] = 0;
    }
    read_pos();
    uint16_t pos[JOINT_NUM];
    for (int i = 0; i < JOINT_NUM; ++i) {
      pos[i] = last_pos[i];
    }
    for (int i = 0; i < JOINT_NUM; ++i) {
      traj[i].trajectory_done_ = true;
      traj[i].Xf_ = pos[i];
      traj[i].pos_setpoint_ = pos[i];
    }
    dualMotorUpdatePos(pos);
    Serial.println("setup torque");
  }
}

void setupTorque(int enable) {
  setupTorque_enable = enable;
  updateSetupTorque = true;
}

int initJoint_id = 0;
int initJoint_offset = 0;
bool updateInitJoint = false;

void doInitJoint(int id, int offset) {
  Serial.printf("INIT_JOINT id=%d offset=%d\n", id, offset);
  sts.EnableTorque(id, 128);
  Serial.printf("Set current position as mid\n");
  sts.unLockEprom(id);//unlock EPROM-SAFE
  int offset_servo = sts.readWord(id, SMS_STS_OFS_L);
  if (offset_servo > 2048) offset_servo = -(offset_servo - 2048);
  Serial.printf("Offset in servo: %d\n", offset_servo);
  offset_servo -= offset;
  if (offset_servo < -2048) offset_servo += 4096;
  if (offset_servo >= 2048) offset_servo -= 4096;
  if (offset_servo < 0) offset_servo = -(offset_servo) + 2048;
  sts.writeWord(id, SMS_STS_OFS_L, offset_servo);
  sts.LockEprom(id);//EPROM-SAFE locked
  offset_servo = sts.readWord(id, SMS_STS_OFS_L);
  if (offset_servo > 2048) offset_servo = -(offset_servo - 2048);
  Serial.printf("Updated offset in servo: %d\n", offset_servo);
}

void initJoint(int id, int offset) {
  initJoint_id = id;
  initJoint_offset = offset;
  updateInitJoint = true;
}

float pidtune_kp = 0, pidtune_kd = 0, pidtune_ki = 0, pidtune_ki_max = 800, pidtune_kp2 = 0, pidtune_kp2_err_point = 0, pidtune_ki_clip_thres = 10, pidtune_ki_clip_coef = 0.5;

void timer_callback(void *arg) {
  if (updateSetupTorque) {
    updateSetupTorque = false;
    doSetupTorque(setupTorque_enable);
  }
  if (updateInitJoint) {
    updateInitJoint = false;
    doInitJoint(initJoint_id, initJoint_offset);
  }
  if (!torque_enabled) {
    return;
  }
  if (!config.init_pos_inited) {
    Serial.println("Joint pos is not inited");
    return;
  }
  read_pos();
  float goal_pos[JOINT_NUM];
  for (int i = 0; i < JOINT_NUM; ++i) {
    traj[i].update();
    goal_pos[i] = traj[i].pos_setpoint_;
  }
  float kp = pidtune_kp, kd = pidtune_kd, ki = pidtune_ki, kp2 = pidtune_kp2, kp2_err_point = pidtune_kp2_err_point;
  static float last_err[JOINT_NUM];
  static float i_out[JOINT_NUM] = {};
  float out[JOINT_NUM] = {};
  float debug_signal[JOINT_NUM];
  static float sticktion_compensation = 60;
  sticktion_compensation = -sticktion_compensation;
  for (int i = 0; i < JOINT_NUM; ++i) {
    float err = goal_pos[i] - last_pos[i];
    float p_out = kp * err + (kp2 - kp) * (err > kp2_err_point ? err - kp2_err_point : 0) + (kp2 - kp) * (err < -kp2_err_point ? err + kp2_err_point : 0);
    i_out[i] += ki * err;
    if (i_out[i] > pidtune_ki_max) i_out[i] = pidtune_ki_max;
    if (i_out[i] < -pidtune_ki_max) i_out[i] = -pidtune_ki_max;
    float d_out = kd * (err - last_err[i]);
    out[i] = sticktion_compensation + p_out + i_out[i] + d_out;
    last_err[i] = err;
  }
  float raw_out[JOINT_NUM];
  for (int i = 0; i < JOINT_NUM; ++i) {
    raw_out[i] = out[i];
  }
  for (int i = 0; i < JOINT_NUM; ++i) {
    int ready_send = -raw_out[i];
    if (ready_send > 800) ready_send = 800;
    if (ready_send < -800) ready_send = -800;
    if (ready_send < 0) ready_send = -(ready_send) + 1024;
    sts.writeWord(4 + i, SCSCL_GOAL_TIME_L, ready_send);
  }
}

void dualMotorSetup() {
#define S_RXD 18
#define S_TXD 19
  Serial1.begin(1000000, SERIAL_8N1, S_RXD, S_TXD);
  while (!Serial1) delay(1);
  sts.pSerial = &Serial1;
  sts.writeWord(15, SMS_STS_TORQUE_LIMIT_L, 500); // Protect servo
  read_pos();
  const esp_timer_create_args_t timer_args = {
    .callback = &timer_callback
  };
  ESP_ERROR_CHECK(esp_timer_create(&timer_args, &timer));
  ESP_ERROR_CHECK(esp_timer_start_periodic(timer, TIMER_TIMEOUT_US));
}

void dualMotorUpdatePos(uint16_t pos[]) {
  if (!torque_enabled) {
    setupTorque(1);
  }
  for (int i = 0; i < JOINT_NUM; ++i) {
    traj[i].planTrapezoidal(pos[i], traj[i].pos_setpoint_, traj[i].vel_setpoint_);
  }
}

void dualMotorReadPos(uint16_t read_pos[]) {
  for (int i = 0; i < JOINT_NUM; ++i) {
    read_pos[i] = last_pos[i];
  }
}