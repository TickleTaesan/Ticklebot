## SO-101 시뮬레이션/컨트롤/무브잇 실행 가이드 (WSL & 네이티브 Ubuntu)

### 1) 환경 개요
- 이 가이드는 두 환경을 모두 지원합니다.
  - WSL Ubuntu: GUI(OpenGL) 이슈가 잦으므로 Gazebo를 headless로 권장
  - 네이티브 Ubuntu 데스크탑: 가장 안정적, GUI 권장

### 2) 필수 ROS 2 패키지 설치 (apt)
- 터미널에서 아래를 실행 (네이티브 Ubuntu 또는 WSL 동일)
```bash
sudo apt update
sudo apt install -y \
  ros-humble-ros-gz-sim \
  ros-humble-ros-gz-bridge \
  ros-humble-gz-ros2-control \
  ros-humble-ros2-controllers \
  ros-humble-joint-state-publisher-gui \
  ros-humble-robot-state-publisher \
  ros-humble-xacro \
  ros-humble-moveit \
  ros-humble-moveit-configs-utils
```

### 3) Python 패키지 설치 위치와 명령 (pip install -e .)
- LeRobot 라이브러리(파이썬)와 ROS 래퍼(파이썬)는 `pip install -e .`로 설치합니다.
- 각각 해당 디렉토리에서 실행하세요.

1) LeRobot (필수)
```bash
cd /home/kowook/robot_project/src/ros2_robot/lerobot
pip install -e .
```

2) lerobot-ros (권장)
```bash
cd /home/kowook/robot_project/src/ros2_robot/lerobot-ros
pip install -e .
```

※ 주의
- ROS 2 워크스페이스(`lerobot_ws`)는 `pip install` 대상이 아닙니다. 이곳은 `colcon build`로 빌드합니다.
- WSL에서 ROS 빌드/런은 시스템 파이썬(ROS)과 콘다 파이썬이 섞일 수 있습니다. 충돌 시 빌드/런 터미널에서는 `conda deactivate`로 콘다 비활성화를 고려하세요. (필요 시 `pip install catkin_pkg empy rospkg rosdistro` 추가 설치)

### 4) ROS 2 워크스페이스 빌드 (colcon)
```bash
source /opt/ros/humble/setup.bash
cd /home/kowook/robot_project/src/ros2_robot/lerobot_ws
rosdep update
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
```

### 5) 실행 순서 (3개 터미널)
아래는 어떤 디렉토리에서든 실행 가능하지만, 예시로 워크스페이스 루트에서 실행합니다. 각 터미널마다 두 줄의 `source`를 먼저 실행하세요.

공통 (각 터미널 시작 시)
```bash
cd /home/kowook/robot_project/src/ros2_robot/lerobot_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
```

- 터미널 1: Gazebo 시뮬레이션
```bash
ros2 launch lerobot_description so101_gazebo.launch.py
```

- 터미널 2: ros2_control 컨트롤러 스포너
```bash
ros2 launch lerobot_controller so101_controller.launch.py
```

- 터미널 3: MoveIt 2
```bash
ros2 launch lerobot_moveit so101_moveit.launch.py
```

### 6) WSL에서 Gazebo GUI 크래시 시 대처
WSL에서는 OpenGL/OGRE 문제로 GUI가 종료될 수 있습니다. 아래 중 하나를 사용하세요.

- 권장(Headless 서버 모드): `so101_gazebo.launch.py` 내부의 `gz_args`에 `-s` 추가
  - 파일: `/home/kowook/robot_project/src/ros2_robot/lerobot_ws/src/lerobot_description/launch/so101_gazebo.launch.py`
  - 변경 예시
```12:14:lerobot_ws/src/lerobot_description/launch/so101_gazebo.launch.py
gazebo = IncludeLaunchDescription(
            PythonLaunchDescriptionSource([os.path.join(
                get_package_share_directory("ros_gz_sim"), "launch"), "/gz_sim.launch.py"]),
            launch_arguments=[
                ("gz_args", [" -v 4 -s -r empty.sdf "])
            ]
         )
```
  - 빌드 재실행 불필요(`--symlink-install`), 다시 터미널 1~3 실행

- 대안(느릴 수 있음): 소프트웨어 렌더러 강제
```bash
export LIBGL_ALWAYS_SOFTWARE=1
ros2 launch lerobot_description so101_gazebo.launch.py
```

### 7) 동작 확인
- 컨트롤러 확인
```bash
ros2 control list_controllers
```

- 상태 토픽 확인
```bash
ros2 topic echo /joint_states
```

### 8) 네이티브 Ubuntu에서 실행(권장 시나리오)
네이티브 Ubuntu 데스크탑(GPU 드라이버 설치 후)에서는 GUI가 안정적으로 동작합니다. 절차는 동일합니다.
1) 2) apt 설치 → 3) pip 설치 → 4) colcon 빌드 → 5) 3개 터미널 실행

### 9) 자주 나오는 오류 & 해결
- `PackageNotFoundError: 'ros_gz_sim' not found`
  - 2) 절의 apt 패키지 설치 누락. 설치 후 다시 실행
- `ModuleNotFoundError: No module named 'catkin_pkg'` 등 ament 파서 오류
  - 빌드 터미널에서 `pip install catkin_pkg empy rospkg rosdistro`
