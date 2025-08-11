from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import List, Optional

import numpy as np
import torch
from PIL import Image as PILImage
from diffusers.schedulers.scheduling_ddpm import DDPMScheduler

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy

from sensor_msgs.msg import Image
from std_msgs.msg import Float32MultiArray


def get_repo_root() -> Path:
    here = Path(__file__).resolve()
    # Try to locate original repo structure
    for p in [here.parents[4], *here.parents]:
        if (p / 'train' / 'config').exists() and (p / 'deployment' / 'src').exists():
            return p
    env = os.getenv('NOMAD_ROOT')
    if env:
        return Path(env).expanduser().resolve()
    # Fallback
    return here.parents[4]


REPO_ROOT = get_repo_root()

# Ensure we can import original project modules
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / 'deployment' / 'src'))
sys.path.insert(0, str(REPO_ROOT / 'diffusion_policy'))
sys.path.insert(0, str(REPO_ROOT / 'train'))

# Now import project utilities
from utils import msg_to_pil, to_numpy, transform_images, load_model  # type: ignore
from topic_names import IMAGE_TOPIC, WAYPOINT_TOPIC, SAMPLED_ACTIONS_TOPIC  # type: ignore


class ExploreNode(Node):
    def __init__(self) -> None:
        super().__init__('explore')

        # Parameters
        self.declare_parameter('model', 'nomad')
        self.declare_parameter('config', '')
        self.declare_parameter('num_samples', 8)
        self.declare_parameter('waypoint_index', 2)
        self.declare_parameter('rate', 9.0)  # fallback if robot.yaml missing

        self.model_name: str = str(self.get_parameter('model').value)
        self.config_path_param: str = str(self.get_parameter('config').value)
        self.num_samples: int = int(self.get_parameter('num_samples').value)
        self.waypoint_index: int = int(self.get_parameter('waypoint_index').value)
        self.rate_hz: float = float(self.get_parameter('rate').value)

        # Try to load robot config for RATE if available
        try:
            import yaml  # local import
            robot_cfg_path = REPO_ROOT / 'deployment' / 'config' / 'robot.yaml'
            if robot_cfg_path.exists():
                with open(robot_cfg_path, 'r') as f:
                    robot_cfg = yaml.safe_load(f) or {}
                self.rate_hz = float(robot_cfg.get('frame_rate', self.rate_hz))
        except Exception as e:
            self.get_logger().warn(f'Failed loading robot.yaml: {e}')

        # Model config
        default_cfg = REPO_ROOT / 'train' / 'config' / f'{self.model_name}.yaml'
        cfg_path = Path(self.config_path_param).resolve() if self.config_path_param else default_cfg

        import yaml
        try:
            with open(cfg_path, 'r') as f:
                cfg = yaml.safe_load(f) or {}
        except Exception as e:
            raise RuntimeError(f'Failed to load config: {cfg_path}\n{e}')

        model_params = cfg.get('model', cfg)
        if 'context_size' not in model_params:
            raise KeyError(f'Missing required key context_size in {cfg_path}')

        self.context_size: int = int(model_params['context_size'])
        self.model_params = model_params

        # Load weights mapping
        models_yaml = REPO_ROOT / 'deployment' / 'config' / 'models.yaml'
        with open(models_yaml, 'r') as f:
            model_paths = yaml.safe_load(f)

        ckpt_path = model_paths[self.model_name]['ckpt_path']
        if not os.path.isabs(ckpt_path):
            ckpt_path = str(REPO_ROOT / ckpt_path)
        if not os.path.exists(ckpt_path):
            raise FileNotFoundError(f'Model weights not found at {ckpt_path}')

        # Device
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.get_logger().info(f'Using device: {self.device}')

        # Load model
        self.model = load_model(ckpt_path, self.model_params, self.device).to(self.device).eval()

        # Diffusion scheduler
        self.noise_scheduler = DDPMScheduler(
            num_train_timesteps=self.model_params['num_diffusion_iters'],
            beta_schedule='squaredcos_cap_v2',
            clip_sample=True,
            prediction_type='epsilon',
        )

        # State
        self.context_queue: List[PILImage.Image] = []

        # QoS for sensor data
        sensor_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=5,
        )

        # ROS2 I/O
        self.create_subscription(Image, IMAGE_TOPIC, self._image_cb, sensor_qos)
        self.waypoint_pub = self.create_publisher(Float32MultiArray, WAYPOINT_TOPIC, 10)
        self.sampled_actions_pub = self.create_publisher(Float32MultiArray, SAMPLED_ACTIONS_TOPIC, 10)

        # Timer loop
        self.create_timer(1.0 / max(self.rate_hz, 1e-3), self._tick)
        self.get_logger().info('ExploreNode started')

    def _image_cb(self, msg: Image) -> None:
        obs_img = msg_to_pil(msg)
        if len(self.context_queue) < self.context_size + 1:
            self.context_queue.append(obs_img)
        else:
            self.context_queue.pop(0)
            self.context_queue.append(obs_img)

    @torch.no_grad()
    def _tick(self) -> None:
        if len(self.context_queue) <= self.context_size:
            return

        # Prepare images
        obs_images = transform_images(self.context_queue, self.model_params['image_size'], center_crop=False)
        obs_images = obs_images.to(self.device)
        fake_goal = torch.randn((1, 3, *self.model_params['image_size']), device=self.device)
        mask = torch.ones(1, dtype=torch.long, device=self.device)  # ignore goal

        # Encode vision features
        obs_cond = self.model('vision_encoder', obs_img=obs_images, goal_img=fake_goal, input_goal_mask=mask)
        if len(obs_cond.shape) == 2:
            obs_cond = obs_cond.repeat(self.num_samples, 1)
        else:
            obs_cond = obs_cond.repeat(self.num_samples, 1, 1)

        # Initialize action from Gaussian noise
        naction = torch.randn((self.num_samples, self.model_params['len_traj_pred'], 2), device=self.device)

        # Diffusion steps
        self.noise_scheduler.set_timesteps(self.model_params['num_diffusion_iters'])
        t0 = time.time()
        for k in self.noise_scheduler.timesteps[:]:
            noise_pred = self.model('noise_pred_net', sample=naction, timestep=k, global_cond=obs_cond)
            naction = self.noise_scheduler.step(model_output=noise_pred, timestep=k, sample=naction).prev_sample
        self.get_logger().debug(f'diffusion elapsed: {time.time() - t0:.3f}s')

        # Publish sampled actions (flattened)
        from vint_train.training.train_utils import get_action  # type: ignore
        np_actions = to_numpy(get_action(naction))
        sampled = Float32MultiArray()
        sampled.data = np.concatenate((np.array([0], dtype=np.float32), np_actions.flatten())).tolist()
        self.sampled_actions_pub.publish(sampled)

        # Choose waypoint and publish
        chosen = np_actions[0][self.waypoint_index]
        if self.model_params.get('normalize', False):
            # scale by max velocity / rate
            max_v = float(self.model_params.get('max_v', 0.4))
            chosen *= (max_v / self.rate_hz)
        wp = Float32MultiArray()
        wp.data = chosen.tolist()
        self.waypoint_pub.publish(wp)
        self.get_logger().info('Published waypoint')


def main() -> None:
    rclpy.init()
    node = ExploreNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


