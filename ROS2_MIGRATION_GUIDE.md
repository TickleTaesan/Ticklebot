# ROS2 Humble 마이그레이션 가이드

이 문서는 Nomad 프로젝트를 ROS1 Noetic에서 ROS2 Humble로 마이그레이션하는 과정을 설명합니다.

## 목차
1. [변경 사항 개요](#변경-사항-개요)
2. [새로운 패키지 구조](#새로운-패키지-구조)
3. [주요 변경점](#주요-변경점)
4. [빌드 및 실행](#빌드-및-실행)
5. [남은 작업](#남은-작업)

## 변경 사항 개요

### ROS1 → ROS2 주요 변경점
- **노드 구조**: `rospy.Node` → `rclpy.node.Node`
- **Launch 파일**: XML → Python
- **QoS 설정**: 기본 QoS → 명시적 QoS 설정
- **파라미터**: `rospy.get_param()` → `self.get_parameter()`
- **빌드 시스템**: catkin → colcon

### 새로운 패키지 구조
```
nomad_ros2/
├── package.xml              # ROS2 패키지 메타데이터
├── CMakeLists.txt           # CMake 빌드 설정
├── setup.py                 # Python 패키지 설정
├── resource/
│   └── nomad_ros2           # 패키지 리소스
├── nomad_ros2/              # Python 패키지
│   ├── __init__.py
│   ├── navigate_node.py     # 메인 네비게이션 노드
│   ├── pd_controller_node.py # PD 제어기 노드
│   ├── joy_teleop_node.py   # 조이스틱 제어 노드
│   ├── explore_node.py      # 탐색 노드
│   ├── create_topomap_node.py # 토폴로지 맵 생성 노드
│   ├── topic_names.py       # 토픽명 정의
│   └── utils.py             # 유틸리티 함수
├── launch/
│   └── nomad_launch.py      # ROS2 Python Launch 파일
├── config/                  # 설정 파일들
│   ├── robot.yaml
│   ├── models.yaml
│   ├── camera_front.yaml
│   └── joystick.yaml
├── build_ros2.sh            # 빌드 스크립트
└── run_nomad_ros2.sh        # 실행 스크립트
```

## 주요 변경점

### 1. 노드 구조 변경

#### ROS1 (기존)
```python
import rospy
from sensor_msgs.msg import Image

def callback_obs(msg):
    # 처리 로직

rospy.init_node("navigate")
rospy.Subscriber("/usb_cam/image_raw", Image, callback_obs)
rospy.spin()
```

#### ROS2 (새로운)
```python
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image

class NavigateNode(Node):
    def __init__(self):
        super().__init__('navigate_node')
        self.image_sub = self.create_subscription(
            Image, '/usb_cam/image_raw', self.callback_obs, 10)
    
    def callback_obs(self, msg):
        # 처리 로직

def main():
    rclpy.init()
    node = NavigateNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()
```

### 2. Launch 파일 변경

#### ROS1 (기존)
```xml
<launch>
    <node name="usb_cam" pkg="usb_cam" type="usb_cam_node" output="screen">
        <rosparam file="../config/camera_front.yaml" command="load" />
    </node>
</launch>
```

#### ROS2 (새로운)
```python
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    usb_cam_node = Node(
        package='usb_cam',
        executable='usb_cam_node_exe',
        name='usb_cam',
        output='screen',
        parameters=[camera_config]
    )
    
    return LaunchDescription([usb_cam_node])
```

### 3. QoS 설정 추가
```python
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy

qos_profile = QoSProfile(
    reliability=ReliabilityPolicy.BEST_EFFORT,
    history=HistoryPolicy.KEEP_LAST,
    depth=1
)

self.image_sub = self.create_subscription(
    Image, IMAGE_TOPIC, self.callback_obs, qos_profile)
```

## 빌드 및 실행

### 1. ROS2 환경 설정
```bash
# ROS2 Humble 설치 (Ubuntu 22.04)
sudo apt update
sudo apt install ros-humble-desktop

# 환경 소스
source /opt/ros/humble/setup.bash
```

### 2. 워크스페이스 설정
```bash
# 워크스페이스 생성
mkdir -p ~/ros2_ws/src
cd ~/ros2_ws/src

# 패키지 복사
cp -r /path/to/nomad_ros2 ./
```

### 3. 빌드
```bash
cd ~/ros2_ws
chmod +x src/nomad_ros2/build_ros2.sh
./src/nomad_ros2/build_ros2.sh
```

### 4. 실행
```bash
# 워크스페이스 소스
source ~/ros2_ws/install/setup.bash

# 실행
chmod +x src/nomad_ros2/run_nomad_ros2.sh
./src/nomad_ros2/run_nomad_ros2.sh nomad topomap -1
```

## 남은 작업

### 1. 추가 노드 변환
- [ ] `pd_controller_node.py` 완성
- [ ] `joy_teleop_node.py` 완성
- [ ] `explore_node.py` 완성
- [ ] `create_topomap_node.py` 완성

### 2. 유틸리티 함수 변환
- [ ] `utils.py` ROS2 호환성 확인
- [ ] `msg_to_pil()` 함수 ROS2 메시지 타입에 맞게 수정

### 3. 설정 파일 경로 수정
- [ ] 상대 경로를 ROS2 패키지 경로로 변경
- [ ] 파라미터 시스템 활용

### 4. 테스트 및 검증
- [ ] 단위 테스트 작성
- [ ] 통합 테스트 수행
- [ ] 성능 비교

### 5. 문서화
- [ ] API 문서 작성
- [ ] 사용자 가이드 업데이트
- [ ] 트러블슈팅 가이드 작성

## 주요 이점

### ROS2의 장점
1. **실시간 성능**: DDS 기반 통신으로 더 나은 실시간 성능
2. **QoS 제어**: 메시지 전송 품질 세밀 제어
3. **보안**: ROS2 Security 기능 활용 가능
4. **멀티 플랫폼**: Windows, macOS, Linux 지원
5. **컴포넌트**: 재사용 가능한 컴포넌트 아키텍처

### 마이그레이션의 이점
1. **향후 호환성**: ROS1은 2025년 EOL 예정
2. **새로운 기능**: ROS2의 최신 기능 활용
3. **커뮤니티 지원**: 활발한 ROS2 커뮤니티
4. **업계 표준**: 자동차, 로봇 업계 표준

## 문제 해결

### 일반적인 문제들
1. **Import 오류**: Python 경로 설정 확인
2. **QoS 불일치**: Publisher/Subscriber QoS 일치 확인
3. **파라미터 오류**: ROS2 파라미터 시스템 사용
4. **빌드 오류**: colcon 빌드 시스템 확인

### 디버깅 팁
```bash
# 노드 상태 확인
ros2 node list
ros2 node info /navigate_node

# 토픽 확인
ros2 topic list
ros2 topic echo /usb_cam/image_raw

# 파라미터 확인
ros2 param list
ros2 param get /navigate_node model
```

## 결론

ROS2 Humble로의 마이그레이션은 Nomad 프로젝트의 장기적인 지속가능성을 위한 중요한 단계입니다. 새로운 아키텍처는 더 나은 성능, 보안, 확장성을 제공하며, 향후 ROS 생태계의 발전에 맞춰 지속적으로 개선될 수 있습니다. 