#!/usr/bin/env python

# Copyright 2024 The HuggingFace Inc. team. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from dataclasses import dataclass, field

from lerobot.robots import RobotConfig

from .config_ros import ROS2Config, ROS2InterfaceConfig, ActionType, GripperActionType


@RobotConfig.register_subclass("dual_so100_ros")
@dataclass
class DualSO100RosConfig(ROS2Config):
    """Configuration for dual SO-100 robots using ROS2 namespaces."""

    action_type: ActionType = ActionType.CARTESIAN_VELOCITY

    # Left arm ROS2 interface configuration
    left_arm_interface: ROS2InterfaceConfig = field(
        default_factory=lambda: ROS2InterfaceConfig(
            namespace="left_arm",
            base_link="base",
            arm_joint_names=["1", "2", "3", "4", "5"],
            gripper_joint_name="6",
            gripper_open_position=0.0,
            gripper_close_position=1.0,
            max_linear_velocity=0.05,
            max_angular_velocity=0.25,
            gripper_action_type=GripperActionType.TRAJECTORY,
        )
    )

    # Right arm ROS2 interface configuration
    right_arm_interface: ROS2InterfaceConfig = field(
        default_factory=lambda: ROS2InterfaceConfig(
            namespace="right_arm",
            base_link="base",
            arm_joint_names=["1", "2", "3", "4", "5"],
            gripper_joint_name="6",
            gripper_open_position=0.0,
            gripper_close_position=1.0,
            max_linear_velocity=0.05,
            max_angular_velocity=0.25,
            gripper_action_type=GripperActionType.TRAJECTORY,
        )
    )

    # Control mode options (used by teleop)
    enable_mirror_mode: bool = True
    enable_sync_mode: bool = True
    default_control_mode: str = "both"  # "left", "right", "both", "mirror"


