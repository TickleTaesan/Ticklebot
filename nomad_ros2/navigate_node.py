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

# ROS2
from sensor_msgs.msg import Image
from std_msgs.msg import Bool, Float32MultiArray
from cv_bridge import CvBridge
import cv2
from PIL import Image as PILImage
import time
import argparse

# Import from original utils (will be converted later)
import sys
sys.path.append('../deployment/src')
from utils import msg_to_pil, to_numpy, transform_images, load_model
from vint_train.training.train_utils import get_action

# Import topic names
from .topic_names import (IMAGE_TOPIC,
                         WAYPOINT_TOPIC,
                         SAMPLED_ACTIONS_TOPIC,
                         GOAL_REACHED_TOPIC)

# CONSTANTS
TOPOMAP_IMAGES_DIR = "../topomaps/images"
MODEL_WEIGHTS_PATH = "../model_weights"
ROBOT_CONFIG_PATH = "../config/robot.yaml"
MODEL_CONFIG_PATH = "../config/models.yaml"

class NavigateNode(Node):
    def __init__(self, args):
        super().__init__('navigate_node')
        
        # Load robot config
        with open(ROBOT_CONFIG_PATH, "r") as f:
            robot_config = yaml.safe_load(f)
        self.max_v = robot_config["max_v"]
        self.max_w = robot_config["max_w"]
        self.rate = robot_config["frame_rate"]
        
        # Load model config
        with open(MODEL_CONFIG_PATH, "r") as f:
            model_paths = yaml.safe_load(f)
        
        model_config_path = model_paths[args.model]["config_path"]
        with open(model_config_path, "r") as f:
            self.model_params = yaml.safe_load(f)
        
        self.context_size = self.model_params["context_size"]
        self.context_queue = []
        
        # Load model
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
        
        # Load topomap
        topomap_filenames = sorted(os.listdir(os.path.join(
            TOPOMAP_IMAGES_DIR, args.dir)), key=lambda x: int(x.split(".")[0]))
        topomap_dir = f"{TOPOMAP_IMAGES_DIR}/{args.dir}"
        num_nodes = len(os.listdir(topomap_dir))
        self.topomap = []
        for i in range(num_nodes):
            image_path = os.path.join(topomap_dir, topomap_filenames[i])
            self.topomap.append(PILImage.open(image_path))
        
        # Navigation parameters
        self.closest_node = 0
        assert -1 <= args.goal_node < len(self.topomap), "Invalid goal index"
        if args.goal_node == -1:
            self.goal_node = len(self.topomap) - 1
        else:
            self.goal_node = args.goal_node
        self.reached_goal = False
        
        # Arguments
        self.args = args
        
        # Setup NoMaD diffusion scheduler if needed
        if self.model_params["model_type"] == "nomad":
            self.num_diffusion_iters = self.model_params["num_diffusion_iters"]
            self.noise_scheduler = DDPMScheduler(
                num_train_timesteps=self.model_params["num_diffusion_iters"],
                beta_schedule='squaredcos_cap_v2',
                clip_sample=True,
                prediction_type='epsilon'
            )
        
        # Setup ROS2 publishers and subscribers
        self.setup_ros2_interface()
        
        # Setup timer for navigation loop
        self.timer = self.create_timer(1.0 / self.rate, self.navigation_loop)
        
        self.get_logger().info("Navigate node initialized successfully")
    
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
        
        self.goal_pub = self.create_publisher(
            Bool,
            GOAL_REACHED_TOPIC,
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
    
    def navigation_loop(self):
        """Main navigation loop"""
        # EXPLORATION MODE
        chosen_waypoint = np.zeros(4)
        
        if len(self.context_queue) > self.model_params["context_size"]:
            if self.model_params["model_type"] == "nomad":
                chosen_waypoint = self.nomad_inference()
            else:
                chosen_waypoint = self.vint_gnm_inference()
        
        # RECOVERY MODE
        if self.model_params["normalize"]:
            chosen_waypoint[:2] *= (self.max_v / self.rate)
        
        # Publish waypoint
        waypoint_msg = Float32MultiArray()
        waypoint_msg.data = chosen_waypoint.tolist()
        self.waypoint_pub.publish(waypoint_msg)
        
        # Check if goal reached
        self.reached_goal = self.closest_node == self.goal_node
        goal_msg = Bool()
        goal_msg.data = self.reached_goal
        self.goal_pub.publish(goal_msg)
        
        if self.reached_goal:
            self.get_logger().info("Reached goal! Stopping...")
            self.timer.cancel()
    
    def nomad_inference(self):
        """NoMaD model inference"""
        obs_images = transform_images(self.context_queue, self.model_params["image_size"], center_crop=False)
        obs_images = torch.split(obs_images, 3, dim=1)
        obs_images = torch.cat(obs_images, dim=1)
        obs_images = obs_images.to(self.device)
        mask = torch.zeros(1).long().to(self.device)
        
        start = max(self.closest_node - self.args.radius, 0)
        end = min(self.closest_node + self.args.radius + 1, self.goal_node)
        goal_image = [transform_images(g_img, self.model_params["image_size"], center_crop=False).to(self.device) 
                     for g_img in self.topomap[start:end + 1]]
        goal_image = torch.concat(goal_image, dim=0)
        
        obsgoal_cond = self.model('vision_encoder', obs_img=obs_images.repeat(len(goal_image), 1, 1, 1), 
                                 goal_img=goal_image, input_goal_mask=mask.repeat(len(goal_image)))
        dists = self.model("dist_pred_net", obsgoal_cond=obsgoal_cond)
        dists = to_numpy(dists.flatten())
        min_idx = np.argmin(dists)
        self.closest_node = min_idx + start
        self.get_logger().info(f"closest node: {self.closest_node}")
        
        sg_idx = min(min_idx + int(dists[min_idx] < self.args.close_threshold), len(obsgoal_cond) - 1)
        obs_cond = obsgoal_cond[sg_idx].unsqueeze(0)
        
        # Infer action
        with torch.no_grad():
            # Encoder vision features
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
        self.get_logger().info("published sampled actions")
        
        naction = naction[0]
        return naction[self.args.waypoint]
    
    def vint_gnm_inference(self):
        """ViNT/GNM model inference"""
        start = max(self.closest_node - self.args.radius, 0)
        end = min(self.closest_node + self.args.radius + 1, self.goal_node)
        distances = []
        waypoints = []
        batch_obs_imgs = []
        batch_goal_data = []
        
        for i, sg_img in enumerate(self.topomap[start: end + 1]):
            transf_obs_img = transform_images(self.context_queue, self.model_params["image_size"])
            goal_data = transform_images(sg_img, self.model_params["image_size"])
            batch_obs_imgs.append(transf_obs_img)
            batch_goal_data.append(goal_data)
        
        # Predict distances and waypoints
        batch_obs_imgs = torch.cat(batch_obs_imgs, dim=0).to(self.device)
        batch_goal_data = torch.cat(batch_goal_data, dim=0).to(self.device)
        
        distances, waypoints = self.model(batch_obs_imgs, batch_goal_data)
        distances = to_numpy(distances)
        waypoints = to_numpy(waypoints)
        
        # Look for closest node
        min_dist_idx = np.argmin(distances)
        
        # Choose subgoal and output waypoints
        if distances[min_dist_idx] > self.args.close_threshold:
            chosen_waypoint = waypoints[min_dist_idx][self.args.waypoint]
            self.closest_node = start + min_dist_idx
        else:
            chosen_waypoint = waypoints[min(min_dist_idx + 1, len(waypoints) - 1)][self.args.waypoint]
            self.closest_node = min(start + min_dist_idx + 1, self.goal_node)
        
        return chosen_waypoint


def main(args=None):
    rclpy.init(args=args)
    
    # Parse arguments (simplified for ROS2)
    parser = argparse.ArgumentParser(description="Code to run GNM DIFFUSION EXPLORATION on the locobot")
    parser.add_argument("--model", "-m", default="nomad", type=str,
                       help="model name (only nomad is supported)")
    parser.add_argument("--waypoint", "-w", default=2, type=int,
                       help="index of the waypoint used for navigation")
    parser.add_argument("--dir", "-d", default="topomap", type=str,
                       help="path to topomap images")
    parser.add_argument("--goal-node", "-g", default=-1, type=int,
                       help="goal node index in the topomap")
    parser.add_argument("--close-threshold", "-t", default=3, type=int,
                       help="temporal distance within the next node")
    parser.add_argument("--radius", "-r", default=4, type=int,
                       help="temporal number of locobal nodes to look at")
    parser.add_argument("--num-samples", "-n", default=8, type=int,
                       help="Number of actions sampled from the exploration model")
    
    # For ROS2, we'll use default arguments for now
    # In a real implementation, you'd get these from ROS2 parameters
    args = parser.parse_args([])  # Empty list for default values
    
    try:
        node = NavigateNode(args)
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main() 