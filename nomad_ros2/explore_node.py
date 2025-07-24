#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
import matplotlib.pyplot as plt
import os
from typing import Tuple, Sequence, Dict, Union, Optional, Callable
import numpy as np
import torch
import torch.nn as nn
from diffusers.schedulers.scheduling_ddpm import DDPMScheduler

import matplotlib.pyplot as plt
import yaml
import time
import argparse

# ROS2
from sensor_msgs.msg import Image
from std_msgs.msg import Bool, Float32MultiArray

# Import from original utils (will be converted later)
import sys
sys.path.append('../deployment/src')
from utils import msg_to_pil, to_numpy, transform_images, load_model
from vint_train.training.train_utils import get_action

# Import topic names
from .topic_names import (IMAGE_TOPIC,
                         WAYPOINT_TOPIC,
                         SAMPLED_ACTIONS_TOPIC)

# CONSTANTS
MODEL_WEIGHTS_PATH = "../model_weights"
ROBOT_CONFIG_PATH = "../config/robot.yaml"
MODEL_CONFIG_PATH = "../config/models.yaml"
with open(ROBOT_CONFIG_PATH, "r") as f:
    robot_config = yaml.safe_load(f)
MAX_V = robot_config["max_v"]
MAX_W = robot_config["max_w"]
RATE = robot_config["frame_rate"]


class ExploreNode(Node):
    def __init__(self, args):
        super().__init__('explore_node')
        
        # Initialize variables
        self.context_queue = []
        self.context_size = None
        
        # Load model parameters
        with open(MODEL_CONFIG_PATH, "r") as f:
            model_paths = yaml.safe_load(f)
        
        model_config_path = model_paths[args.model]["config_path"]
        with open(model_config_path, "r") as f:
            self.model_params = yaml.safe_load(f)
        
        self.context_size = self.model_params["context_size"]
        
        # Load model weights
        ckpth_path = model_paths[args.model]["ckpt_path"]
        if os.path.exists(ckpth_path):
            self.get_logger().info(f"Loading model from {ckpth_path}")
        else:
            raise FileNotFoundError(f"Model weights not found at {ckpth_path}")
        
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.get_logger().info(f"Using device: {self.device}")
        
        self.model = load_model(ckpth_path, self.model_params, self.device)
        self.model = self.model.to(self.device)
        self.model.eval()
        
        # Setup NoMaD diffusion scheduler
        self.num_diffusion_iters = self.model_params["num_diffusion_iters"]
        self.noise_scheduler = DDPMScheduler(
            num_train_timesteps=self.model_params["num_diffusion_iters"],
            beta_schedule='squaredcos_cap_v2',
            clip_sample=True,
            prediction_type='epsilon'
        )
        
        # Arguments
        self.args = args
        
        # Setup ROS2 interface
        self.setup_ros2_interface()
        
        # Setup timer for exploration loop
        self.timer = self.create_timer(1.0 / RATE, self.exploration_loop)
        
        self.get_logger().info("Explore node initialized successfully")
    
    def setup_ros2_interface(self):
        """Setup ROS2 publishers and subscribers"""
        # QoS profile for real-time data
        qos_profile = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=1
        )
        
        # Subscribers
        self.image_sub = self.create_subscription(
            Image,
            IMAGE_TOPIC,
            self.callback_obs,
            qos_profile
        )
        
        # Publishers
        self.waypoint_pub = self.create_publisher(
            Float32MultiArray,
            WAYPOINT_TOPIC,
            1
        )
        
        self.sampled_actions_pub = self.create_publisher(
            Float32MultiArray,
            SAMPLED_ACTIONS_TOPIC,
            1
        )
        
        self.get_logger().info("ROS2 interface setup complete")
    
    def callback_obs(self, msg):
        """Callback for image observations"""
        obs_img = msg_to_pil(msg)
        if self.context_size is not None:
            if len(self.context_queue) < self.context_size + 1:
                self.context_queue.append(obs_img)
            else:
                self.context_queue.pop(0)
                self.context_queue.append(obs_img)
    
    def exploration_loop(self):
        """Main exploration loop"""
        # EXPLORATION MODE
        waypoint_msg = Float32MultiArray()
        
        if len(self.context_queue) > self.model_params["context_size"]:
            obs_images = transform_images(self.context_queue, self.model_params["image_size"], center_crop=False)
            obs_images = obs_images.to(self.device)
            fake_goal = torch.randn((1, 3, *self.model_params["image_size"])).to(self.device)
            mask = torch.ones(1).long().to(self.device)  # ignore the goal
            
            # Infer action
            with torch.no_grad():
                # Encoder vision features
                obs_cond = self.model('vision_encoder', obs_img=obs_images, goal_img=fake_goal, input_goal_mask=mask)
                
                # (B, obs_horizon * obs_dim)
                if len(obs_cond.shape) == 2:
                    obs_cond = obs_cond.repeat(self.args.num_samples, 1)
                else:
                    obs_cond = obs_cond.repeat(self.args.num_samples, 1, 1)
                
                # Initialize action from Gaussian noise
                noisy_action = torch.randn(
                    (self.args.num_samples, self.model_params["len_traj_pred"], 2), device=self.device)
                naction = noisy_action
                
                # Init scheduler
                self.noise_scheduler.set_timesteps(self.num_diffusion_iters)
                
                start_time = time.time()
                for k in self.noise_scheduler.timesteps[:]:
                    # Predict noise
                    noise_pred = self.model(
                        'noise_pred_net',
                        sample=naction,
                        timestep=k,
                        global_cond=obs_cond
                    )
                    
                    # Inverse diffusion step (remove noise)
                    naction = self.noise_scheduler.step(
                        model_output=noise_pred,
                        timestep=k,
                        sample=naction
                    ).prev_sample
                self.get_logger().info(f"time elapsed: {time.time() - start_time}")
            
            naction = to_numpy(get_action(naction))
            
            sampled_actions_msg = Float32MultiArray()
            sampled_actions_msg.data = np.concatenate((np.array([0]), naction.flatten())).tolist()
            self.sampled_actions_pub.publish(sampled_actions_msg)
            
            naction = naction[0]  # change this based on heuristic
            
            chosen_waypoint = naction[self.args.waypoint]
            
            if self.model_params["normalize"]:
                chosen_waypoint *= (MAX_V / RATE)
            waypoint_msg.data = chosen_waypoint.tolist()
            self.waypoint_pub.publish(waypoint_msg)
            self.get_logger().info("Published waypoint")


def main(args=None):
    rclpy.init(args=args)
    
    # Parse arguments (simplified for ROS2)
    parser = argparse.ArgumentParser(description="Code to run GNM DIFFUSION EXPLORATION on the locobot")
    parser.add_argument("--model", "-m", default="nomad", type=str,
                       help="model name (hint: check ../config/models.yaml)")
    parser.add_argument("--waypoint", "-w", default=2, type=int,
                       help="index of the waypoint used for navigation")
    parser.add_argument("--num-samples", "-n", default=8, type=int,
                       help="Number of actions sampled from the exploration model")
    
    # For ROS2, we'll use default arguments for now
    # In a real implementation, you'd get these from ROS2 parameters
    args = parser.parse_args([])  # Empty list for default values
    
    try:
        node = ExploreNode(args)
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main() 