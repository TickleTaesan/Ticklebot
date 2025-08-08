# Teleoprator.py 코드 분석

## 개요
`teleoprator.py`는 로봇 원격 조작(Teleoperation)을 위한 핵심 클래스인 `Teleopoperator`를 정의합니다. 이 클래스는 웹 기반 인터페이스를 통해 로봇의 팔과 베이스를 제어하는 시스템입니다.

## 주요 구성 요소

### 1. 클래스 구조
```python
class Teleopoperator:
    def __init__(self)
    async def reset_Tscam(self)
    async def update_percise_mode(self, percise_mode)
    def update_teleop_mode(self, teleop_mode)
    async def reset_arm(self, lift_distance, joint_bent, far_seeing)
    def get_head_tilt(self, lift_distance)
    def hand_cb(self, camera_matrix, distortion_coefficients, corners, ids)
    def pedal_cb(self, pedal_real_values)
    async def control_cb(self, control_type)
    def error_cb(self, msg)
```

### 2. 주요 상태 변수
- `teleop_mode`: 조작 모드 ("base", "arm", None)
- `percise_mode`: 정밀도 모드 (True/False/"more_percise")
- `lift_distance`: 팔의 높이 거리
- `Tscam`: 카메라-로봇 좌표계 변환 행렬
- `gripper_lock`: 그리퍼 잠금 상태
- `far_seeing`: 원거리 시야 모드

## 콜그래프 (Call Graph)

```mermaid
graph TD
    A[Teleopoperator.__init__] --> B[WebServer 생성]
    A --> C[콜백 함수 등록]
    A --> D[초기 상태 설정]
    
    E[WebServer] --> F[hand_cb]
    E --> G[pedal_cb]
    E --> H[control_cb]
    
    F --> I[reset_Tscam]
    F --> J[update_percise_mode]
    F --> K[update_teleop_mode]
    
    G --> L[reset_arm]
    G --> M[get_head_tilt]
    
    H --> N[control_cb 내부 로직]
    N --> O[reset]
    N --> P[done]
    N --> Q[teleop_mode 변경]
    N --> R[percise_mode 변경]
    N --> S[gripper_lock 설정]
    
    T[astra_teleop.process.get_solve] --> U[ArUco 태그 해석]
    U --> V[좌표계 변환]
    
    W[pytransform3d] --> X[transformations]
    W --> Y[rotations]
    
    Z[asyncio] --> AA[비동기 처리]
```

## 플로우차트 (Flowchart)

### 1. 초기화 플로우
```mermaid
flowchart TD
    A([시작]) --> B[Teleopoperator 생성]
    B --> C[WebServer 초기화]
    C --> D[콜백 함수 등록]
    D --> E[초기 상태 설정]
    E --> F[get_solve 함수 생성]
    F --> G[대기 상태]
    
    G --> H{이벤트 발생?}
    H -->|Yes| I{이벤트 타입}
    H -->|No| G
    I -->|hand| J[hand_cb 호출]
    I -->|pedal| K[pedal_cb 호출]
    I -->|control| L[control_cb 호출]
    J --> G
    K --> G
    L --> G
```

### 2. 핸드 콜백 플로우
```mermaid
flowchart TD
    A([hand_cb 시작]) --> B[ArUco 태그 해석]
    B --> C{태그 감지됨?}
    C -->|No| D[에러 메시지 출력]
    D --> E([종료])
    C -->|Yes| F[좌표계 변환]
    F --> G{teleop_mode 확인}
    G -->|None| E
    G -->|arm| H{Tscam 초기화됨?}
    H -->|No| I[리셋 요청]
    I --> E
    H -->|Yes| J[목표 위치 계산]
    J --> K[로봇 팔 제어]
    K --> L[헤드 제어]
    L --> E
```

### 3. 페달 콜백 플로우
```mermaid
flowchart TD
    A([pedal_cb 시작]) --> B{teleop_mode 확인}
    B -->|arm| C[그리퍼 제어 모드]
    B -->|base| D[베이스 제어 모드]
    
    C --> E[리프트 거리 조정]
    E --> F{리프트 한계 확인}
    F -->|초과| G[경고 메시지]
    F -->|정상| H[그리퍼 위치 계산]
    G --> E
    H --> I{그리퍼 잠금 상태}
    I -->|잠금| J[잠금 해제 대기]
    I -->|해제| K[그리퍼 제어]
    J --> K
    K --> L([종료])
    
    D --> M[선형 속도 계산]
    M --> N[각속도 계산]
    N --> O[베이스 제어]
    O --> L
```

