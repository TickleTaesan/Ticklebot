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