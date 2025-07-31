#include <Arduino.h>
#include <HardwareSerial.h>

HardwareSerial RobotSerial(1);


void setup() {
  // USB (PC/Orin과 디버깅용 시리얼)
  Serial.begin(115200);  
  delay(1000);

  // 로봇팔과 UART1 초기화 (921600bps, 8N1, RX=16, TX=17)
  RobotSerial.begin(921600, SERIAL_8N1, 16, 17);
  Serial.println("ESP32 ↔ Robot Arm UART Bridge Ready");
}

void loop() {
  // PC → 로봇팔 (USB → UART1)
  while (Serial.available()) {
    RobotSerial.write(Serial.read());
  }

  // 로봇팔 → PC (UART1 → USB)
  while (RobotSerial.available()) {
    Serial.write(RobotSerial.read());
  }
}