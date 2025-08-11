# 프로젝트 개요

이 저장소는 **로봇 제어 및 자율 주행을 위한 ROS 기반 배포 환경**과 **Diffusion Policy 기반의 로봇 학습/추론 프레임워크**를 통합한 프로젝트입니다.  
시뮬레이션 및 실제 로봇 환경에서 시각 데이터를 활용해 경로 계획, 원격 조작, 자율 주행 등을 지원합니다.

---

## 주요 구성

### 1. **deployment/**
실제 배포 환경 및 로봇 제어를 위한 ROS 노드와 스크립트가 포함되어 있습니다.
- **config/**: 카메라, 조이스틱, 속도 명령 멀티플렉싱(`cmd_vel_mux`) 등의 설정 YAML
- **src/**: ROS 기반 유틸리티 및 제어 스크립트
  - `image_dir_player.py`: 디렉토리 내 이미지를 ROS Image 토픽으로 송신
  - `joy_teleop.py`: 조이스틱 입력을 ROS 명령으로 변환
  - `navigate.py`: 로봇 내비게이션 로직 실행
  - `path_viz.py`: 웨이포인트 경로를 ROS Path 메시지로 시각화
  - `viz_overlay.py`: 이미지 위에 웨이포인트와 샘플 경로를 오버레이
  - `pd_controller.py`: PD 제어기 구현
  - `record_bag.sh`: ROS bag 기록 스크립트
  - 기타 ROS 통신용 토픽 정의(`topic_names.py`), 데이터 핸들링(`ros_data.py`) 등

---

### 2. **diffusion_policy/**
Diffusion 기반 정책 학습 및 추론을 위한 모듈.
- **codecs/**: 이미지 압축/복호화 지원 모듈
- **common/**: 체크포인트, 로깅, 데이터 처리 등 공통 유틸
- **config/**: 다양한 환경/작업(task)에 맞춘 학습 설정 YAML
- **dataset/**: 환경별 데이터셋 로더
- **env_runner/**: 학습 환경 실행기
- **gym_util/**: Gym 환경 래퍼 및 비디오 기록 유틸
- **model/**: Diffusion, Vision Encoder, BET, Transformer 등 신경망 모델
- **policy/**: 이미지/저차원 상태 기반 정책 구현
- **real_world/**: 실로봇(Realsense, SpaceMouse, UR 로봇) 지원 코드
- **scripts/**: 데이터 변환, 성능 측정 스크립트
- **workspace/**: 학습/추론 워크스페이스 클래스

---

### 3. **train/**
주행 모델(GNM, NoMaD, ViNT) 학습을 위한 코드.
- **config/**: 학습 환경/모델 설정 YAML
- **vint_train/**: 모델 구조 정의, 데이터 처리, 학습 루프, 시각화 유틸
- **process_bags.py**: ROS bag 파일을 학습 데이터로 변환
- **train.py**: 메인 학습 실행 스크립트

---

## 주요 기능

1. **실시간 이미지 스트리밍 및 제어**
   - 로컬 이미지 디렉토리를 ROS Image 토픽으로 전송
   - 조이스틱, 키보드 등을 통한 원격 제어
2. **자율 주행 경로 계획**
   - 웨이포인트 기반 경로 생성 및 시각화
   - PD 제어를 통한 주행 안정화
3. **Diffusion Policy 기반 행동 생성**
   - 시각 데이터 입력 → 정책 모델 → 행동 명령 생성
   - 시뮬레이션 및 실로봇 환경 모두 지원
4. **데이터셋 생성 및 전처리**
   - ROS bag 파일로부터 학습용 데이터셋 생성
   - 다양한 환경 설정 및 멀티 작업 지원

---

## 환경 설정

- Python 3.8
- ROS (Noetic 또는 ROS2 호환 가능, 설정에 따라 변경)
- 주요 의존성:
  - `torch`, `torchvision`, `opencv-python`
  - `efficientnet_pytorch`, `timm`, `transformers`
  - ROS Python 라이브러리 (`rospy`, `sensor_msgs`, `geometry_msgs` 등)

설치 예시:
```bash
conda env create -f deployment/src/deployment_environment.yml
conda activate nomad_train
