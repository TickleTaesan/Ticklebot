# 듀얼 SO-100 로봇 원격 조종 및 데이터셋 수집 가이드 (ROS2 네임스페이스 기반)

## 📋 목차
1. [환경 설정](#환경-설정)
2. [시뮬레이션/실기 구동](#시뮬레이션실기-구동)
3. [원격 조종(텔레옵)](#원격-조종텔레옵)
4. [데이터셋 녹화](#데이터셋-녹화)
5. [데이터 구조와 스키마](#데이터-구조와-스키마)
6. [문제 해결](#문제-해결)

---

## 🛠️ 환경 설정

### 1) 디렉토리 및 환경 활성화

```bash
# 프로젝트 루트로 이동
cd /Ubuntu-22.04/home/kowook/robot_project/src/dual_ros2_robot

# Python 가상환경 활성화
conda activate lerobot  # 혹은
# source /path/to/venv/bin/activate

# ROS2 환경 변수
source /opt/ros/humble/setup.bash

# ROS2 워크스페이스 빌드/세팅 (최초 1회 빌드 권장)
cd lerobot_ws
colcon build --symlink-install
source install/setup.bash
```

### 2) 하드웨어 확인 (실기)

```bash
# 게임패드 연결 확인
ls /dev/input/js*
# 예: /dev/input/js0

# 포트 권한 (필요 시)
sudo chmod 666 /dev/input/js0
```

---

## 🚀 시뮬레이션/실기 구동

듀얼 제어는 ROS2 네임스페이스(`left_arm`, `right_arm`)를 사용합니다.

### A. 시뮬레이션(Gazebo + ros_gz)

1) Terminal 1 - Gazebo/컨트롤러/브리지
```bash
cd /Ubuntu-22.04/home/kowook/robot_project/src/dual_ros2_robot
source /opt/ros/humble/setup.bash
cd lerobot_ws && source install/setup.bash
cd ../lerobot-ros
ros2 launch lerobot-ros dual_so100_bringup.launch.py
```

2) Terminal 2 - MoveIt Servo(카르테시안 속도 제어 시 필수)
```bash
cd /Ubuntu-22.04/home/kowook/robot_project/src/dual_ros2_robot
source /opt/ros/humble/setup.bash
cd lerobot_ws && source install/setup.bash
ros2 launch lerobot_moveit so101_moveit.launch.py namespace:=left_arm &
ros2 launch lerobot_moveit so101_moveit.launch.py namespace:=right_arm
```

3) Terminal 3 - 텔레옵 또는 레코딩 실행(아래 섹션 참고)

### B. 실제 로봇(ROS2 드라이버가 제공하는 토픽/컨트롤러를 사용)

- 실제 하드웨어 노드가 `left_arm`, `right_arm` 네임스페이스로 `joint_states`, `/arm_controller`, `/gripper_controller` 등을 제공해야 합니다.
- 카르테시안 속도 제어(`cartesian_velocity`)를 사용할 경우 MoveIt Servo를 각 네임스페이스로 기동하세요.

---

## 🎮 원격 조종(텔레옵)

듀얼 게임패드 텔레옵 구성은 다음과 같습니다.

```bash
# Terminal 3 - 텔레옵 실행
cd /Ubuntu-22.04/home/kowook/robot_project/src/dual_ros2_robot
source /opt/ros/humble/setup.bash
cd lerobot_ws && source install/setup.bash
cd ../lerobot-ros
python scripts/teleoperate.py \
  --robot.type=dual_so100_ros \
  --robot.id=dual_robot \
  --teleop.type=dual_gamepad_6dof \
  --teleop.use_gripper=true \
  --teleop.default_mode=both
```

### 제어 모드 단축키
- A: 왼팔 전용(left)
- B: 오른팔 전용(right)
- X: 미러 모드(mirror)
- Y: 양팔 동기(both)
- Start: 기본 모드로 리셋

### 게임패드 맵핑
- 왼쪽 스틱: Linear X/Y
- 오른쪽 스틱: Angular X/Y(roll/pitch)
- LB/RB: Angular Z(yaw)
- LT/RT: Linear Z(up/down)
- Grip 버튼: 그리퍼 열림/닫힘(정규화 0~1)

### 제어 타입 선택
- 기본값은 카르테시안 속도 제어(`--robot.action_type=cartesian_velocity`). MoveIt Servo가 필요합니다.
- 조인트 궤적 제어를 원할 경우:
```bash
# Terminal 3 - 텔레옵(조인트 궤적 제어)
cd /Ubuntu-22.04/home/kowook/robot_project/src/dual_ros2_robot
source /opt/ros/humble/setup.bash
cd lerobot_ws && source install/setup.bash
cd ../lerobot-ros
python scripts/teleoperate.py \
  --robot.type=dual_so100_ros \
  --robot.action_type=joint_trajectory \
  --teleop.type=dual_gamepad_6dof
```

---

## 📹 데이터셋 녹화

### 1) 듀얼 데이터셋 녹화 시작

```bash
# Terminal 1/2: 시뮬레이션 또는 실제 하드웨어 스택을 먼저 구동

# Terminal 3 - 레코딩 실행
cd /Ubuntu-22.04/home/kowook/robot_project/src/dual_ros2_robot
source /opt/ros/humble/setup.bash
cd lerobot_ws && source install/setup.bash
cd ../lerobot-ros
python scripts/record.py \
  --robot.type=dual_so100_ros \
  --robot.id=cloth_folding_robot \
  --teleop.type=dual_gamepad_6dof \
  --teleop.default_mode=mirror \
  --num_episodes=10 \
  --episode_time_s=30 \
  --dataset.repo_id=your_username/cloth_folding_dual_so100 \
  --dataset.local_dir=./datasets \
  --save_videos=true \
  --fps=30
```

### 2) 레코딩 중 제어(시작/종료)
- 시작: `record.py` 실행 즉시 활성화(게임패드 입력 시 기록)
- 에피소드 성공 종료: 게임패드 Y/Triangle
- 에피소드 실패 종료: 게임패드 A/Cross
- 현재 에피소드 재시작: 게임패드 X/Square
- 전체 녹화 종료: 설정한 `--num_episodes` 완료 또는 터미널에서 Ctrl+C

### 3) 녹화 완료 후 확인

```bash
ls -la ./datasets/your_username/cloth_folding_dual_so100/

# 데이터셋 로드 확인
python - << 'PY'
from lerobot.datasets.lerobot_dataset import LeRobotDataset
d = LeRobotDataset('./datasets/your_username/cloth_folding_dual_so100')
print('episodes:', len(d.episode_data_index))
print('frames:', len(d))
print('action_features:', d.action_features)
PY
```

### 4) 리플레이(선택)

```bash
python scripts/replay.py \
  --robot.type=dual_so100_ros \
  --dataset.repo_id=./datasets/your_username/cloth_folding_dual_so100 \
  --local-files-only 1
```

---

## ✅ 요약: 터미널별 실행 순서
- Terminal 1: Gazebo/컨트롤러/브리지 런치(시뮬) 또는 실제 하드웨어 드라이버 기동
- Terminal 2: MoveIt Servo 두 네임스페이스(left_arm/right_arm) 기동(카르테시안 속도 제어 시 필수)
- Terminal 3:
  - 텔레옵 시작: `scripts/teleoperate.py --robot.type=dual_so100_ros --teleop.type=dual_gamepad_6dof`
  - 데이터셋 녹화: `scripts/record.py` 동일 옵션(+에피소드/경로 옵션)으로 실행

---

## 🧱 데이터 구조와 스키마

### 액션 키(action_features)
- 카르테시안 속도 제어(`cartesian_velocity`):
  - `left_linear_x.vel`, `left_linear_y.vel`, `left_linear_z.vel`, `left_angular_x.vel`, `left_angular_y.vel`, `left_angular_z.vel`, `left_gripper.pos`
  - `right_linear_x.vel`, `right_linear_y.vel`, `right_linear_z.vel`, `right_angular_x.vel`, `right_angular_y.vel`, `right_angular_z.vel`, `right_gripper.pos`

- 조인트 제어(`joint_position`/`joint_trajectory`):
  - `left_1.pos`, `left_2.pos`, `left_3.pos`, `left_4.pos`, `left_5.pos`, `left_gripper.pos`
  - `right_1.pos`, `right_2.pos`, `right_3.pos`, `right_4.pos`, `right_5.pos`, `right_gripper.pos`

### 관측(observation) 키
- 조인트 기반:
  - `left_1.pos` ... `left_5.pos`, `left_gripper.pos`
  - `right_1.pos` ... `right_5.pos`, `right_gripper.pos`
- 카메라 사용 시: 각 카메라 키가 추가됨(`config.cameras`에 정의된 이름)

### 그리퍼 정규화
- `gripper.pos`: 0.0(open) ~ 1.0(closed). 실제 값 매핑은 `DualSO100RosConfig`의 `gripper_open_position`/`gripper_close_position`에 의해 선형 변환됩니다.

---

## 🔧 문제 해결

### 공통
```bash
export LEROBOT_LOG_LEVEL=DEBUG
```

**1) 게임패드 인식 불가**
```bash
jstest /dev/input/js0
pip install pygame
sudo chmod 666 /dev/input/js0
```

**2) MoveIt Servo 미기동(속도 제어 멈춤)**
```bash
ros2 launch lerobot_moveit so101_moveit.launch.py namespace:=left_arm
ros2 launch lerobot_moveit so101_moveit.launch.py namespace:=right_arm
```

**3) 토픽/컨트롤러 네임스페이스 불일치**
- 실제 하드웨어 또는 시뮬 노드가 `left_arm`/`right_arm` 네임스페이스로 다음을 제공해야 합니다:
  - `joint_states`, `/arm_controller/joint_trajectory` 또는 `/position_controller/commands`
  - `/gripper_controller/joint_trajectory` 또는 `/gripper_controller/gripper_cmd`

**4) gripper 범위 불일치**
- `DualSO100RosConfig`에서 `gripper_open_position`, `gripper_close_position`을 실제 하드웨어 범위에 맞게 조정하세요.

**5) 디스크/성능 이슈(녹화)**
```bash
df -h
rm -rf /tmp/lerobot_*
```

---

## 📝 참고사항
- 안전 수칙: 로봇 동작 전에 주변 확보, 속도 스케일(민감도) 보수적으로 시작
- 첫 실행 시 보정/홈 동작이 필요한 하드웨어는 제조사 가이드에 따르세요
- 데이터는 즉시 백업 권장, FPS와 해상도는 저장소/성능 상황에 맞게 조정

---

이 문서는 `dual_so100_ros` + `dual_gamepad_6dof` 듀얼 제어 파이프라인을 기준으로 작성되었습니다. 위 절차대로 진행하면 시뮬레이션과 실제 환경에서 동일한 인터페이스로 텔레옵/레코딩/리플레이가 가능합니다.
