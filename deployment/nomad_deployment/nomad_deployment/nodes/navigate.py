from __future__ import annotations

import os
import time
from pathlib import Path
from typing import List

import numpy as np
from PIL import Image as PILImage

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy

from sensor_msgs.msg import Image
from std_msgs.msg import Bool, Float32MultiArray


def get_repo_root() -> Path:
    here = Path(__file__).resolve()
    for p in [here.parents[4], *here.parents]:
        if (p / 'train' / 'config').exists() and (p / 'deployment' / 'src').exists():
            return p
    env = os.getenv('NOMAD_ROOT')
    if env:
        return Path(env).expanduser().resolve()
    return here.parents[4]


REPO_ROOT = get_repo_root()

# Add project paths for imports
import sys
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / 'deployment' / 'src'))
sys.path.insert(0, str(REPO_ROOT / 'diffusion_policy'))
sys.path.insert(0, str(REPO_ROOT / 'train'))

from utils import msg_to_pil, to_numpy, transform_images, load_model  # type: ignore
from topic_names import IMAGE_TOPIC, WAYPOINT_TOPIC, SAMPLED_ACTIONS_TOPIC  # type: ignore


class NavigateNode(Node):
    def __init__(self) -> None:
        super().__init__('navigate')

        # Parameters mirroring original script
        self.declare_parameter('model', 'nomad')
        self.declare_parameter('waypoint', 2)
        self.declare_parameter('dir', 'topomap')
        self.declare_parameter('goal_node', -1)
        self.declare_parameter('close_threshold', 3)
        self.declare_parameter('radius', 4)
        self.declare_parameter('rate', 9.0)
        self.declare_parameter('config', '')  # optional explicit config path

        self.model_name: str = str(self.get_parameter('model').value)
        self.waypoint_index: int = int(self.get_parameter('waypoint').value)
        self.topomap_dir_name: str = str(self.get_parameter('dir').value)
        self.goal_node_param: int = int(self.get_parameter('goal_node').value)
        self.close_threshold: int = int(self.get_parameter('close_threshold').value)
        self.radius: int = int(self.get_parameter('radius').value)
        self.rate_hz: float = float(self.get_parameter('rate').value)
        self.config_path_param: str = str(self.get_parameter('config').value)

        # Load robot config for rate if available
        try:
            import yaml
            robot_cfg_path = REPO_ROOT / 'deployment' / 'config' / 'robot.yaml'
            if robot_cfg_path.exists():
                with open(robot_cfg_path, 'r') as f:
                    robot_cfg = yaml.safe_load(f) or {}
                self.rate_hz = float(robot_cfg.get('frame_rate', self.rate_hz))
                self.max_v = float(robot_cfg.get('max_v', 0.4))
                self.max_w = float(robot_cfg.get('max_w', 0.8))
            else:
                self.max_v = 0.4
                self.max_w = 0.8
        except Exception:
            self.max_v = 0.4
            self.max_w = 0.8

        # Load model config
        import yaml
        default_cfg = REPO_ROOT / 'train' / 'config' / f'{self.model_name}.yaml'
        cfg_path = Path(self.config_path_param).resolve() if self.config_path_param else default_cfg
        with open(cfg_path, 'r') as f:
            cfg = yaml.safe_load(f) or {}
        self.model_params = cfg.get('model', cfg)
        self.context_size: int = int(self.model_params['context_size'])

        # Model weights mapping
        models_yaml = REPO_ROOT / 'deployment' / 'config' / 'models.yaml'
        with open(models_yaml, 'r') as f:
            model_paths = yaml.safe_load(f)
        ckpt_path = model_paths[self.model_name]['ckpt_path']
        if not os.path.isabs(ckpt_path):
            ckpt_path = str(REPO_ROOT / ckpt_path)
        if not os.path.exists(ckpt_path):
            raise FileNotFoundError(f'Model weights not found at {ckpt_path}')

        # Device and model
        import torch
        from diffusers.schedulers.scheduling_ddpm import DDPMScheduler
        from vint_train.training.train_utils import get_action  # type: ignore

        self.torch = torch
        self.get_action = get_action
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = load_model(ckpt_path, self.model_params, self.device).to(self.device).eval()
        self.noise_scheduler = DDPMScheduler(
            num_train_timesteps=self.model_params['num_diffusion_iters'],
            beta_schedule='squaredcos_cap_v2',
            clip_sample=True,
            prediction_type='epsilon',
        )

        # Load topomap images
        self.topomap_images_dir = REPO_ROOT / 'deployment' / 'topomaps' / 'images' / self.topomap_dir_name
        assert self.topomap_images_dir.exists(), f'Topomap dir not found: {self.topomap_images_dir}'
        files = sorted(self.topomap_images_dir.iterdir(), key=lambda p: int(p.stem))
        self.topomap: List[PILImage.Image] = [PILImage.open(str(p)) for p in files]

        # Goal node
        if self.goal_node_param == -1:
            self.goal_node = len(self.topomap) - 1
        else:
            self.goal_node = self.goal_node_param
        self.closest_node = 0

        # State
        self.context_queue: List[PILImage.Image] = []

        # ROS2 I/O
        sensor_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=5,
        )
        self.create_subscription(Image, IMAGE_TOPIC, self._image_cb, sensor_qos)
        self.wp_pub = self.create_publisher(Float32MultiArray, WAYPOINT_TOPIC, 10)
        self.sampled_pub = self.create_publisher(Float32MultiArray, SAMPLED_ACTIONS_TOPIC, 10)
        self.goal_pub = self.create_publisher(Bool, '/topoplan/reached_goal', 10)

        # Timer loop
        self.create_timer(1.0 / max(self.rate_hz, 1e-3), self._tick)
        self.get_logger().info(f'NavigateNode started; goal_node={self.goal_node}, topomap={self.topomap_images_dir}')

    def _image_cb(self, msg: Image) -> None:
        obs_img = msg_to_pil(msg)
        if len(self.context_queue) < self.context_size + 1:
            self.context_queue.append(obs_img)
        else:
            self.context_queue.pop(0)
            self.context_queue.append(obs_img)

    @torch.no_grad()
    def _tick(self) -> None:  # type: ignore
        if len(self.context_queue) <= self.context_size:
            return

        chosen_waypoint = np.zeros(4, dtype=np.float32)
        if self.model_params.get('model_type', 'nomad') == 'nomad':
            # Encode obs
            obs_images = transform_images(self.context_queue, self.model_params['image_size'], center_crop=False)
            obs_images = self.torch.split(obs_images, 3, dim=1)
            obs_images = self.torch.cat(obs_images, dim=1)
            obs_images = obs_images.to(self.device)
            mask = self.torch.zeros(1, dtype=self.torch.long, device=self.device)

            start = max(self.closest_node - self.radius, 0)
            end = min(self.closest_node + self.radius + 1, self.goal_node)
            goal_batch = [transform_images(img, self.model_params['image_size'], center_crop=False).to(self.device) for img in self.topomap[start:end + 1]]
            goal_batch = self.torch.concat(goal_batch, dim=0)

            obsgoal_cond = self.model('vision_encoder', obs_img=obs_images.repeat(len(goal_batch), 1, 1, 1), goal_img=goal_batch, input_goal_mask=mask.repeat(len(goal_batch)))
            dists = self.model('dist_pred_net', obsgoal_cond=obsgoal_cond)
            dists = to_numpy(dists.flatten())
            min_idx = int(np.argmin(dists))
            self.closest_node = min_idx + start

            sg_idx = min(min_idx + int(dists[min_idx] < self.close_threshold), len(obsgoal_cond) - 1)
            obs_cond = obsgoal_cond[sg_idx].unsqueeze(0)

            # Sample actions by diffusion
            if len(obs_cond.shape) == 2:
                obs_cond = obs_cond.repeat(self.model_params.get('num_samples', 8), 1)
            else:
                obs_cond = obs_cond.repeat(self.model_params.get('num_samples', 8), 1, 1)

            naction = self.torch.randn((self.model_params.get('num_samples', 8), self.model_params['len_traj_pred'], 2), device=self.device)
            self.noise_scheduler.set_timesteps(self.model_params['num_diffusion_iters'])
            t0 = time.time()
            for k in self.noise_scheduler.timesteps[:]:
                noise_pred = self.model('noise_pred_net', sample=naction, timestep=k, global_cond=obs_cond)
                naction = self.noise_scheduler.step(model_output=noise_pred, timestep=k, sample=naction).prev_sample
            self.get_logger().debug(f'diffusion elapsed: {time.time() - t0:.3f}s')

            np_actions = to_numpy(self.get_action(naction))
            sampled = Float32MultiArray()
            sampled.data = np.concatenate((np.array([0], dtype=np.float32), np_actions.flatten())).tolist()
            self.sampled_pub.publish(sampled)
            np_actions = np_actions[0]
            chosen_waypoint = np_actions[self.waypoint_index]
        else:
            # Non-nomad path (kept minimal)
            start = max(self.closest_node - self.radius, 0)
            end = min(self.closest_node + self.radius + 1, self.goal_node)
            batch_obs_imgs = []
            batch_goal_data = []
            for sg_img in self.topomap[start:end + 1]:
                batch_obs_imgs.append(transform_images(self.context_queue, self.model_params['image_size']))
                batch_goal_data.append(transform_images(sg_img, self.model_params['image_size']))
            batch_obs_imgs = self.torch.cat(batch_obs_imgs, dim=0).to(self.device)
            batch_goal_data = self.torch.cat(batch_goal_data, dim=0).to(self.device)
            distances, waypoints = self.model(batch_obs_imgs, batch_goal_data)
            distances = to_numpy(distances)
            waypoints = to_numpy(waypoints)
            min_dist_idx = int(np.argmin(distances))
            if distances[min_dist_idx] > self.close_threshold:
                chosen_waypoint = waypoints[min_dist_idx][self.waypoint_index]
                self.closest_node = start + min_dist_idx
            else:
                chosen_waypoint = waypoints[min(min_dist_idx + 1, len(waypoints) - 1)][self.waypoint_index]
                self.closest_node = min(start + min_dist_idx + 1, self.goal_node)

        # Scale and publish
        if self.model_params.get('normalize', False):
            chosen_waypoint[..., :2] *= (self.max_v / self.rate_hz)
        wp = Float32MultiArray()
        wp.data = chosen_waypoint.tolist()
        self.wp_pub.publish(wp)

        reached = Bool()
        reached.data = bool(self.closest_node == self.goal_node)
        self.goal_pub.publish(reached)
        if reached.data:
            self.get_logger().info('Reached goal!')


def main() -> None:
    rclpy.init()
    node = NavigateNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


