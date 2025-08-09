from pathlib import Path
import matplotlib.pyplot as plt
import os
from typing import Tuple, Sequence, Dict, Union, Optional, Callable
import numpy as np
import torch
import torch.nn as nn
from diffusers.schedulers.scheduling_ddpm import DDPMScheduler
import argparse
import matplotlib.pyplot as plt
import yaml

# ROS
import rospy
from sensor_msgs.msg import Image
from std_msgs.msg import Bool, Float32MultiArray
from utils import msg_to_pil, to_numpy, transform_images, load_model

from vint_train.training.train_utils import get_action
import torch
from PIL import Image as PILImage
import numpy as np
import argparse
import yaml
import time


def get_repo_root() -> Path:

    here = Path(__file__).resolve()

    for p in [here.parents[2], *here.parents]:
        if (p / "train" / "config").exists() and (p / "deployment" / "src").exists():
            return p

    env = os.getenv("NOMAD_ROOT")
    if env:
        return Path(env).expanduser().resolve()

    return here.parents[2]

REPO_ROOT = get_repo_root()
repo_root = REPO_ROOT
# UTILS
from topic_names import (IMAGE_TOPIC,
                        WAYPOINT_TOPIC,
                        SAMPLED_ACTIONS_TOPIC)


# CONSTANTS
MODEL_WEIGHTS_PATH = "../model_weights"
ROBOT_CONFIG_PATH ="../config/robot.yaml"
MODEL_CONFIG_PATH = "../config/models.yaml"
with open(ROBOT_CONFIG_PATH, "r") as f:
    robot_config = yaml.safe_load(f)
MAX_V = robot_config["max_v"]
MAX_W = robot_config["max_w"]
RATE = robot_config["frame_rate"] 

# GLOBALS
context_queue = []
context_size = None  

# Load the model 
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print("Using device:", device)

def callback_obs(msg):
    obs_img = msg_to_pil(msg)
    if context_size is not None:
        if len(context_queue) < context_size + 1:
            context_queue.append(obs_img)
        else:
            context_queue.pop(0)
            context_queue.append(obs_img)


