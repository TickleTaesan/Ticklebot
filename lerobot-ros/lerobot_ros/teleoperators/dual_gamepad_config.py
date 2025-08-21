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

from dataclasses import dataclass

from lerobot.teleoperators import TeleoperatorConfig


@TeleoperatorConfig.register_subclass("dual_gamepad_6dof")
@dataclass
class DualGamepadTeleop6DOFConfig(TeleoperatorConfig):
    """Configuration for dual arm gamepad teleoperation."""

    use_gripper: bool = True

    # Control mode
    default_mode: str = "both"  # "left", "right", "both", "mirror"
    enable_mode_switching: bool = True

    # Sensitivity
    linear_sensitivity: float = 0.05  # m/s
    angular_sensitivity: float = 0.25  # rad/s
    gripper_sensitivity: float = 10.0

    # Deadzone
    deadzone: float = 0.1

    # Mirror mode axes
    mirror_x_axis: bool = True
    mirror_y_axis: bool = False
    mirror_z_axis: bool = False


