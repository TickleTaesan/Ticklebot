# LeRobot 프로젝트 문서

이 문서는 LeRobot, LeRobot ROS, LeRobot ROS 2 워크스페이스를 포함하는 로봇 프로젝트의 전체 구조와 주요 파일에 대한 설명을 담고 있습니다.

## 1. 프로젝트 개요

이 프로젝트는 PyTorch 기반의 로봇 학습 라이브러리인 **LeRobot**을 중심으로, **ROS (Robot Operating System)** 와의 연동을 통해 실제 로봇 및 시뮬레이션 환경에서 머신러닝 모델을 훈련하고 평가할 수 있도록 구성되어 있습니다.

크게 세 가지 주요 부분으로 나뉩니다.

1.  **`lerobot/`**: 핵심 로봇 학습 라이브러리 (Python)
2.  **`lerobot_ws/`**: ROS 2 워크스페이스 (시뮬레이션, 컨트롤러)
3.  **`lerobot-ros/`**: LeRobot과 ROS를 연결하는 Python 패키지

## 2. `lerobot/` - 핵심 라이브러리

PyTorch를 기반으로 하는 메인 로봇 학습 라이브러리입니다. 데이터셋 처리, 정책 모델, 로봇 인터페이스, 훈련 및 평가 스크립트 등 핵심 기능을 포함합니다.

### 주요 디렉토리 구조

* **`.github/`**: GitHub 워크플로우 및 이슈/PR 템플릿이 포함된 디렉토리입니다. CI/CD 및 프로젝트 관리를 위한 설정 파일들이 있습니다.
    * `workflows/`: `fast_tests.yml`, `full_tests.yml`, `release.yml` 등 자동화된 테스트 및 배포 파이프라인이 정의되어 있습니다.
* **`docs/`**: 프로젝트 문서 관련 파일들이 위치합니다.
* **`examples/`**: 라이브러리 사용법을 보여주는 예제 코드들이 있습니다.
    * `1_load_lerobot_dataset.py`: LeRobot 데이터셋을 로드하는 예제입니다.
    * `2_evaluate_pretrained_policy.py`: 사전 훈련된 정책을 평가하는 예제입니다.
    * `3_train_policy.py`: 정책을 훈련하는 예제입니다.
* **`src/lerobot/`**: 실제 라이브러리 소스 코드가 위치합니다.
    * **`cameras/`**: `OpenCV`, `RealSense` 등 다양한 카메라 인터페이스를 관리합니다.
    * **`datasets/`**: `LeRobotDataset` 클래스를 포함하여 데이터셋을 로드하고 처리하는 기능을 담당합니다.
    * **`envs/`**: `Gymnasium` 기반의 시뮬레이션 환경 설정을 관리합니다.
    * **`motors/`**: `Dynamixel`, `Feetech` 등 모터와의 통신 및 제어를 담당합니다.
    * **`policies/`**: `ACT`, `Diffusion Policy`, `TDMPC` 등 다양한 모방 학습 및 강화 학습 정책 모델이 구현되어 있습니다.
    * **`robots/`**: `SO-101`, `LeKiwi`, `Stretch3` 등 실제 로봇 하드웨어와의 인터페이스를 정의합니다.
    * **`teleoperators/`**: `gamepad`, `keyboard`, `leader arm` 등 원격 조종 장치 인터페이스를 관리합니다.
    * **`scripts/`**: `train.py`, `eval.py`, `record.py` 등 주요 실행 스크립트들이 포함되어 있습니다.
* **`tests/`**: 라이브러리의 각 기능에 대한 단위 테스트 및 통합 테스트 코드가 있습니다.

## 3. `lerobot_ws/` - ROS 2 워크스페이스

ROS 2 패키지들을 관리하는 워크스페이스입니다. 주로 Gazebo 시뮬레이션, MoveIt 2를 이용한 모션 플래닝, ROS 2 컨트롤러 설정을 다룹니다.

### 주요 패키지

* **`lerobot_controller/`**: `ros2_control`을 위한 컨트롤러 설정(`so101_controllers.yaml`)과 실행 파일(`so101_controller.launch.py`)을 포함합니다.
* **`lerobot_description/`**: 로봇의 외형과 물리적 속성을 정의하는 URDF (`.xacro`) 파일과, 이를 Gazebo 시뮬레이션 및 RViz에서 시각화하기 위한 실행 파일들을 포함합니다.
* **`lerobot_moveit/`**: MoveIt 2 설정을 담고 있습니다. SRDF 파일(`so101.srdf`), 운동학 설정(`kinematics.yaml`), 컨트롤러 설정(`moveit_controllers.yaml`) 및 MoveIt 실행 파일(`so101_moveit.launch.py`)이 포함됩니다.

## 4. `lerobot-ros/` - LeRobot-ROS 연동 패키지

`lerobot` 라이브러리와 ROS 2를 연결하는 Python 패키지입니다. ROS 2 환경에서 LeRobot의 데이터 수집, 원격 조종, 정책 실행 기능을 사용할 수 있도록 래퍼(wrapper) 역할을 합니다.

### 주요 디렉토리 구조

* **`lerobot_ros/`**: ROS 2 노드와 인터페이스를 구현한 소스 코드입니다.
    * **`robots/`**: `ros.py` 파일은 ROS 2 환경에서 `lerobot`의 `Robot` 인터페이스를 구현하여, 토픽(topic)과 서비스(service)를 통해 로봇을 제어합니다.
    * **`teleoperators/`**: `gamepad_6dof.py` 와 같이 ROS 2의 `Twist` 메시지 등을 사용하여 6자유도 원격 조종을 구현합니다.
* **`scripts/`**: ROS 2 환경에서 사용할 수 있도록 수정된 `record.py`, `replay.py`, `teleoperate.py` 스크립트가 있습니다.

## 5. 주요 실행 스크립트

이 프로젝트는 `lerobot` 라이브러리를 통해 다양한 작업을 수행할 수 있는 커맨드라인 스크립트를 제공합니다. (`lerobot/src/lerobot.egg-info/entry_points.txt` 참고)

* **`lerobot-calibrate`**: 로봇 모터를 보정합니다.
* **`lerobot-record`**: 원격 조종을 통해 로봇 시연 데이터를 수집하고 데이터셋을 생성합니다.
* **`lerobot-teleoperate`**: 리더 암(leader arm)이나 게임패드 등으로 로봇을 실시간으로 원격 조종합니다.
* **`lerobot-train`**: 수집된 데이터셋을 사용하여 정책 모델을 훈련합니다.
* **`lerobot-eval`**: 훈련된 정책을 시뮬레이션 또는 실제 로봇 환경에서 평가합니다.
* **`lerobot-replay`**: 데이터셋에 기록된 에피소드를 로봇으로 재현합니다.