# NoMaD ROS1 Demo – README

빠르게 동일 환경에서 재현하고, 약간의 코드/파라미터만 바꿔서 실험할 수 있도록 정리했습니다. 아래 순서대로 실행하면, 이미지 재생 → 모델 추론(웨이포인트 샘플) → 시각화 오버레이 → 스트리밍(web\_video\_server) → 외부 공개(cloudflared)까지 동작합니다.

---

## 0) 요구사항

* **OS/ROS**: Ubuntu 20.04 + **ROS1 Noetic** (권장)
* **Python**: 3.8+ (ROS 환경과 동일 권장)
* **패키지(ROS)**: `roscore`, `rosbag`(선택), `web_video_server`
* **패키지(Python)**: `numpy`, `opencv-python`, `rospkg`, `cv_bridge` (ROS 설치 시 포함), `pyyaml`
* **레포 구조(예시)**

  ```
  ~/nomad/
  ├── deployment/
  │   └── src/
  │       ├── explore.py
  │       ├── viz_overlay.py
  │       └── image_dir_player.py
  └── processed_data/
      └── data_00000014_0/      # 이미지 폴더 (jpg/png 등)
  ```

> **토픽 형식 가정**
>
> * 이미지: `/usb_cam/image_raw` (`sensor_msgs/Image`)
> * 웨이포인트: `/waypoint` (`std_msgs/Float32MultiArray`)
> * 샘플 액션: `/sampled_actions` (메시지 타입은 내부 코드가 publish하는 형태)

---

## 1) 빠른 실행(터미널 별)

아래는 각 **서로 다른 터미널**에서 순서대로 실행하는 권장 플로우입니다.

### T1 — roscore

```bash
roscore
```

### T2 — 이미지 디렉토리 재생

이미지 폴더를 ROS 이미지 토픽으로 Publish합니다.

```bash
python /root/nomad/deployment/src/image_dir_player.py \
  --dir /root/nomad/processed_data/data_00000014_0 \
  --rate 9 \
  --topic /usb_cam/image_raw \
  --loop
```

* `--dir`: 이미지가 있는 디렉토리 경로
* `--rate`: 초당 프레임(Hz)
* `--topic`: 퍼블리시할 이미지 토픽명
* `--loop`: 폴더 끝까지 가면 다시 처음부터 반복

### T3 — 모델 추론(웨이포인트/액션 샘플)

```bash
cd ~/nomad/deployment/src
python3 explore.py --model nomad --num-samples 8 --waypoint 2
```

* `--model`: 사용할 모델 이름 (예: `nomad`)
* `--num-samples`: 샘플링 개수
* `--waypoint`: 사용할 웨이포인트 인덱스/모드 (내부 로직에 맞춰 조정)

> **참고**: 모델 체크포인트 경로/로딩 로직은 `explore.py` 내부에서 설정되어 있을 수 있습니다. 경로가 다르면 아래 “커스터마이즈 포인트” 참고.

### T4 — 오버레이 시각화 노드

```bash
cd ~/nomad/deployment/src
python3 viz_overlay.py \
  --image /usb_cam/image_raw \
  --waypoint /waypoint \
  --samples /sampled_actions \
  --out /viz/image
```

* `--image`: 입력 이미지 토픽
* `--waypoint`: 웨이포인트 토픽
* `--samples`: 샘플 액션 토픽
* `--out`: 오버레이 결과 이미지 토픽

### T5 — 웹 스트리밍(로컬 네트워크)

```bash
rosrun web_video_server web_video_server _address:=0.0.0.0 _port:=8888
```

* 로컬 브라우저에서 `http://<HOST_IP>:8888/stream?topic=/viz/image` 로 확인

### T6 — 외부 공개(선택, cloudflared)

```bash
cloudflared tunnel --url http://127.0.0.1:8888
```

* 실행 로그에 표시되는 **trycloudflare.com** URL을 공유하면 외부에서도 접근 가능

---

## 2) 한 번에 실행하고 싶다면 (tmux 예시)

아래 스크립트를 `run_all.sh`로 저장 후 실행 권한을 주고 사용하세요.

```bash
#!/usr/bin/env bash
set -e
SESSION="nomad_demo"

# tmux 세션 생성
tmux new-session -d -s $SESSION

# T1 roscore
tmux rename-window -t $SESSION:0 'roscore'
tmux send-keys -t $SESSION:0 'roscore' C-m

# T2 image_dir_player
tmux new-window -t $SESSION -n 'image_player'
tmux send-keys -t $SESSION:1 'python /root/nomad/deployment/src/image_dir_player.py --dir /root/nomad/processed_data/data_00000014_0 --rate 9 --topic /usb_cam/image_raw --loop' C-m

# T3 explore.py
tmux new-window -t $SESSION -n 'explore'
tmux send-keys -t $SESSION:2 'cd ~/nomad/deployment/src && python3 explore.py --model nomad --num-samples 8 --waypoint 2' C-m

# T4 viz_overlay
tmux new-window -t $SESSION -n 'viz'
tmux send-keys -t $SESSION:3 'cd ~/nomad/deployment/src && python3 viz_overlay.py --image /usb_cam/image_raw --waypoint /waypoint --samples /sampled_actions --out /viz/image' C-m

# T5 web_video_server
tmux new-window -t $SESSION -n 'web_video'
tmux send-keys -t $SESSION:4 'rosrun web_video_server web_video_server _address:=0.0.0.0 _port:=8888' C-m

# T6 cloudflared (옵션)
tmux new-window -t $SESSION -n 'cloudflared'
tmux send-keys -t $SESSION:5 'cloudflared tunnel --url http://127.0.0.1:8888' C-m

# 세션 attach
tmux attach -t $SESSION
```

