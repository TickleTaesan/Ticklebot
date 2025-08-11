# Jetson Orin Nano에서 NoMaD 자율주행 실행 가이드 (Ubuntu 22.04, ROS2 Humble, JetPack 6.2)

이 문서는 Jetson Orin Nano(JetPack 6.2, Ubuntu 22.04, ROS2 Humble)에서 이 저장소를 git clone 한 뒤 NoMaD 기반 자율주행을 실행하기 위한 절차를 정리합니다.

## 0) 사전 준비
- ROS2 Humble 설치(이미 설치되어 있다고 가정)
- 필수 ROS2 패키지 설치
  ```bash
  sudo apt update
  sudo apt install -y ros-humble-joy ros-humble-twist-mux ros-humble-v4l2-camera
  ```
- Python 3.10 확인
  ```bash
  python3 -V   # Python 3.10.x
  ```

## 1) 저장소 가져오기
```bash
cd ~
# 본인 Git URL 사용
git clone <YOUR_REPO_URL> nomad_sj
cd nomad_sj
```

## 2) Python 의존성 설치
- 기본 의존성(GPU-독립)
  ```bash
  sudo apt install -y python3-pip
  pip3 install --upgrade pip
  ```
- PyTorch/torchvision 설치(중요)
  - Jetson Orin(AArch64)은 x86_64와 설치 방식이 다릅니다.
  - JetPack 6.2에 맞는 NVIDIA 공식 가이드를 따르세요(컨테이너 또는 전용 wheel 권장).

- Jetson 전용 설치 순서 요약
  ```bash
  # 1) (Jetson 전용) NVIDIA 가이드로 PyTorch/torchvision 설치
  # 2) OpenCV(제트슨에서는 시스템 패키지 권장)
  sudo apt install -y python3-opencv
  # 3) 기타 의존성
  pip3 install -r requirements.txt
  ```

## 3) ROS2 패키지 빌드
```bash
# 터미널 1
source /opt/ros/humble/setup.bash
colcon build --base-paths deployment/nomad_deployment --packages-select nomad_deployment --symlink-install
source install/setup.bash
```
- 새 터미널을 열 때마다 다음을 순서대로 실행
  ```bash
  source /opt/ros/humble/setup.bash
  source ~/nomad_sj/install/setup.bash
  ```

## 4) 하드웨어/파라미터 설정
- 카메라: `deployment/nomad_deployment/config/camera_front.yaml`
  ```yaml
  camera:
    ros__parameters:
      image_size: [640, 480]
      device: /dev/video0
      fps: 30
  ```
- 모터/직렬 제어: `deployment/nomad_deployment/config/pd_controller.yaml`
  ```yaml
  pd_controller:
    ros__parameters:
      max_v: 0.4
      max_w: 0.8
      frame_rate: 9
      waypoint_topic: /waypoint
      vel_topic: /cmd_vel/nav
      reached_goal_topic: /topoplan/reached_goal
      wheel_separation: 0.26
      wheel_radius: 0.069
      use_serial: true          # 로봇에서 ODESC 사용 시 true
      serial_port: /dev/ttyUSB0 # 실제 포트 확인
      baudrate: 115200
      waypoint_timeout: 1.0
  ```
- 직렬 권한(한 번만)
  ```bash
  sudo usermod -aG dialout $USER
  # 재로그인 또는 재부팅 필요
  ```

## 5) 모델/가중치 설정
- 가중치 파일을 `deployment/model_weights/`에 배치
- `deployment/config/models.yaml`에서 사용할 모델 엔트리의 `ckpt_path`, `config_path`를 실제 경로로 맞춤
  ```yaml
  nomad:
    config_path: train/config/nomad.yaml
    ckpt_path: deployment/model_weights/nomad_latest.pth
  ```
- (선택) 레포 루트 고정이 필요하면
  ```bash
  export NOMAD_ROOT=~/nomad_sj
  ```

## 6) 토포맵 생성(선택)
- 방법 A) 라이브 카메라에서 주기적으로 이미지 저장
  - 터미널 1: 카메라 포함 파이프라인 실행
    ```bash
    ros2 launch nomad_deployment vint_locobot.launch.py
    ```
  - 터미널 2: 이미지 저장 노드 실행(1초 간격 예시)
    ```bash
    ros2 run nomad_deployment create_topomap --ros-args -p dir:=my_topo -p dt:=1.0 -p image_topic:=/usb_cam/image_raw
    # 저장: deployment/topomaps/images/my_topo/{0,1,2...}.png
    ```
- 방법 B) ros2 bag에서 생성(스크립트 제공)
  ```bash
  # 기록
  ./install/nomad_deployment/share/nomad_deployment/scripts/record_bag_ros2.sh my_bag
  # 재생 → 토포맵 생성
  ./install/nomad_deployment/share/nomad_deployment/scripts/create_topomap_ros2.sh my_topo my_bag
  ```

## 7) 실행 예시
- 탐색(Exploration; 카메라 관측 → 웨이포인트 → 모터 제어)
  ```bash
  ros2 launch nomad_deployment explore.launch.py use_camera:=true \
    model:=nomad \
    config:=/home/ubuntu/nomad_sj/train/config/nomad.yaml
  ```
- 내비게이션(Navigation; 토포맵 기반 목표 지향)
  ```bash
  ros2 launch nomad_deployment navigate.launch.py use_camera:=true \
    model:=nomad \
    config:=/home/ubuntu/nomad_sj/train/config/nomad.yaml \
    dir:=my_topo \
    goal_node:=-1
  ```

## 8) 카메라 없이 테스트(옵션)
- 폴더 이미지를 `/usb_cam/image_raw`로 퍼블리시
  ```bash
  ros2 run nomad_deployment image_dir_player --ros-args \
    -p dir:=/home/ubuntu/images \
    -p topic:=/usb_cam/image_raw \
    -p rate:=9.0
  ```
- Torch 미설치 상태에서 파이프라인 검증(더미 웨이포인트)
  ```bash
  ros2 run nomad_deployment explore_dummy
  # /waypoint → pd_controller → twist_mux → /cmd_vel 흐름 확인
  ```

## 9) 문제 해결(Troubleshooting)
- `package 'joy' not found` 등 패키지 에러 → `ros-humble-joy`, `ros-humble-twist-mux`, `ros-humble-v4l2-camera` 설치 확인
- `/dev/video0` 없음 → 카메라 연결/권한, `camera_front.yaml`의 `device` 수정
- `ModuleNotFoundError: torch` → Jetson용 PyTorch를 NVIDIA 가이드에 따라 설치
- 직렬 권한 오류 → `sudo usermod -aG dialout $USER` 후 재로그인, `serial_port` 경로 점검
- 웨이포인트 미발행 → 카메라 토픽(`/usb_cam/image_raw`), 모델/가중치 경로, `config` 경로 확인. 필요 시 `explore_dummy`로 테스트
- 매 터미널마다 환경 설정 필요 → 항상 `source /opt/ros/humble/setup.bash && source ~/nomad_sj/install/setup.bash`

(참고) 본 가이드는 RViz 설정을 포함하지 않습니다.