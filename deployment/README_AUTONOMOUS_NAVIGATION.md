# NoMaD 자율주행 실행 가이드 (컨테이너 기반)

이 가이드는 Jetson Orin + Jetpack 6.2 (Ubuntu 22.04)에서 Docker 컨테이너를 사용한 NoMaD 모델 완전 자동화 자율주행을 위한 실행 방법을 설명합니다.

## 📋 사전 요구사항

- Jetson Orin (CUDA 지원)
- Jetpack 6.2 (Ubuntu 22.04 기반)
- Docker 설치
- USB 카메라
- ODESC 3.6 v0.5.1 BLDC 모터 드라이버

## 🚀 환경 설정

### 1단계: Docker 설치 (Jetson Orin)
```bash
# Docker 설치
sudo apt update
sudo apt install docker.io docker-compose

# Docker 권한 설정
sudo usermod -aG docker $USER
newgrp docker

# Docker 서비스 시작
sudo systemctl start docker
sudo systemctl enable docker
```

### 2단계: 컨테이너 빌드
```bash
# 1. 프로젝트 디렉토리로 이동
cd /Ubuntu-22.04/home/kowook/robot_project/src/nomad/deployment

# 2. Docker 이미지 빌드
docker build -t nomad-autonomous-navigation .

# 3. 하드웨어 연결 확인
ls /dev/video*          # USB 카메라
ls /dev/ttyUSB*         # ODESC 모터 드라이버
```

### 3단계: 컨테이너 실행 스크립트 생성
```bash
# 컨테이너 실행 스크립트 생성
cat > run_container.sh << 'EOF'
#!/bin/bash

# 하드웨어 디바이스 마운트
DEVICES=""
if [ -e "/dev/video0" ]; then
    DEVICES="$DEVICES --device=/dev/video0:/dev/video0"
fi
if [ -e "/dev/ttyUSB0" ]; then
    DEVICES="$DEVICES --device=/dev/ttyUSB0:/dev/ttyUSB0"
fi

# 네트워크 설정 (ROS 통신용)
NETWORK="--network=host"

# 컨테이너 실행
docker run -it --rm \
    --runtime=nvidia \
    --gpus all \
    $DEVICES \
    $NETWORK \
    --privileged \
    -v /tmp/.X11-unix:/tmp/.X11-unix \
    -e DISPLAY=$DISPLAY \
    -v $(pwd):/workspace/nomad \
    nomad-autonomous-navigation
EOF

chmod +x run_container.sh
```

## 🎯 완전 자동화 자율주행 실행

### 방법 1: 컨테이너 내부에서 수동 실행

#### 1단계: 컨테이너 실행
```bash
# 컨테이너 실행
./run_container.sh

# 컨테이너 내부에서 환경 설정
source /workspace/setup_env.sh
cd /workspace/nomad/deployment
```

#### 2단계: 자동화 스크립트 실행 (컨테이너 내부)
```bash
# 자동화 스크립트 생성 (컨테이너용)
cat > src/container_autonomous.sh << 'EOF'
#!/bin/bash

# Create a new tmux session
session_name="nomad_container_$(date +%s)"
tmux new-session -d -s $session_name

# Split the window into four panes
tmux selectp -t 0
tmux splitw -h -p 50
tmux selectp -t 0
tmux splitw -v -p 50
tmux selectp -t 2
tmux splitw -v -p 50
tmux selectp -t 0

# Run the roslaunch command in the first pane
tmux select-pane -t 0
tmux send-keys "source /workspace/setup_env.sh" Enter
tmux send-keys "cd /workspace/nomad/deployment" Enter
tmux send-keys "roslaunch src/vint_locobot.launch" Enter

# Run the explore.py script in the second pane
tmux select-pane -t 1
tmux send-keys "source /workspace/setup_env.sh" Enter
tmux send-keys "cd /workspace/nomad/deployment" Enter
tmux send-keys "python src/explore.py $@" Enter

# Run the create_topomap.py script in the third pane
tmux select-pane -t 2
tmux send-keys "source /workspace/setup_env.sh" Enter
tmux send-keys "cd /workspace/nomad/deployment" Enter
tmux send-keys "python src/create_topomap.py --dir auto_explored --dt 1.0" Enter

# Run the pd_controller.py script in the fourth pane
tmux select-pane -t 3
tmux send-keys "source /workspace/setup_env.sh" Enter
tmux send-keys "cd /workspace/nomad/deployment" Enter
tmux send-keys "python src/pd_controller.py" Enter

# Attach to the tmux session
tmux -2 attach-session -t $session_name
EOF

chmod +x src/container_autonomous.sh

# 자동화 스크립트 실행
./src/container_autonomous.sh --model nomad --num-samples 8
```

### 방법 2: 호스트에서 직접 실행 (권장)

```bash
# 호스트에서 컨테이너 실행 및 자동화 스크립트 실행
docker run -it --rm \
    --runtime=nvidia \
    --gpus all \
    --device=/dev/video0:/dev/video0 \
    --device=/dev/ttyUSB0:/dev/ttyUSB0 \
    --network=host \
    --privileged \
    -v $(pwd):/workspace/nomad \
    nomad-autonomous-navigation \
    bash -c "source /workspace/setup_env.sh && cd /workspace/nomad/deployment && ./src/container_autonomous.sh --model nomad --num-samples 8"
```

