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
from typing import Any

from lerobot.teleoperators import Teleoperator

from .dual_gamepad_config import DualGamepadTeleop6DOFConfig
from .gamepad_6dof_utils import GamepadController6DOF

logger = logging.getLogger(__name__)


class DualGamepadTeleop6DOF(Teleoperator):
    """
    Dual arm teleoperation using a single gamepad for 6-DOF control.
    Modes: left, right, both, mirror
    """

    config_class = DualGamepadTeleop6DOFConfig
    name = "dual_gamepad_6dof"

    def __init__(self, config: DualGamepadTeleop6DOFConfig):
        super().__init__(config)
        self.config = config
        self.current_mode = config.default_mode
        self.previous_button_states: dict[int, bool] = {}
        self.gamepad: GamepadController6DOF | None = None

    @property
    def action_features(self) -> dict:
        base_features = {
            "linear_x.vel": 0,
            "linear_y.vel": 1,
            "linear_z.vel": 2,
            "angular_x.vel": 3,
            "angular_y.vel": 4,
            "angular_z.vel": 5,
        }
        if self.config.use_gripper:
            base_features["gripper.pos"] = 6

        dual_features: dict[str, int] = {}
        for arm in ("left", "right"):
            for key, idx in base_features.items():
                dual_features[f"{arm}_{key}"] = idx + (len(base_features) if arm == "right" else 0)

        total_features = len(base_features) * 2
        return {"dtype": "float32", "shape": (total_features,), "names": dual_features}

    @property
    def feedback_features(self) -> dict:
        return {}

    def connect(self) -> None:
        self.gamepad = GamepadController6DOF(
            x_step_size=self.config.linear_sensitivity,
            y_step_size=self.config.linear_sensitivity,
            z_step_size=self.config.linear_sensitivity,
            rot_step_size=self.config.angular_sensitivity,
            deadzone=self.config.deadzone,
        )
        self.gamepad.start()
        logger.info("Dual gamepad teleoperator connected")

    def get_action(self) -> dict[str, Any]:
        if self.gamepad is None:
            raise RuntimeError("Gamepad is not connected. Please call connect() first.")

        self.gamepad.update()
        self._update_control_mode()

        base_action = self._get_base_action()
        dual_action = self._generate_dual_action(base_action)
        return dual_action

    def _get_base_action(self) -> dict[str, float]:
        assert self.gamepad is not None
        dx, dy, dz, droll, dpitch, dyaw = self.gamepad.get_6dof_deltas()
        action = {
            "linear_x.vel": dx,
            "linear_y.vel": dy,
            "linear_z.vel": dz,
            "angular_x.vel": droll,
            "angular_y.vel": dpitch,
            "angular_z.vel": dyaw,
        }
        if self.config.use_gripper:
            action["gripper.pos"] = self.gamepad.gripper_command()
        return action

    def _update_control_mode(self) -> None:
        if not self.config.enable_mode_switching:
            return
        import pygame

        current_buttons: dict[int, bool] = {}
        if self.gamepad and self.gamepad.joystick:
            for i in range(self.gamepad.joystick.get_numbuttons()):
                current_buttons[i] = bool(self.gamepad.joystick.get_button(i))

        for button, pressed in current_buttons.items():
            was_pressed = self.previous_button_states.get(button, False)
            if pressed and not was_pressed:
                if button == 0:
                    self.current_mode = "left"
                elif button == 1:
                    self.current_mode = "right"
                elif button == 2:
                    self.current_mode = "mirror"
                elif button == 3:
                    self.current_mode = "both"
                elif button == 7:
                    self.current_mode = self.config.default_mode
        self.previous_button_states = current_buttons.copy()

    def _generate_dual_action(self, base_action: dict[str, float]) -> dict[str, Any]:
        dual_action: dict[str, Any] = {}
        if self.current_mode == "left":
            for key, value in base_action.items():
                dual_action[f"left_{key}"] = value
                dual_action[f"right_{key}"] = 0.0
        elif self.current_mode == "right":
            for key, value in base_action.items():
                dual_action[f"left_{key}"] = 0.0
                dual_action[f"right_{key}"] = value
        elif self.current_mode == "both":
            for key, value in base_action.items():
                dual_action[f"left_{key}"] = value
                dual_action[f"right_{key}"] = value
        elif self.current_mode == "mirror":
            for key, value in base_action.items():
                dual_action[f"left_{key}"] = value
                dual_action[f"right_{key}"] = self._mirror_value(key, value)
        else:
            for key, value in base_action.items():
                dual_action[f"left_{key}"] = value
                dual_action[f"right_{key}"] = value
        return dual_action

    def _mirror_value(self, key: str, value: float) -> float:
        if "linear_x" in key and self.config.mirror_x_axis:
            return -value
        if "linear_y" in key and self.config.mirror_y_axis:
            return -value
        if "linear_z" in key and self.config.mirror_z_axis:
            return -value
        if "angular_x" in key and self.config.mirror_x_axis:
            return -value
        if "angular_y" in key and self.config.mirror_y_axis:
            return -value
        if "angular_z" in key and self.config.mirror_z_axis:
            return -value
        return value

    def disconnect(self) -> None:
        if self.gamepad is not None:
            self.gamepad.stop()
            self.gamepad = None

    def is_connected(self) -> bool:
        return self.gamepad is not None

    def calibrate(self) -> None:
        pass

    def is_calibrated(self) -> bool:
        return True

    def configure(self) -> None:
        pass

    def send_feedback(self, feedback: dict) -> None:
        pass


