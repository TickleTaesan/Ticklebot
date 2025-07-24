# ROS2 Nomad 테스트 가이드 (실제 로봇 없이)

## 🎯 개요

실제 로봇 하드웨어가 없어도 ROS2 Nomad 패키지를 충분히 테스트하고 검증할 수 있습니다. 이 가이드는 다양한 테스트 방법을 제공합니다.

## 📋 테스트 방법들

### 1. **Gazebo 시뮬레이션** 🎮

가장 현실적인 테스트 환경을 제공합니다.

#### 설정
```bash
# 시뮬레이션 환경 설정
./test_simulation_setup.sh

# 패키지 빌드
./build_ros2.sh

# 워크스페이스 소싱
source install/setup.bash
```

#### 실행
```bash
# 기본 시뮬레이션 실행
ros2 launch nomad_ros2 simulation_launch.py

# 네비게이션 모드
ros2 launch nomad_ros2 simulation_launch.py mode:=navigate model:=nomad

# 탐색 모드
ros2 launch nomad_ros2 simulation_launch.py mode:=explore model:=nomad
```

#### 시뮬레이션 환경
- **TurtleBot3 Burger**: 실제 로봇과 유사한 물리 모델
- **간단한 방 환경**: 장애물과 벽이 있는 테스트 공간
- **카메라 시뮬레이션**: RGB 카메라 이미지 제공
- **물리 엔진**: 실제 로봇 움직임 시뮬레이션

### 2. **Mock 데이터 테스트** 🤖

실제 센서 데이터를 시뮬레이션합니다.

#### 실행
```bash
# Mock 데이터 테스트 실행
python3 test/test_with_mock_data.py
```

#### 제공되는 Mock 노드들
- **MockCameraNode**: 테스트 이미지 생성 및 발행
- **MockJoystickNode**: 조이스틱 입력 시뮬레이션
- **MockRobotNode**: 로봇 움직임 시뮬레이션
- **TestMonitorNode**: 데이터 수집 및 분석

#### 테스트 시나리오
1. **정지 상태**: 5초 대기
2. **전진**: 3초간 전진 명령
3. **회전**: 2초간 우회전 명령
4. **정지**: 모든 명령 중단

### 3. **단위 테스트** 🧪

개별 함수와 노드의 기능을 검증합니다.

#### 실행
```bash
# 모든 테스트 실행
./run_tests.sh

# 개별 테스트 실행
cd test
python3 -m pytest test_nomad_nodes.py -v
```

#### 테스트 범위
- **PD Controller**: 각도 클리핑, 제어 로직
- **Joy Teleop**: 조이스틱 입력 처리
- **Utility Functions**: 이미지 변환, QoS 설정
- **Node Integration**: 노드 생성 및 초기화
- **Topic Communication**: 메시지 송수신

### 4. **통합 테스트** 🔗

여러 노드 간의 상호작용을 테스트합니다.

#### 실행
```bash
# 통합 테스트 실행
python3 test/test_integration.py
```

#### 테스트 항목
- **노드 간 통신**: 토픽 송수신 확인
- **데이터 흐름**: 이미지 → AI 모델 → 웨이포인트 → 제어
- **에러 처리**: 예외 상황 대응
- **성능 측정**: 처리 시간 및 메모리 사용량

## 🛠️ 테스트 도구들

### 1. **RViz2 시각화** 👁️
```bash
# RViz2 실행
ros2 run rviz2 rviz2

# 또는 시뮬레이션과 함께
ros2 launch nomad_ros2 simulation_launch.py
```

**표시 가능한 정보:**
- 로봇 모델 및 TF 프레임
- 카메라 이미지
- 웨이포인트 경로
- 센서 데이터

### 2. **ROS2 명령어 도구** 🛠️

#### 토픽 모니터링
```bash
# 모든 토픽 확인
ros2 topic list

# 특정 토픽 모니터링
ros2 topic echo /waypoint
ros2 topic echo /cmd_vel
ros2 topic echo /usb_cam/image_raw

# 토픽 정보 확인
ros2 topic info /waypoint
ros2 topic hz /usb_cam/image_raw
```