- RViz2 `Error document empty`
  - 보통 로봇 디스크립션 파라미터 미주입. 터미널 1(시뮬)과 2(컨트롤러)가 정상 가동 후 3을 실행하세요.
- Gazebo GUI가 WSL에서 크래시
  - 6) 절의 headless 모드(-s) 또는 소프트웨어 렌더러 사용

---

## SO-100 하드웨어 + 게임패드 제어 (Gazebo 없이)

아래 절차는 Feetech STS3215 서보 7개를 Waveshare Bus Servo Adapter로 연결한 SO-100/101 계열 팔을, Gazebo 없이 실제 하드웨어로 MoveIt Servo + 게임패드(`gamepad_6dof`)로 제어하는 방법입니다. 본 리포에 반영된 최소 수정 사항을 전제로 합니다.

### A) 사전 준비
- 필수 패키지 설치(이미 설치되어 있다면 생략 가능)
```bash
sudo apt update
sudo apt install -y \
  ros-humble-ros2-controllers \
  ros-humble-moveit \
  ros-humble-moveit-configs-utils \
  ros-humble-feetech-ros2-driver
```

- 시리얼 권한(최초 1회):
```bash
sudo usermod -aG dialout $USER
# 로그아웃/로그인 후 적용
```

- 시리얼 포트 확인(어댑터 경로):
```bash
ls -l /dev/serial/by-id
# 예) /dev/serial/by-id/usb-1a86_USB2.0-Ser_-if00-port0 -> ../../ttyUSB0
```

### B) 코드 변경 요약(이미 반영됨)
- `lerobot_description/urdf/so101_ros2_control.xacro`: `hardware_plugin` 인자 추가 → 하드웨어 플러그인 선택 가능
- `lerobot_controller/launch/so101_controller.launch.py`: xacro에 `hardware_plugin` 전달
- `lerobot_moveit/config/servo.yaml`, `lerobot_moveit/launch/so101_servo.launch.py`: MoveIt Servo 구성 추가

### C) 워크스페이스 빌드
```bash
source /opt/ros/humble/setup.bash
cd /home/kowook/robot_project/ros2_robot/lerobot_ws
rosdep update
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
source install/setup.bash
```

### D) 하드웨어 컨트롤러 기동(ros2_control)
- Feetech 하드웨어 플러그인 타입: `feetech_ros2_driver/FeetechHardwareInterface`
- 기본 통신설정으로 먼저 시도:
```bash
ros2 launch lerobot_controller so101_controller.launch.py \
  is_sim:=False \
  hardware_plugin:=feetech_ros2_driver/FeetechHardwareInterface
```

- 통신 파라미터가 필요할 경우(포트/보드레이트/ID):
  - `lerobot_ws/src/lerobot_description/urdf/so101_ros2_control.xacro`의 `<ros2_control> <hardware>` 블록 안에 다음을 추가하여 재시도하세요(환경에 맞게 값 수정).
  ```xml
  <param name="port">/dev/serial/by-id/usb-...-port0</param>
  <param name="baudrate">1000000</param>
  <param name="ids">1,2,3,4,5,6</param>
  ```

- 상태 확인:
```bash
ros2 control list_controllers
ros2 topic echo /joint_states -n 1
```
  - 기대: `joint_state_broadcaster`, `arm_controller`, `gripper_controller`가 active, `/joint_states` 값 수신

### E) MoveIt 2 실행
```bash
ros2 launch lerobot_moveit so101_moveit.launch.py is_sim:=False
```

### F) MoveIt Servo 실행(엔드이펙터 속도 제어)
```bash
ros2 launch lerobot_moveit so101_servo.launch.py
```
- 인터페이스 확인:
```bash
ros2 topic list | grep servo_node
ros2 service list | grep servo_node
```
  - 기대 토픽/서비스: `/servo_node/delta_twist_cmds`, `/servo_node/pause_servo`

### G) 게임패드 텔레오퍼레이션 실행
```bash
python /home/kowook/robot_project/ros2_robot/lerobot-ros/scripts/teleoperate.py \
  --robot.type=so101_ros \
  --robot.action_type=cartesian_velocity \
  --teleop.type=gamepad_6dof \
  --display_data=true
```
- 메모:
  - `gamepad_6dof`는 MoveIt Servo가 켜져 있어야 동작합니다.
  - 모터 ID는 URDF/컨트롤러 기대값과 일치해야 합니다(팔: 1~5, 그리퍼: 6). 7번째 모터는 기본 URDF에 포함되어 있지 않습니다.

### H) 트러블슈팅
- `/joint_states` 없음 → 포트/보드레이트/ID 불일치, 권한 미부여(dialout), 케이블/전원 확인
- `Pause service not available` → F단계(Servo) 먼저 실행 필요
- 컨트롤러 inactive → `so101_ros2_control.xacro`에 하드웨어 `<param>` 추가 후 재실행
- 게임패드 미인식 → OS에서 조이스틱 인식 확인 후 재시도

### I) 안전 주의
- 초기 구동 시 장애물 없는 환경에서 저속으로 검증 후 사용하세요. MoveIt Servo의 속도 스케일은 `lerobot_moveit/config/servo.yaml`에서 조정 가능합니다(`linear_scale`, `rotational_scale`).
