# General Navigation Models: GNM, ViNT and NoMaD

This repository is a port of [visualnav-transformer](https://github.com/robodhruv/visualnav-transformer) to ROS2. Its purpose is to make running the models more straightforward by providing a Dockerfile with all dependencies set up. For more details on the models, please refer to the original repository.

### Run on host (no Docker)

#### 1) Prerequisites
- ROS2 Humble 환경 활성화
```bash
source /opt/ros/humble/setup.bash
```
- 프로젝트 루트에서 Python 모듈 경로 설정(또는 `pip3 install -e .` 사용)
```bash
export PYTHONPATH=$PWD/src
```
- 필수 패키지(예: Jetson/Ubuntu)
```bash
sudo apt update
sudo apt install -y ros-humble-v4l2-camera ros-humble-cv-bridge
```
- 모델 가중치 존재: `model_weights/nomad.pth`

#### 2) Bring up camera (USB webcam)
- 장치 확인(옵션): `ls /dev/video*`
- 카메라 노드 실행(YUYV + rgb8 권장)
```bash
ros2 run v4l2_camera v4l2_camera_node --ros-args \
  -p video_device:=/dev/video0 -p image_size:=[640,480] \
  -p pixel_format:=YUYV -p output_encoding:=rgb8
```
- 이미지 토픽 확인
```bash
ros2 topic list | grep -E "image_raw|camera_info"
```
  - 일반적으로 `/image_raw` 또는 `/v4l2_camera/image_raw`가 생성됩니다.

#### 3) Run model (exploration; no topomap)
- 확인된 이미지 토픽으로 리매핑하여 모델 실행
```bash
python3 src/visualnav_transformer/deployment/src/explore.py -m nomad \
  --ros-args -r /camera/camera/color/image_raw:=/image_raw
```
  - 우측 `/image_raw`는 실제 보이는 이미지 토픽 이름으로 바꿔주세요.

#### 4) Publish waypoint → cmd_vel
```bash
python3 scripts/publish_cmd.py
```

#### 5) Verify pipeline
```bash
ros2 topic echo /waypoint -n 1
ros2 topic echo /cmd_vel -n 1
```

#### 6) Optional: Create topomap and navigate
- Topomap 생성
```bash
python3 src/visualnav_transformer/deployment/src/create_topomap.py -d topomap -t 1.0 \
  --ros-args -r /camera/camera/color/image_raw:=/image_raw
```
- 내비게이션 실행(별도 터미널에서 `scripts/publish_cmd.py`도 실행 필요)
```bash
python3 src/visualnav_transformer/deployment/src/navigate.py -m nomad -d topomap -g -1 \
  --ros-args -r /camera/camera/color/image_raw:=/image_raw
```

#### Troubleshooting
- MJPG 인코딩 관련 예외가 나면(YUYV 권장):
  - `-p pixel_format:=YUYV -p output_encoding:=rgb8`로 재시도하세요.
- 이미지 토픽이 안 보이면:
  - `ros2 run image_tools cam2image`로 가짜 카메라를 띄워 빠르게 검증 가능(`/image`).
  - `groups | grep video`로 `video` 그룹 포함 여부 확인. 미포함 시 `sudo usermod -a -G video $USER` 후 재로그인.
- Calibration 경고는 초기에 무시해도 동작에는 지장 없습니다.

---

### Running the code (with Docker)

1. Clone the repository:
```bash
git clone https://github.com/RobotecAI/visualnav-transformer-ros2
cd visualnav-transformer-ros2
```

2. Build the Docker image:
```bash
docker build -t visualnav_transformer:latest .
```

3. Run the Docker container:
```bash
docker run -it --env ROS_DOMAIN_ID=$ROS_DOMAIN_ID --rm --gpus=all --net=host visualnav_transformer:latest
```

4. Run the model:

Inside the container, run the following commands:
```bash
poetry shell
python src/visualnav_transformer/deployment/src/explore.py
```
This will run the model and publish the predicted waypoints to a ROS2 topic, but your robot will not move yet. Next to running the model you have to run a script that will publish the movement commands to the robot.

```bash
python scripts/publish_cmd.py
```

Now the robot should start moving based on the model's predictions.

To visualize the waypoints that the model is outputting you can run the following command:
```bash
python scripts/visualize.py
```
A window should appear with the camera image and the model outputs updated in real time.

### Creating a topomap of the environment

In order to navigate to a desired goal location, the robot needs to have a map of the environment. To create a topomap of the environment, you can run the following command:
```bash
python src/visualnav_transformer/deployment/src/create_topomap.py
```
The script will save an image from the camera every second (this interval can be changed with the `-t` parameter). Now you can drive the robot around the environment manually (using your navigation stack or teleop) and the map will be saved automatically. After you have driven around the environment, you can stop the script and proceed to the next step.

### Navigation
Having created a topomap of the environment, you can now run the navigation script:
```bash
python src/visualnav_transformer/deployment/src/navigate.py
```
By default the robot will try to follow the topomap to reach the last image captured. You can specify a different goal image by providing an index of an image in the topomap using the `--goal-node` parameter.