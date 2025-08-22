# LeRobot ROS: LeRobot 프레임워크를 위한 ROS 2 통합 프로젝트

## 개요

이 프로젝트는 Hugging Face의 `LeRobot` 머신러닝 프레임워크를 ROS 2(Robot Operating System 2) 생태계와 통합하여 **SO-101** 로봇 팔을 제어하고 시뮬레이션하기 위해 설계되었습니다. 이 프로젝트는 크게 두 가지 주요 부분으로 구성됩니다.

1.  **`lerobot_ws`**: SO-101 로봇의 시뮬레이션, 제어, 모션 플래닝을 담당하는 표준 ROS 2 워크스페이스입니다.
2.  **`lerobot-ros`**: `LeRobot`의 고수준 API(데이터 수집, 정책 실행 등)와 ROS 2의 저수준 로봇 제어를 연결하는 경량 파이썬 래퍼(wrapper)입니다.

이를 통해 사용자는 Gazebo 시뮬레이터에서 로봇을 원격으로 조종하고, 그 과정을 데이터셋으로 기록하며, 수집된 데이터를 사용해 강화학습 정책을 훈련하고 재현하는 등 `LeRobot`의 강력한 기능들을 ROS 2 기반의 모든 로봇에 쉽게 적용할 수 있습니다.

---

## 주요 구성 요소

### 1. `lerobot_ws` (ROS 2 워크스페이스)

`colcon`으로 빌드되는 이 워크스페이스는 SO-101 로봇을 ROS 2 환경에서 구동하기 위한 핵심 패키지들을 포함합니다.

-   **`lerobot_description`**:
    -   로봇의 3D 모델(URDF/Xacro), 관절, 링크 등 기구학적/물리적 속성을 정의합니다.
    -   RViz 시각화(`so101_display.launch.py`) 및 Gazebo 시뮬레이션(`so101_gazebo.launch.py`)을 위한 런치 파일을 제공합니다.

-   **`lerobot_controller`**:
    -   `ros2_control` 프레임워크를 사용하여 로봇의 관절을 제어합니다.
    -   `so101_controllers.yaml` 설정 파일은 팔과 그리퍼를 위한 `JointTrajectoryController`를 정의합니다.
    -   `so101_controller.launch.py` 런치 파일은 컨트롤러를 활성화하는 스포너(spawner) 노드를 실행합니다.

-   **`lerobot_moveit`**:
    -   ROS 2의 표준 모션 플래닝 프레임워크인 MoveIt 2 설정을 포함합니다.
    -   SRDF(`so101.srdf`) 파일은 로봇의 의미론적 정보(플래닝 그룹 등)를 정의하며, 다양한 YAML 파일들이 운동학, 컨트롤러, 관절 제한 등을 설정합니다.
    -   `so101_moveit.launch.py`를 통해 MoveIt의 핵심 노드인 `move_group`을 실행하여 복잡한 모션 플래닝을 가능하게 합니다.

### 2. `lerobot-ros` (파이썬 패키지)

`pip`으로 설치되는 이 파이썬 패키지는 `LeRobot` 프레임워크와 ROS 2 시스템 간의 브릿지 역할을 수행합니다.

-   **`lerobot_ros/robots`**:
    -   `ros.py`의 `ROS2Robot` 클래스는 `LeRobot`의 표준 `Robot` 인터페이스를 상속받아 구현합니다.
    -   `ros_interface.py`는 ROS 2의 토픽, 서비스, 액션 통신을 직접 처리하여 로봇에 명령을 보내고(`send_action`), 센서 데이터를 수신(`get_observation`)합니다.

-   **`lerobot_ros/teleoperators`**:
    -   로봇을 원격으로 조종하기 위한 다양한 입력 방식을 제공합니다.
    -   `gamepad_6dof.py`: 6-DOF(자유도) 게임패드를 사용하여 로봇의 엔드 이펙터를 직관적으로 제어합니다.
    -   `keyboard_joint.py`: 키보드를 사용하여 각 관절을 개별적으로 정밀하게 제어합니다.

-   **`scripts/`**:
    -   `LeRobot` 프레임워크의 핵심 유틸리티를 실행하는 스크립트입니다.
    -   `teleoperate.py`: 로봇을 실시간으로 원격 조종합니다.
    -   `record.py`: 원격 조종을 통해 로봇 시연 데이터를 `Hugging Face Hub` 또는 로컬에 수집하고 저장합니다.
    -   `replay.py`: 저장된 데이터나 훈련된 정책을 로봇에서 재현하여 테스트합니다.

---

## 핵심 기능

-   **고품질 시뮬레이션**: Gazebo Fortress를 사용하여 SO-101 로봇 팔의 사실적인 시뮬레이션 환경을 제공합니다.
-   **다중 제어 모드**: `ros2_control`과 `MoveIt 2`를 통해 다음과 같은 다양한 제어 방식을 지원합니다.
    -   **관절 위치/궤적 제어 (`Joint Position/Trajectory Control`)**: 각 관절의 목표 각도를 직접 지정합니다.
    -   **데카르트 속도 제어 (`Cartesian Velocity Control`)**: 엔드 이펙터의 선속도와 각속도를 기반으로 로봇을 제어합니다.
-   **고급 모션 플래닝**: MoveIt 2와의 통합으로 장애물 회피와 같은 복잡한 경로 계획이 가능합니다.
-   **직관적인 원격 조종**: 게임패드나 키보드를 사용하여 누구나 쉽게 로봇을 조종하고 데이터를 수집할 수 있습니다.
-   **완벽한 LeRobot 통합**: `record`, `replay` 스크립트를 통해 데이터 수집부터 정책 훈련, 배포까지 이어지는 `LeRobot`의 머신러닝 워크플로우를 ROS 2 기반 로봇에 원활하게 적용할 수 있습니다.

---

## 설치 및 실행 방법

프로젝트의 `guide.md` 파일에 상세한 설치 및 실행 가이드가 포함되어 있으며, 주요 단계는 다음과 같습니다.

1.  **ROS 2 의존성 설치**: `apt`를 사용하여 `ros-humble-ros-gz-sim`, `ros-humble-moveit` 등 필수 ROS 2 패키지를 설치합니다.
2.  **파이썬 의존성 설치**: `lerobot` 및 `lerobot-ros` 리포지토리에서 각각 `pip install -e .`를 실행하여 파이썬 패키지를 설치합니다.
3.  **ROS 2 워크스페이스 빌드**: `lerobot_ws` 디렉토리에서 `colcon build` 명령어를 실행하여 ROS 2 패키지를 컴파일합니다.
4.  **시스템 실행**: 3개의 개별 터미널을 열고, 각각 아래의 명령어를 실행하여 전체 시스템(시뮬레이션, 컨트롤러, 모션 플래닝)을 시작합니다.
    ```bash
    # 터미널 1: Gazebo 시뮬레이션 시작
    ros2 launch lerobot_description so101_gazebo.launch.py

    # 터미널 2: ROS 2 컨트롤러 시작
    ros2 launch lerobot_controller so101_controller.launch.py

    # 터미널 3: MoveIt 2 시작
    ros2 launch lerobot_moveit so101_moveit.launch.py
    ```
5.  **LeRobot 스크립트 실행**: 네 번째 터미널에서 `teleoperate.py`, `record.py` 등의 스크립트를 실행하여 로봇을 제어하고 데이터를 수집합니다.