#### 노드 모니터링
```bash
# 실행 중인 노드 확인
ros2 node list

# 노드 정보 확인
ros2 node info /navigate_node

# 노드 그래프 시각화
ros2 node graph
```

#### 파라미터 관리
```bash
# 파라미터 목록 확인
ros2 param list

# 파라미터 값 확인
ros2 param get /navigate_node model

# 파라미터 설정
ros2 param set /navigate_node model nomad
```

### 3. **ros2bag 데이터 기록** 📹
```bash
# 데이터 기록
ros2 bag record /waypoint /cmd_vel /usb_cam/image_raw

# 데이터 재생
ros2 bag play <bag_file>
```

## 📊 성능 테스트

### 1. **처리 시간 측정**
```bash
# 토픽 주파수 확인
ros2 topic hz /usb_cam/image_raw
ros2 topic hz /waypoint
ros2 topic hz /cmd_vel
```

### 2. **메모리 사용량 모니터링**
```bash
# 노드별 메모리 사용량
ros2 node info /navigate_node
```

### 3. **CPU 사용량 확인**
```bash
# 시스템 리소스 모니터링
htop
top
```

## 🐛 디버깅 방법

### 1. **로그 레벨 설정**
```bash
# 로그 레벨 설정
ros2 run nomad_ros2 navigate_node --ros-args --log-level DEBUG
```

### 2. **콜백 함수 디버깅**
```python
# 노드에 디버그 로그 추가
self.get_logger().debug(f"Received waypoint: {waypoint}")
```

### 3. **예외 처리**
```python
try:
    # 위험한 코드
    result = some_function()
except Exception as e:
    self.get_logger().error(f"Error occurred: {e}")
```

## 📈 테스트 결과 분석

### 1. **성공 지표**
- ✅ 모든 노드가 정상적으로 시작됨
- ✅ 토픽 간 메시지 송수신 확인
- ✅ 이미지 처리 시간 < 100ms
- ✅ 웨이포인트 생성 주기 일정
- ✅ 제어 명령이 물리적으로 합리적

### 2. **실패 시나리오**
- ❌ 노드 시작 실패
- ❌ 토픽 연결 실패
- ❌ 메모리 누수
- ❌ 처리 시간 초과
- ❌ 제어 명령 이상

### 3. **성능 기준**
- **이미지 처리**: < 100ms
- **웨이포인트 생성**: < 500ms
- **제어 루프**: 10Hz 이상
- **메모리 사용량**: < 1GB
- **CPU 사용량**: < 50%

## 🚀 실제 로봇 테스트 준비

시뮬레이션 테스트가 성공하면 실제 로봇에서 테스트할 준비가 완료됩니다.

### 체크리스트
- [ ] 모든 단위 테스트 통과
- [ ] Mock 데이터 테스트 성공
- [ ] 시뮬레이션에서 정상 동작 확인
- [ ] 성능 기준 충족
- [ ] 에러 처리 검증 완료
- [ ] 문서화 완료

## 📝 테스트 보고서 템플릿

```markdown
# 테스트 보고서

## 테스트 환경
- OS: Ubuntu 22.04
- ROS2: Humble
- Python: 3.10
- GPU: NVIDIA RTX 3080 (선택사항)

## 테스트 결과
- [ ] 단위 테스트: PASS/FAIL
- [ ] Mock 데이터 테스트: PASS/FAIL
- [ ] 시뮬레이션 테스트: PASS/FAIL
- [ ] 성능 테스트: PASS/FAIL

## 발견된 문제점
1. 문제 1
2. 문제 2

## 해결 방안
1. 해결책 1
2. 해결책 2

## 결론
시뮬레이션 테스트 결과, 실제 로봇 테스트 준비 완료/미완료
```

## 🎯 결론

실제 로봇이 없어도 위의 테스트 방법들을 통해 ROS2 Nomad 패키지의 대부분을 검증할 수 있습니다. 시뮬레이션과 Mock 데이터 테스트가 성공하면 실제 로봇에서도 안정적으로 동작할 가능성이 높습니다. 