## 🔧 주요 파라미터 설명

### explore.py 파라미터
- `--model nomad`: NoMaD 모델 사용
- `--num-samples 8`: Diffusion 샘플링 개수
- `--waypoint 2`: 사용할 waypoint 인덱스 (0-4)

### navigate.py 파라미터
- `--model nomad`: NoMaD 모델 사용
- `--dir auto_explored`: 토폴로지 맵 디렉토리
- `--goal-node -1`: 목표 노드 (-1 = 마지막 노드)
- `--radius 4`: 로컬라이제이션 반경
- `--close-threshold 3`: 다음 노드 전환 임계값

## 📊 모니터링 및 디버깅

### 컨테이너 내부에서 토픽 모니터링
```bash
# 컨테이너 내부에서 실행
source /workspace/setup_env.sh

# 주요 토픽 확인
rostopic echo /waypoint          # AI 예측 waypoint
rostopic echo /cmd_vel_mux/output # 실제 로봇 속도
rostopic echo /usb_cam/image_raw  # 카메라 이미지
rostopic echo /topoplan/reached_goal # 목표 도달 여부
```

### 시각화 (X11 포워딩 필요)
```bash
# 호스트에서 X11 서버 허용
xhost +local:docker

# 컨테이너 내부에서 시각화
rqt_image_view /usb_cam/image_raw
rqt_graph
```

## 🛡️ 안전 설정

### robot.yaml 설정 (컨테이너 내부)
```yaml
max_v: 2.33    # 최대 선속도 (m/s)
max_w: 5.0     # 최대 각속도 (rad/s)
frame_rate: 4  # 프레임 레이트 (Hz)
```

### 비상 정지
- `pd_controller.py`에서 bumper 감지 시 자동 정지
- waypoint 타임아웃으로 안전장치
- 속도 제한으로 안전한 주행

## 🔍 문제 해결

### 일반적인 문제들

1. **Docker 권한 문제**
   ```bash
   sudo usermod -aG docker $USER
   newgrp docker
   ```

2. **CUDA 인식 안됨**
   ```bash
   # 컨테이너 내부에서
   nvidia-smi
   python3 -c "import torch; print(torch.cuda.is_available())"
   ```

3. **하드웨어 디바이스 인식 안됨**
   ```bash
   # 호스트에서
   ls -la /dev/video*
   ls -la /dev/ttyUSB*
   
   # 컨테이너 내부에서
   ls -la /dev/video*
   ls -la /dev/ttyUSB*
   ```

4. **ROS 토픽 연결 안됨**
   ```bash
   # 컨테이너 내부에서
   source /workspace/setup_env.sh
   rostopic list
   ```

5. **메모리 부족**
   ```bash
   # 컨테이너 실행 시 메모리 제한 설정
   docker run --memory=4g --shm-size=2g ...
   ```

6. **X11 디스플레이 문제**
   ```bash
   # 호스트에서
   xhost +local:docker
   
   # 컨테이너 실행 시
   -e DISPLAY=$DISPLAY -v /tmp/.X11-unix:/tmp/.X11-unix
   ```

## 📁 파일 구조

```
deployment/
├── Dockerfile                    # 컨테이너 이미지 정의
├── run_container.sh              # 컨테이너 실행 스크립트
├── src/
│   ├── explore.py               # 자동 탐색
│   ├── navigate.py              # 내비게이션
│   ├── pd_controller.py         # 모터 제어
│   ├── create_topomap.py        # 토폴로지 맵 생성
│   ├── vint_locobot.launch      # 기본 시스템
│   └── container_autonomous.sh  # 컨테이너용 자동화 스크립트
├── config/
│   ├── robot.yaml               # 로봇 설정
│   └── models.yaml              # 모델 설정
├── model_weights/
│   └── nomad.pth                # NoMaD 모델 가중치
└── topomaps/
    └── images/                  # 토폴로지 맵 이미지
```

## 🎯 실행 순서 요약

1. **환경 설정**: Docker 설치 + 컨테이너 빌드
2. **컨테이너 실행**: 하드웨어 디바이스 마운트 + 네트워크 설정
3. **자동화 실행**: 컨테이너 내부에서 NoMaD 자동 탐색
4. **토폴로지 맵**: 탐색 과정의 이미지들을 저장
5. **내비게이션**: 저장된 맵을 사용해서 목표까지 자율주행

## 🚀 빠른 시작

```bash
# 1. 컨테이너 빌드
docker build -t nomad-autonomous-navigation .

# 2. 컨테이너 실행 및 자동화
./run_container.sh

# 3. 컨테이너 내부에서
source /workspace/setup_env.sh
cd /workspace/nomad/deployment
./src/container_autonomous.sh --model nomad --num-samples 8
```

**결과**: 수동 조작 없이 완전 자동화된 자율주행!