### 4. 컨트롤 콜백 플로우
```mermaid
flowchart TD
    A([control_cb 시작]) --> B{control_type 확인}
    B -->|reset| C[모드 리셋]
    B -->|done| D[완료 이벤트]
    B -->|teleop_mode_*| E[모드 변경]
    B -->|percise_mode_*| F[정밀도 변경]
    B -->|gripper_lock_*| G[그리퍼 잠금]
    
    C --> H[팔 리셋]
    H --> I[상태 초기화]
    I --> J([종료])
    
    D --> J
    
    E --> K[모드별 설정]
    K --> J
    
    F --> L[정밀도 설정]
    L --> J
    
    G --> M[그리퍼 잠금 설정]
    M --> J
```

### 5. 리셋 팔 플로우
```mermaid
flowchart TD
    A([reset_arm 시작]) --> B[목표 포즈 계산]
    B --> C[for 루프: 좌우 팔]
    C --> D[현재 포즈 가져오기]
    D --> E[위치/회전 거리 계산]
    E --> F{목표 도달?}
    F -->|No| G[목표 포즈 발행]
    G --> H[그리퍼 제어]
    H --> I[헤드 제어]
    I --> J[0.1초 대기]
    J --> D
    F -->|Yes| K{모든 팔 완료?}
    K -->|No| C
    K -->|Yes| L([종료])
```

### 6. Tscam 리셋 플로우
```mermaid
flowchart TD
    A([reset_Tscam 시작]) --> B[Tscam 초기화]
    B --> C[while 루프: 태그 대기]
    C --> D{새 태그 결과 확인}
    D -->|대기 중| E[0.1초 대기]
    E --> C
    D -->|완료| F[for 루프: 좌우 팔]
    F --> G[현재 EEF 포즈 가져오기]
    G --> H[Tcamgoal_last 확인]
    H --> I[Tscam 계산]
    I --> J[로그 출력]
    J --> K{모든 팔 완료?}
    K -->|No| F
    K -->|Yes| L([종료])
```

## 주요 기능 설명

### 1. ArUco 태그 기반 위치 추적
- 웹 카메라를 통해 ArUco 태그를 감지
- 태그의 3D 위치를 계산하여 로봇 팔의 목표 위치 결정
- 좌우 손에 대한 개별 추적

### 2. 정밀도 모드
- `percise_mode`: 일반 정밀도 (scale=1.0)
- `more_percise`: 고정밀도 (scale=0.5)
- 모션 증폭을 통해 미세한 움직임 제어

### 3. 그리퍼 제어
- 페달을 통한 그리퍼 개폐 제어
- 그리퍼 잠금 기능으로 안전성 확보
- 좌우 그리퍼 독립 제어

### 4. 베이스 제어
- 페달을 통한 로봇 베이스 이동
- 선형 속도와 각속도 제어
- 전진/후진 시 각속도 방향 자동 조정

### 5. 헤드 제어
- 리프트 거리에 따른 자동 헤드 틸트 조정
- 원거리 시야 모드 지원

## 데이터 플로우

```mermaid
graph LR
    A[웹 카메라] --> B[ArUco 태그 감지]
    B --> C[좌표계 변환]
    C --> D[목표 위치 계산]
    D --> E[로봇 팔 제어]
    
    F[페달 입력] --> G[그리퍼/베이스 제어]
    G --> H[로봇 동작]
    
    I[웹 인터페이스] --> J[모드 변경]
    J --> K[시스템 상태 업데이트]
```

## 에러 처리

1. **태그 미감지**: 카메라 연결 및 태그 가시성 확인 요청
2. **Tscam 미초기화**: 팔 리셋 요청
3. **리프트 한계 초과**: 경고 메시지 출력
4. **연결 실패**: 웹서버 연결 상태 모니터링

## 성능 최적화

1. **비동기 처리**: asyncio를 활용한 비동기 이벤트 처리
2. **로우패스 필터**: 센서 노이즈 제거를 위한 위치 필터링
3. **스레드 안전**: 웹서버와의 안전한 통신
4. **메모리 효율성**: 큐 기반 이미지 처리

이 시스템은 웹 기반의 직관적인 인터페이스를 통해 로봇의 정밀한 원격 조작을 가능하게 하는 고도화된 텔레오퍼레이션 시스템입니다. 