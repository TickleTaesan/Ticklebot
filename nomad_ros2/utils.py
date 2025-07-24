#!/usr/bin/env python3

import os
import sys
import io
import matplotlib.pyplot as plt

# ROS2
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2

# pytorch
import torch
import torch.nn as nn
from torchvision import transforms
import torchvision.transforms.functional as TF

import numpy as np
from PIL import Image as PILImage
from typing import List, Tuple, Dict, Optional

# models
from vint_train.models.gnm.gnm import GNM
from vint_train.models.vint.vint import ViNT
from vint_train.models.vint.vit import ViT
from vint_train.models.nomad.nomad import NoMaD, DenseNetwork
from vint_train.models.nomad.nomad_vint import NoMaD_ViNT, replace_bn_with_gn
from diffusion_policy.model.diffusion.conditional_unet1d import ConditionalUnet1D
from vint_train.data.data_utils import IMAGE_ASPECT_RATIO


def load_model(
    model_path: str,
    config: dict,
    device: torch.device = torch.device("cpu"),
) -> nn.Module:
    """Load a model from a checkpoint file (works with models trained on multiple GPUs)"""
    model_type = config["model_type"]
    
    if model_type == "gnm":
        model = GNM(
            config["context_size"],
            config["len_traj_pred"],
            config["learn_angle"],
            config["obs_encoding_size"],
            config["goal_encoding_size"],
        )
    elif model_type == "vint":
        model = ViNT(
            context_size=config["context_size"],
            len_traj_pred=config["len_traj_pred"],
            learn_angle=config["learn_angle"],
            obs_encoder=config["obs_encoder"],
            obs_encoding_size=config["obs_encoding_size"],
            late_fusion=config["late_fusion"],
            mha_num_attention_heads=config["mha_num_attention_heads"],
            mha_num_attention_layers=config["mha_num_attention_layers"],
            mha_ff_dim_factor=config["mha_ff_dim_factor"],
        )
    elif config["model_type"] == "nomad":
        if config["vision_encoder"] == "nomad_vint":
            vision_encoder = NoMaD_ViNT(
                obs_encoding_size=config["encoding_size"],
                context_size=config["context_size"],
                mha_num_attention_heads=config["mha_num_attention_heads"],
                mha_num_attention_layers=config["mha_num_attention_layers"],
                mha_ff_dim_factor=config["mha_ff_dim_factor"],
            )
            vision_encoder = replace_bn_with_gn(vision_encoder)
        elif config["vision_encoder"] == "vit": 
            vision_encoder = ViT(
                obs_encoding_size=config["encoding_size"],
                context_size=config["context_size"],
                image_size=config["image_size"],
                patch_size=config["patch_size"],
                mha_num_attention_heads=config["mha_num_attention_heads"],
                mha_num_attention_layers=config["mha_num_attention_layers"],
            )
            vision_encoder = replace_bn_with_gn(vision_encoder)
        else: 
            raise ValueError(f"Vision encoder {config['vision_encoder']} not supported")
        
        noise_pred_net = ConditionalUnet1D(
                input_dim=2,
                global_cond_dim=config["encoding_size"],
                down_dims=config["down_dims"],
                cond_predict_scale=config["cond_predict_scale"],
            )
        dist_pred_network = DenseNetwork(embedding_dim=config["encoding_size"])
        
        model = NoMaD(
            vision_encoder=vision_encoder,
            noise_pred_net=noise_pred_net,
            dist_pred_net=dist_pred_network,
        )
    else:
        raise ValueError(f"Invalid model type: {model_type}")
    
    checkpoint = torch.load(model_path, map_location=device)
    if model_type == "nomad":
        state_dict = checkpoint
        model.load_state_dict(state_dict, strict=False)
    else:
        loaded_model = checkpoint["model"]
        try:
            state_dict = loaded_model.module.state_dict()
            model.load_state_dict(state_dict, strict=False)
        except AttributeError as e:
            state_dict = loaded_model.state_dict()
            model.load_state_dict(state_dict, strict=False)
    model.to(device)
    return model


def load_trained_nomad_model(model_path: str, device: str = 'cuda') -> tuple:
    """
    학습된 NoMaD 모델을 로드합니다.
    
    Args:
        model_path: 학습된 모델 체크포인트 경로
        device: 사용할 디바이스 ('cuda' 또는 'cpu')
    
    Returns:
        tuple: (model, noise_scheduler)
    """
    import torch
    from vint_train.models.nomad.nomad_vint import NoMaD_ViNT
    from diffusers.schedulers.scheduling_ddpm import DDPMScheduler
    
    # 모델 초기화
    model = NoMaD_ViNT(
        obs_encoder='efficientnet-b0',
        encoding_size=256,
        mha_num_attention_heads=4,
        mha_num_attention_layers=4,
        mha_ff_dim_factor=4,
        down_dims=[64, 128, 256],
        len_traj_pred=8,
        learn_angle=False
    )
    
    # 체크포인트 로드
    checkpoint = torch.load(model_path, map_location=device)
    
    # 모델 가중치 로드
    if 'model_state_dict' in checkpoint:
        model.load_state_dict(checkpoint['model_state_dict'])
    else:
        model.load_state_dict(checkpoint)
    
    model.to(device)
    model.eval()
    
    # Noise scheduler 초기화
    noise_scheduler = DDPMScheduler(
        num_train_timesteps=1000,
        beta_start=0.0001,
        beta_end=0.02,
        beta_schedule="linear"
    )
    
    return model, noise_scheduler