```bash
chmod +x run_all.sh
./run_all.sh
```

---

## 3) 커스터마이즈 포인트(필수 수정 위치)

### A) 데이터/토픽 이름 변경

* **이미지 폴더**: `image_dir_player.py` 실행 시 `--dir` 만 변경하면 됩니다.
* **프레임레이트**: `--rate` 값으로 조절(예: 5, 9, 15 등)
* **토픽명**: `--topic`, `--image`, `--waypoint`, `--samples`, `--out` 인자를 상황에 맞게 변경

### B) 모델 경로/파라미터

* `deployment/src/explore.py` 내부에서 모델 로딩/체크포인트 경로를 확인하세요.

  * 예: `checkpoint = /path/to/nomad.pth`
  * 하드코딩돼 있으면 `argparse` 인자를 추가하여 외부에서 넘길 수 있게 바꾸세요.
  * 예시 패치:

    ```python
    # explore.py 상단
    parser.add_argument('--ckpt', type=str, default='~/nomad/model_weights/nomad.pth')
    # ...로딩부에서 args.ckpt 사용
    ```
* 샘플링 횟수/웨이포인트 모드는 `--num-samples`, `--waypoint` 인자로 노출돼 있으니 필요 시 기본값만 바꾸면 됩니다.

### C) 오버레이 스타일

* `viz_overlay.py` 내에서 컬러, 두께, 폰트, 스케일 등을 OpenCV 파라미터로 변경 가능

  * 예: `cv2.circle`, `cv2.line`, `cv2.putText` 의 색/두께 수정
  * 결과 토픽 `--out` 이름을 바꿔 다른 스트림과 구분

### D) 스트리밍 포트/주소

* `web_video_server`:

  * `_port:=8888` → 다른 포트로 충돌 회피 가능
  * `_address:=0.0.0.0` → 로컬 네트워크 전체 공개
* `cloudflared`:

  * `--url http://127.0.0.1:<PORT>`에서 `<PORT>`만 일치시키면 됨

---

## 4) 자주 나는 이슈 & 해결

* **`roscore` 미실행 오류**: 모든 노드 실행 전에 반드시 `roscore`를 먼저 켜세요.
* **토픽 타입 불일치**: `rostopic echo /waypoint -n1` 로 메시지 타입을 확인하고, 코드 기대 타입과 맞추세요.
* **`tf` 모듈 에러**: `import tf` 는 ROS1의 `tf`(Python 바인딩)입니다. `ros-noetic-tf` 패키지가 필요할 수 있습니다.

  ```bash
  sudo apt-get update && sudo apt-get install -y ros-noetic-tf
  ```
* **cv\_bridge 에러**: 아래로 설치 확인

  ```bash
  sudo apt-get install -y ros-noetic-cv-bridge ros-noetic-vision-opencv
  ```
* **`web_video_server` 없음**:

  ```bash
  sudo apt-get install -y ros-noetic-web-video-server
  ```
* **권한 문제(스크립트 실행)**:

  ```bash
  chmod +x ~/nomad/deployment/src/*.py
  ```
* **네트워크 접근 불가**: 방화벽/보안 그룹에서 8888 포트 허용 또는 다른 포트 사용.

---

## 5) 최소 설치 명령(요약)

```bash
sudo apt-get update
sudo apt-get install -y ros-noetic-desktop-full \
    ros-noetic-web-video-server \
    ros-noetic-tf ros-noetic-cv-bridge ros-noetic-vision-opencv

python3 -m pip install --upgrade pip
python3 -m pip install numpy opencv-python pyyaml rospkg
```

---

## 6) 확인 방법

* 토픽 확인

  ```bash
  rostopic list
  rostopic hz /usb_cam/image_raw
  rostopic echo /waypoint -n1
  rostopic list | grep viz
  ```
* 스트림 보기

  * 로컬: `http://<HOST_IP>:8888/` → **Streams** 목록에서 `/viz/image` 선택
  * 외부: `cloudflared`가 출력한 URL에서 `/stream?topic=/viz/image` 접속

---

## 7) 라이선스/인용(예시)

* 본 레포 코드와 모델 가중치의 라이선스/출처를 `LICENSE`와 `README` 하단에 명시하세요.
* 공개 저장소일 경우, 모델 가중치(예: `nomad.pth`) 배포 정책을 확인하세요.

---

## 8) 연락/기여

* 이 README로 실행 시 문제가 있으면 이슈 탭에 로그/스크린샷과 함께 남겨주세요.
* PR로 환경변수/인자 개선 환영합니다.
