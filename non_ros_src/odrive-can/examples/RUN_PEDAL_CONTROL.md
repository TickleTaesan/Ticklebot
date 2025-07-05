# 페달로 BLDC 모터 제어 실행 가이드

## 🚀 실행 순서

### 1. 하드웨어 연결 확인
```bash
# ESP32 연결 확인
ls /dev/ttyUSB* /dev/ttyACM*

# CAN 인터페이스 확인 (ODrive 연결)
ip link show can0
```

### 2. ESP32 펌웨어 업로드 (필요시)
```bash
cd ~/robot_project/src/AstraFirmwares/AstraPedalController
pio run --target upload
```

### 3. CAN 인터페이스 활성화
```bash
# CAN 모듈 로드
sudo modprobe can
sudo modprobe can_raw

# CAN 인터페이스 설정 (ODrive 기본: 250kbps)
sudo ip link set can0 type can bitrate 250000
sudo ip link set up can0

# 상태 확인
ip link show can0
```

### 4. ODrive 연결 테스트
```bash
# 다른 터미널에서 CAN 메시지 확인
candump can0

# ODrive 하트비트 메시지가 보이면 정상 (1초마다)
# 예: can0  001   [8]  00 00 00 00 00 00 00 00
```

### 5. 페달 제어 프로그램 실행
```bash
cd ~/robot_project/src/astra_ws/non_ros_src/odrive-can/examples
python3 pedal_usage.py
```

## 📊 예상 출력

### 정상 시작시:
```
시리얼 포트 /dev/ttyUSB0 연결됨
모터 1 시작 중...
모터 2 시작 중...
페달 제어 시작! (Ctrl+C로 종료)
페달: [2048, 2048] → 위치: [   0.0,    0.0]
페달: [2100, 1950] → 위치: [   1.3,   -2.4]
...
```

### ESP32 연결 실패시:
```
시리얼 포트 연결 실패: [Errno 2] No such file or directory: '/dev/ttyUSB0'
ESP32가 연결되었는지 확인하세요
```

### ODrive 연결 실패시:
```
Error: No heartbeat message received.
```

## 🔧 문제 해결

### 1. 시리얼 포트 문제
```bash
# 포트 확인
dmesg | tail
ls /dev/tty*

# 권한 확인
sudo chmod 666 /dev/ttyUSB0
sudo usermod -a -G dialout $USER
```

### 2. CAN 인터페이스 문제
```bash
# 인터페이스 재시작
sudo ip link set down can0
sudo ip link set can0 type can bitrate 250000
sudo ip link set up can0
```

### 3. ODrive 설정 확인
- ODrive 웹 UI 접속: `http://localhost:8080`
- CAN 설정 확인:
  - `odrv0.axis0.config.can.node_id = 0`
  - `odrv0.axis1.config.can.node_id = 1`
  - `odrv0.can.config.baud_rate = 250000`

## ⚠️ 안전 주의사항

1. **첫 테스트시 위치 범위 줄이기**:
   ```python
   # pedal_usage.py 수정
   pos1 = (pedal_values[0] - 2048) / 2048.0 * 5.0  # 50.0 → 5.0
   pos2 = (pedal_values[1] - 2048) / 2048.0 * 5.0  # 50.0 → 5.0
   ```

2. **모터 자유 회전 확인**: 모터가 막히지 않았는지 확인

3. **비상 정지**: 언제든 `Ctrl+C`로 즉시 중단 가능

## 🎛️ 제어 설정 조정

### 위치 범위 조정:
```python
# 작게: 민감도 감소
pos1 = (pedal_values[0] - 2048) / 2048.0 * 10.0

# 크게: 민감도 증가  
pos1 = (pedal_values[0] - 2048) / 2048.0 * 100.0
```

### 제어 주기 조정:
```python
await asyncio.sleep(0.01)  # 100Hz (기본)
await asyncio.sleep(0.02)  # 50Hz (부드럽게)
await asyncio.sleep(0.005) # 200Hz (빠르게)
```

### 모터 게인 조정:
```python
motor1.set_pos_gain(3.0)    # 기본값
motor1.set_pos_gain(1.0)    # 부드럽게
motor1.set_pos_gain(5.0)    # 민감하게
```

## 📈 모니터링

### 실시간 CAN 메시지:
```bash
candump can0 | grep -E "(001|009)"  # 하트비트, 엔코더
```

### 시리얼 데이터 확인:
```bash
hexdump -C /dev/ttyUSB0
```

## 성공 확인

✅ ESP32에서 페달값 전송  
✅ 파이썬에서 시리얼 수신  
✅ ODrive CAN 통신  
✅ 모터 위치 제어  
✅ 실시간 피드백  

모든 단계가 성공하면 페달을 움직일 때 모터가 연동해서 움직입니다! 