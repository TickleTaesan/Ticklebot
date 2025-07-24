# ROS 코드와 AI 모델 연결 구조 분석

이 문서는 Nomad 프로젝트에서 ROS 코드와 AI 모델이 어떻게 연결되어 있는지에 대한 상세한 분석입니다.

## 목차
1. [전체 아키텍처 개요](#전체-아키텍처-개요)
2. [핵심 연결 지점들](#핵심-연결-지점들)
3. [주요 ROS 노드들](#주요-ros-노드들)
4. [AI 모델 종류](#ai-모델-종류)
5. [데이터 흐름](#데이터-흐름)
6. [핵심 파일 분석](#핵심-파일-분석)

## 전체 아키텍처 개요

```
[카메라] → [ROS Image Topic] → [AI 모델] → [Waypoint Topic] → [PD Controller] → [로봇 제어]
```

Nomad 프로젝트는 RGB 카메라 데이터를 기반으로 한 자율주행 시스템으로, 다음과 같은 파이프라인으로 구성됩니다:

1. **센서 데이터 수집**: USB 카메라에서 실시간 RGB 이미지 수집
2. **AI 모델 추론**: 사전 훈련된 시각적 네비게이션 모델로 waypoint 예측
3. **로봇 제어**: 예측된 waypoint를 바탕으로 로봇의 선속도/각속도 계산
4. **실행**: 계산된 속도 명령으로 로봇 이동

## 핵심 연결 지점들

### A. 센서 데이터 수집 (ROS → AI)

#### 카메라 설정
- **Launch 파일**: `deployment/src/vint_locobot.launch`
- **카메라 노드**: `usb_cam` 패키지 사용
- **설정 파일**: `deployment/config/camera_front.yaml`

```xml
<!-- vint_locobot.launch -->
<node name="usb_cam" pkg="usb_cam" type="usb_cam_node" output="screen">
    <rosparam file="../config/camera_front.yaml" command="load" />
</node>
```

#### 이미지 토픽 처리
- **토픽명**: `/usb_cam/image_raw`
- **메시지 타입**: `sensor_msgs/Image`
- **처리 함수**: `navigate.py`의 `callback_obs()`

```python
# navigate.py의 핵심 부분
def callback_obs(msg):
    obs_img = msg_to_pil(msg)  # ROS 메시지를 PIL 이미지로 변환
    if context_size is not None:
        if len(context_queue) < context_size + 1:
            context_queue.append(obs_img)  # 컨텍스트 큐에 저장
```

### B. AI 모델 추론

#### 모델 로딩
- **로딩 함수**: `utils.py`의 `load_model()`
- **지원 모델**: GNM, ViNT, NoMaD
- **가중치 경로**: `deployment/model_weights/`

```python
# utils.py에서 모델 로딩
def load_model(model_path: str, config: dict, device: torch.device):
    model_type = config["model_type"]
    
    if model_type == "gnm":
        model = GNM(...)
    elif model_type == "vint":
        model = ViNT(...)
    elif model_type == "nomad":
        model = NoMaD(...)
    
    checkpoint = torch.load(model_path, map_location=device)
    model.load_state_dict(checkpoint)
    return model
```

#### 추론 과정
- **입력**: 현재 관찰 이미지 + 목표 이미지
- **출력**: Waypoint 좌표 (x, y) 또는 (x, y, heading_x, heading_y)

```python
# navigate.py에서 모델 추론
if model_params["model_type"] == "nomad":
    # NoMaD 모델 추론 (Diffusion 기반)
    obs_images = transform_images(context_queue, model_params["image_size"])
    # ... diffusion 과정 ...
    naction = to_numpy(get_action(naction))
    chosen_waypoint = naction[0]
else:
    # ViNT/GNM 모델 추론
    distances, waypoints = model(batch_obs_imgs, batch_goal_data)
    chosen_waypoint = waypoints[min_dist_idx][args.waypoint]
```

### C. 제어 명령 전송 (AI → ROS)

#### Waypoint 발행
- **토픽명**: `/waypoint`
- **메시지 타입**: `std_msgs/Float32MultiArray`
- **데이터**: [x, y] 또는 [x, y, heading_x, heading_y]

```python
# navigate.py에서 waypoint 발행
waypoint_msg = Float32MultiArray()
waypoint_msg.data = chosen_waypoint
waypoint_pub.publish(waypoint_msg)
```

#### PD Controller
- **파일**: `deployment/src/pd_controller.py`
- **기능**: Waypoint를 받아 로봇 속도 계산
- **출력 토픽**: 로봇별 속도 제어 토픽

```python
# pd_controller.py에서 속도 계산
def pd_controller(waypoint: np.ndarray) -> Tuple[float]:
    dx, dy = waypoint[:2]
    v = dx / DT  # 선속도
    w = np.arctan(dy/dx) / DT  # 각속도
    return v, w
```

## 주요 ROS 노드들

### 1. navigate.py (메인 AI 추론 노드)
- **기능**: 카메라 이미지 구독, AI 모델 추론, waypoint 발행
- **입력 토픽**: `/usb_cam/image_raw`
- **출력 토픽**: `/waypoint`, `/sampled_actions`
- **설정**: `deployment/config/models.yaml`

### 2. pd_controller.py (로봇 제어 노드)
- **기능**: Waypoint 구독, PD 제어기로 속도 계산, 로봇 제어
- **입력 토픽**: `/waypoint`, `/topoplan/reached_goal`
- **출력 토픽**: 로봇 속도 토픽 (설정에 따라 다름)
- **설정**: `deployment/config/robot.yaml`

### 3. joy_teleop.py (수동 조작 노드)
- **기능**: 조이스틱 입력 처리, 수동 제어 모드 지원
- **입력 토픽**: `/joy`
- **출력 토픽**: 로봇 수동 제어 토픽

### 4. explore.py (탐색 모드 노드)
- **기능**: NoMaD 모델을 사용한 자율 탐색
- **특징**: 목표 없이 환경을 탐색하며 이동

## AI 모델 종류

### 1. GNM (General Navigation Model)
- **특징**: 기본적인 시각적 네비게이션 모델
- **아키텍처**: CNN 기반 인코더 + MLP 디코더
- **출력**: 거리 예측 + waypoint 좌표

### 2. ViNT (Visual Navigation Transformer)
- **특징**: Transformer 기반 시각적 네비게이션 모델
- **아키텍처**: EfficientNet 인코더 + Multi-Head Attention
- **장점**: 긴 시퀀스 처리, 임베디먼트 불변성

### 3. NoMaD (Goal Masked Diffusion Policies)
- **특징**: Diffusion 기반 탐색 및 네비게이션 모델
- **아키텍처**: Vision Encoder + Conditional UNet1D
- **장점**: 탐색과 네비게이션 모두 가능, 다중 액션 샘플링

## 데이터 흐름

```
1. 카메라 → /usb_cam/image_raw
   ↓
2. navigate.py → 이미지 처리 → AI 모델 추론
   ↓
3. navigate.py → /waypoint 토픽 발행
   ↓
4. pd_controller.py → waypoint 수신 → 속도 계산
   ↓
5. pd_controller.py → 로봇 속도 토픽 발행
   ↓
6. 로봇 → 실제 이동
```

## 핵심 파일 분석

### 설정 파일들
- **`deployment/config/models.yaml`**: AI 모델 설정
- **`deployment/config/robot.yaml`**: 로봇 하드웨어 설정
- **`deployment/config/camera_front.yaml`**: 카메라 설정
- **`deployment/config/joystick.yaml`**: 조이스틱 설정

### 핵심 Python 파일들
- **`deployment/src/navigate.py`**: 메인 네비게이션 로직
- **`deployment/src/pd_controller.py`**: 로봇 제어 로직
- **`deployment/src/utils.py`**: 모델 로딩 및 유틸리티 함수
- **`deployment/src/topic_names.py`**: ROS 토픽명 정의

### AI 모델 파일들
- **`train/vint_train/models/nomad/nomad.py`**: NoMaD 모델 정의
- **`train/vint_train/models/vint/vint.py`**: ViNT 모델 정의
- **`train/vint_train/models/gnm/gnm.py`**: GNM 모델 정의

## 실행 방법

### 1. 네비게이션 모드
```bash
cd deployment/src/
./navigate.sh "--model nomad --dir topomap"
```

### 2. 탐색 모드
```bash
cd deployment/src/
./explore.sh "--model nomad"
```

### 3. 토폴로지 맵 생성
```bash
cd deployment/src/
./create_topomap.sh topomap_name bag_filename
```

## 결론

Nomad 프로젝트는 ROS의 실시간 센서 데이터 처리 능력과 AI 모델의 고급 추론 능력을 효과적으로 결합한 시스템입니다. 특히 다음과 같은 특징을 가집니다:

1. **모듈화된 설계**: 각 기능이 독립적인 ROS 노드로 구현
2. **유연한 모델 지원**: GNM, ViNT, NoMaD 등 다양한 AI 모델 지원
3. **실시간 처리**: ROS의 토픽 기반 통신으로 실시간 데이터 처리
4. **확장 가능성**: 다른 로봇 플랫폼으로 쉽게 확장 가능

이러한 구조를 통해 연구자들은 다양한 시각적 네비게이션 모델을 실제 로봇에서 테스트하고 비교할 수 있습니다. 