def main(args: argparse.Namespace):
    global context_size

    # load model parameters
    with open(MODEL_CONFIG_PATH, "r") as f:
        model_paths = yaml.safe_load(f)

    #repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
   # model_config_path = model_paths[args.model]["config_path"]
   # if not os.path.isabs(model_config_path):
    #    model_config_path = os.path.join(repo_root, model_config_path)
    default_cfg = REPO_ROOT / "train" / "config" / f"{args.model}.yaml"
    model_config_path = Path(args.config).resolve() if args.config else default_cfg
    try:
        with open(model_config_path, "r") as f:
             cfg = yaml.safe_load(f) or {}
    except Exception as e:
        raise RuntimeError(f"Failed to load config: {model_config_path}\n{e}")
    model_params = cfg.get("model", cfg)
    required_keys = ["context_size"] 
    missing = [k for k in required_keys if k not in model_params]
    if missing:
        raise KeyError(
            f"Missing keys in {model_config_path}: {missing}\n"
            f"Available keys: {list(model_params.keys())}"
        )
    if not model_config_path.exists():
        raise FileNotFoundError(
             f"Config not found: {model_config_path}\n"
             f"(Repo root guessed as: {REPO_ROOT})\n"
             f"Tip: pass --config /absolute/path/to/nomad.yaml"
        )
        with open(model_config_path, "r") as f:
            model_params = yaml.safe_load(f)

    context_size = model_params["context_size"]

    # load model weights
    ckpth_path = model_paths[args.model]["ckpt_path"]
    if not os.path.isabs(ckpth_path):
        ckpth_path = os.path.join(repo_root, ckpth_path)

    if os.path.exists(ckpth_path):
        print(f"Loading model from {ckpth_path}")
    else:
        raise FileNotFoundError(f"Model weights not found at {ckpth_path}")
    model = load_model(
        ckpth_path,
        model_params,
        device,
    )
    model = model.to(device)
    model.eval()

    num_diffusion_iters = model_params["num_diffusion_iters"]
    noise_scheduler = DDPMScheduler(
        num_train_timesteps=model_params["num_diffusion_iters"],
        beta_schedule='squaredcos_cap_v2',
        clip_sample=True,
        prediction_type='epsilon'
    )

    # ROS
    rospy.init_node("EXPLORATION", anonymous=False)
    rate = rospy.Rate(RATE)
    image_curr_msg = rospy.Subscriber(
        IMAGE_TOPIC, Image, callback_obs, queue_size=1)
    waypoint_pub = rospy.Publisher(
        WAYPOINT_TOPIC, Float32MultiArray, queue_size=1)  
    sampled_actions_pub = rospy.Publisher(SAMPLED_ACTIONS_TOPIC, Float32MultiArray, queue_size=1)

    print("Registered with master node. Waiting for image observations...")

    while not rospy.is_shutdown():
        # EXPLORATION MODE
        waypoint_msg = Float32MultiArray()
        if (
                len(context_queue) > model_params["context_size"]
            ):

            obs_images = transform_images(context_queue, model_params["image_size"], center_crop=False)
            obs_images = obs_images.to(device)
            fake_goal = torch.randn((1, 3, *model_params["image_size"])).to(device)
            mask = torch.ones(1).long().to(device) # ignore the goal

            # infer action
            with torch.no_grad():
                # encoder vision features
                obs_cond = model('vision_encoder', obs_img=obs_images, goal_img=fake_goal, input_goal_mask=mask)
                
                # (B, obs_horizon * obs_dim)
                if len(obs_cond.shape) == 2:
                    obs_cond = obs_cond.repeat(args.num_samples, 1)
                else:
                    obs_cond = obs_cond.repeat(args.num_samples, 1, 1)
                
                # initialize action from Gaussian noise
                noisy_action = torch.randn(
                    (args.num_samples, model_params["len_traj_pred"], 2), device=device)
                naction = noisy_action

                # init scheduler
                noise_scheduler.set_timesteps(num_diffusion_iters)

                start_time = time.time()
                for k in noise_scheduler.timesteps[:]:
                    # predict noise
                    noise_pred = model(
                        'noise_pred_net',
                        sample=naction,
                        timestep=k,
                        global_cond=obs_cond
                    )

                    # inverse diffusion step (remove noise)
                    naction = noise_scheduler.step(
                        model_output=noise_pred,
                        timestep=k,
                        sample=naction
                    ).prev_sample
                print("time elapsed:", time.time() - start_time)

            naction = to_numpy(get_action(naction))
            
            sampled_actions_msg = Float32MultiArray()
            sampled_actions_msg.data = np.concatenate((np.array([0]), naction.flatten()))
            sampled_actions_pub.publish(sampled_actions_msg)

            naction = naction[0] # change this based on heuristic

            chosen_waypoint = naction[args.waypoint]

            if model_params["normalize"]:
                chosen_waypoint *= (MAX_V / RATE)
            waypoint_msg.data = chosen_waypoint
            waypoint_pub.publish(waypoint_msg)
            print("Published waypoint")
        rate.sleep()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Code to run GNM DIFFUSION EXPLORATION on the locobot")
    parser.add_argument(
        "--model",
        "-m",
        default="nomad",
        type=str,
        help="model name (hint: check ../config/models.yaml) (default: nomad)",
    )
    parser.add_argument(
        "--waypoint",
        "-w",
        default=2, # close waypoints exihibit straight line motion (the middle waypoint is a good default)
        type=int,
        help=f"""index of the waypoint used for navigation (between 0 and 4 or 
        how many waypoints your model predicts) (default: 2)""",
    )
    parser.add_argument(
        "--num-samples",
        "-n",
        default=8,
        type=int,
        help=f"Number of actions sampled from the exploration model (default: 8)",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to model config YAML (default: <repo>/train/config/<model>.yaml)"
    )
    args = parser.parse_args()
    args = parser.parse_args()
    print(f"Using {device}")
    main(args)


