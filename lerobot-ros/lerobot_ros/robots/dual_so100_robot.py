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

import logging
from functools import cached_property
from typing import Any

from lerobot.errors import DeviceNotConnectedError
from lerobot.robots import Robot

from .config_ros import ActionType
from .dual_so100_config import DualSO100RosConfig
from .ros_interface import ROS2Interface

logger = logging.getLogger(__name__)


class DualSO100RosRobot(Robot):
    """
    Dual SO-100 robots controlled via ROS2 namespaces.

    This class manages two SO-100 robots using separate ROS2 namespaces:
    - left_arm: Controls the left SO-100 robot
    - right_arm: Controls the right SO-100 robot

    Each robot can be controlled independently or in coordination.
    """

    config_class = DualSO100RosConfig
    name = "dual_so100_ros"

    def __init__(self, config: DualSO100RosConfig):
        super().__init__(config)
        self.config = config

        # Create separate ROS2 interfaces for each arm
        self.left_arm = ROS2Interface(config.left_arm_interface, config.action_type)
        self.right_arm = ROS2Interface(config.right_arm_interface, config.action_type)

    @cached_property
    def observation_features(self) -> dict[str, type | tuple]:
        left_features = {f"left_{k}": v for k, v in self._get_arm_features().items()}
        right_features = {f"right_{k}": v for k, v in self._get_arm_features().items()}
        return {**left_features, **right_features}

    @cached_property
    def action_features(self) -> dict[str, type]:
        if self.config.action_type == ActionType.CARTESIAN_VELOCITY:
            arm_features = {
                "linear_x.vel": float,
                "linear_y.vel": float,
                "linear_z.vel": float,
                "angular_x.vel": float,
                "angular_y.vel": float,
                "angular_z.vel": float,
                "gripper.pos": float,
            }
        else:
            arm_features = {f"{joint}.pos": float for joint in self.config.left_arm_interface.arm_joint_names}
            arm_features["gripper.pos"] = float

        left_features = {f"left_{k}": v for k, v in arm_features.items()}
        right_features = {f"right_{k}": v for k, v in arm_features.items()}
        return {**left_features, **right_features}

    def _get_arm_features(self) -> dict[str, type]:
        if self.config.action_type == ActionType.CARTESIAN_VELOCITY:
            return {
                "linear_x.vel": float,
                "linear_y.vel": float,
                "linear_z.vel": float,
                "angular_x.vel": float,
                "angular_y.vel": float,
                "angular_z.vel": float,
                "gripper.pos": float,
            }
        else:
            features = {f"{joint}.pos": float for joint in self.config.left_arm_interface.arm_joint_names}
            features["gripper.pos"] = float
            return features

    @property
    def is_connected(self) -> bool:
        return self.left_arm.is_connected and self.right_arm.is_connected

    def connect(self, calibrate: bool = True) -> None:
        logger.info("Connecting to dual SO-100 robots...")
        self.left_arm.connect()
        self.right_arm.connect()
        logger.info("Dual SO-100 robots connected successfully")

    def get_observation(self) -> dict[str, Any]:
        if not self.is_connected:
            raise DeviceNotConnectedError(f"{self} is not connected.")

        observation: dict[str, Any] = {}

        left_obs = self._get_arm_observation(self.left_arm)
        observation.update({f"left_{k}": v for k, v in left_obs.items()})

        right_obs = self._get_arm_observation(self.right_arm)
        observation.update({f"right_{k}": v for k, v in right_obs.items()})

        return observation

    def _get_arm_observation(self, arm_interface: ROS2Interface) -> dict[str, Any]:
        if self.config.action_type == ActionType.CARTESIAN_VELOCITY:
            return {
                "linear_x.vel": 0.0,
                "linear_y.vel": 0.0,
                "linear_z.vel": 0.0,
                "angular_x.vel": 0.0,
                "angular_y.vel": 0.0,
                "angular_z.vel": 0.0,
                "gripper.pos": 0.0,
            }
        else:
            joint_state = arm_interface.joint_state
            if joint_state is None:
                obs = {f"{joint}.pos": 0.0 for joint in self.config.left_arm_interface.arm_joint_names}
                obs["gripper.pos"] = 0.0
                return obs

            obs = {}
            for joint in self.config.left_arm_interface.arm_joint_names:
                obs[f"{joint}.pos"] = joint_state["position"].get(joint, 0.0)
            obs["gripper.pos"] = joint_state["position"].get(
                self.config.left_arm_interface.gripper_joint_name, 0.0
            )
            return obs

    def send_action(self, action: dict[str, Any]) -> dict[str, Any]:
        if not self.is_connected:
            raise DeviceNotConnectedError(f"{self} is not connected.")

        left_action = self._extract_arm_action(action, "left")
        right_action = self._extract_arm_action(action, "right")

        if left_action:
            self._send_arm_action(self.left_arm, left_action)
        if right_action:
            self._send_arm_action(self.right_arm, right_action)

        return action

    def _extract_arm_action(self, action: dict[str, Any], arm: str) -> dict[str, Any]:
        prefix = f"{arm}_"
        arm_action: dict[str, Any] = {}
        for key, value in action.items():
            if key.startswith(prefix):
                clean_key = key[len(prefix) :]
                arm_action[clean_key] = value
        return arm_action

    def _send_arm_action(self, arm_interface: ROS2Interface, action: dict[str, Any]) -> None:
        if self.config.action_type == ActionType.CARTESIAN_VELOCITY:
            linear_vel = (
                action.get("linear_x.vel", 0.0),
                action.get("linear_y.vel", 0.0),
                action.get("linear_z.vel", 0.0),
            )
            angular_vel = (
                action.get("angular_x.vel", 0.0),
                action.get("angular_y.vel", 0.0),
                action.get("angular_z.vel", 0.0),
            )
            arm_interface.servo(linear=linear_vel, angular=angular_vel)

            gripper_pos = action.get("gripper.pos", 0.0)
            arm_interface.send_gripper_command(gripper_pos)
        else:
            joint_positions = [
                action.get(f"{joint}.pos", 0.0) for joint in self.config.left_arm_interface.arm_joint_names
            ]
            arm_interface.send_joint_position_command(joint_positions)

            gripper_pos = action.get("gripper.pos", 0.0)
            arm_interface.send_gripper_command(gripper_pos)

    def disconnect(self) -> None:
        if self.left_arm.is_connected:
            self.left_arm.disconnect()
        if self.right_arm.is_connected:
            self.right_arm.disconnect()
        logger.info("Dual SO-100 robots disconnected")


