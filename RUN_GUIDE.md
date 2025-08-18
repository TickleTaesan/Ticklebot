## 실행 가이드 (ODESC 모터 자율주행)

### 전제 조건
- ROS2 Humble 환경 활성화
```bash
source /opt/ros/humble/setup.bash
```
- 프로젝트 루트에서 Python 모듈 경로 설정
```bash
export PYTHONPATH=$PWD/src
```
- 모델 가중치 존재: `model_weights/nomad.pth`
- ODESC 3.6 56V 보드와 BLDC 모터 2개 연결 완료
- UART 연결: `/dev/ttyUSB0` (config/robot.yaml에서 설정 가능)

---

### 완전한 자율주행 실행 (4개 터미널 필요)

#### 터미널 1: 카메라 실행
```bash
source /opt/ros/humble/setup.bash
ros2 run v4l2_camera v4l2_camera_node --ros-args \
  -p video_device:=/dev/video0 -p image_size:=[320,240] \
  -p pixel_format:=YUYV -p output_encoding:=rgb8
```
- 결과: `/image_raw` 토픽으로 카메라 이미지 발행

#### 터미널 2: NoMaD 모델 실행
```bash
source /opt/ros/humble/setup.bash
export PYTHONPATH=$PWD/src
python3 src/visualnav_transformer/deployment/src/explore.py -m nomad
```
- 결과: `/waypoint` 토픽으로 예측된 경로점 발행

#### 터미널 3: waypoint → cmd_vel 변환
```bash
source /opt/ros/humble/setup.bash
python3 scripts/publish_cmd.py
```
- 결과: `/cmd_vel` 토픽으로 로봇 속도 명령 발행

#### 터미널 4: ODESC 모터 제어
```bash
source /opt/ros/humble/setup.bash
python3 scripts/cmdvel_to_odesc.py
```
- 결과: UART로 ODESC 보드에 모터 속도 명령 전송

### 동작 확인
각각 별도 터미널에서 실행:
```bash
# 카메라 이미지 확인
ros2 topic hz /image_raw

# waypoint 생성 확인  
ros2 topic echo /waypoint -n 3

# 속도 명령 확인
ros2 topic echo /cmd_vel -n 3
```

---

### 고급: Topomap 기반 내비게이션

#### 1) Topomap 생성 (선택사항)
```bash
# 터미널 1: 카메라 실행 (위와 동일)
# 터미널 2: 토포맵 생성
python3 src/visualnav_transformer/deployment/src/create_topomap.py -d topomap -t 1.0
```
- 결과: `topomaps/images/topomap/0.png, 1.png, ...`
- 1초마다 이미지 저장, 수동으로 로봇을 움직여서 환경 탐색

#### 2) Topomap 기반 내비게이션
```bash
# 터미널 2: NoMaD 내비게이션 모델 (explore.py 대신)
python3 src/visualnav_transformer/deployment/src/navigate.py -m nomad -d topomap -g -1
# 터미널 3, 4: 위와 동일 (publish_cmd.py, cmdvel_to_odesc.py)
```

---

### 하드웨어 설정 (config/robot.yaml)
```yaml
# 모터/바퀴 사양 (실제 측정값으로 수정 필요)
wheel_radius: 0.069          # [m] 바퀴 반지름
wheel_separation: 0.26       # [m] 바퀴간 거리
gear_ratio: 1.0              # 감속비 (직결시 1.0)

# UART 통신 설정
uart_port: "/dev/ttyUSB0"    # ODESC 연결 포트
uart_baud: 115200            # 통신 속도

# 모터 설정
left_motor_index: 0          # 왼쪽 모터 ID
right_motor_index: 1         # 오른쪽 모터 ID
motor_max_turns: 20.0        # 최대 모터 속도 [turn/s]
watchdog_timeout: 0.5        # 안전 정지 시간 [s]
```

### 문제 해결
- **카메라 안 됨**: `ls /dev/video*` 확인, USB 재연결
- **ODESC 안 됨**: `ls /dev/ttyUSB*` 확인, UART 케이블 점검
- **모터 역방향**: `config/robot.yaml`에서 `invert_left/right: true`
- **속도 조절**: `max_v`, `max_w`, `motor_max_turns` 값 조정