def nomad_inference_with_trained_model(
    model, 
    noise_scheduler, 
    image: np.ndarray, 
    goal_image: np.ndarray,
    num_samples: int = 8,
    device: str = 'cuda'
) -> np.ndarray:
    """
    학습된 NoMaD 모델로 추론을 수행합니다.
    
    Args:
        model: 학습된 NoMaD 모델
        noise_scheduler: Noise scheduler
        image: 현재 이미지
        goal_image: 목표 이미지
        num_samples: 샘플링할 액션 수
        device: 사용할 디바이스
    
    Returns:
        np.ndarray: 예측된 액션들
    """
    import torch
    
    # 이미지 전처리
    transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])
    
    # 이미지를 텐서로 변환
    obs_tensor = transform(image).unsqueeze(0).to(device)
    goal_tensor = transform(goal_image).unsqueeze(0).to(device)
    
    # 배치 차원 확장 (num_samples만큼)
    obs_tensor = obs_tensor.repeat(num_samples, 1, 1, 1)
    goal_tensor = goal_tensor.repeat(num_samples, 1, 1, 1)
    
    with torch.no_grad():
        # 모델 추론
        predicted_actions = model(
            obs=obs_tensor,
            goal=goal_tensor,
            noise_scheduler=noise_scheduler,
            num_inference_steps=10
        )
    
    # CPU로 이동하고 numpy로 변환
    predicted_actions = predicted_actions.cpu().numpy()
    
    return predicted_actions


def msg_to_pil(msg: Image) -> PILImage.Image:
    """Convert ROS2 Image message to PIL Image"""
    # Use cv_bridge for better compatibility
    bridge = CvBridge()
    try:
        cv_image = bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        # Convert BGR to RGB
        cv_image_rgb = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)
        pil_image = PILImage.fromarray(cv_image_rgb)
        return pil_image
    except Exception as e:
        # Fallback to original method
        img = np.frombuffer(msg.data, dtype=np.uint8).reshape(
            msg.height, msg.width, -1)
        pil_image = PILImage.fromarray(img)
        return pil_image


def pil_to_msg(pil_img: PILImage.Image, encoding="bgr8") -> Image:
    """Convert PIL Image to ROS2 Image message"""
    # Use cv_bridge for better compatibility
    bridge = CvBridge()
    img = np.asarray(pil_img)
    # Convert RGB to BGR for OpenCV
    if len(img.shape) == 3:
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    ros_image = bridge.cv2_to_imgmsg(img, encoding=encoding)
    return ros_image


def to_numpy(tensor):
    """Convert PyTorch tensor to numpy array"""
    return tensor.cpu().detach().numpy()


def transform_images(pil_imgs: List[PILImage.Image], image_size: List[int], center_crop: bool = False) -> torch.Tensor:
    """Transforms a list of PIL image to a torch tensor."""
    transform_type = transforms.Compose(
        [
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[
                                    0.229, 0.224, 0.225]),
        ]
    )
    if type(pil_imgs) != list:
        pil_imgs = [pil_imgs]
    transf_imgs = []
    for pil_img in pil_imgs:
        w, h = pil_img.size
        if center_crop:
            if w > h:
                pil_img = TF.center_crop(pil_img, (h, int(h * IMAGE_ASPECT_RATIO)))  # crop to the right ratio
            else:
                pil_img = TF.center_crop(pil_img, (int(w / IMAGE_ASPECT_RATIO), w))
        pil_img = pil_img.resize(image_size) 
        transf_img = transform_type(pil_img)
        transf_img = torch.unsqueeze(transf_img, 0)
        transf_imgs.append(transf_img)
    return torch.cat(transf_imgs, dim=1)


def clip_angle(angle):
    """Clip angle between -pi and pi"""
    return np.mod(angle + np.pi, 2 * np.pi) - np.pi


def get_ros2_parameter(node, param_name, default_value):
    """Get ROS2 parameter with fallback to default value"""
    try:
        return node.get_parameter(param_name).value
    except:
        return default_value


def setup_ros2_qos(reliability='best_effort', history='keep_last', depth=1):
    """Setup ROS2 QoS profile"""
    from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
    
    reliability_map = {
        'best_effort': ReliabilityPolicy.BEST_EFFORT,
        'reliable': ReliabilityPolicy.RELIABLE
    }
    
    history_map = {
        'keep_last': HistoryPolicy.KEEP_LAST,
        'keep_all': HistoryPolicy.KEEP_ALL
    }
    
    return QoSProfile(
        reliability=reliability_map.get(reliability, ReliabilityPolicy.BEST_EFFORT),
        history=history_map.get(history, HistoryPolicy.KEEP_LAST),
        depth=depth
    ) 