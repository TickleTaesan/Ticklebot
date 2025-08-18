from lerobot import record as lr_rec
from lerobot.robots import Robot, RobotConfig
from lerobot.teleoperators import Teleoperator, TeleoperatorConfig

from lerobot_ros import GamepadTeleop6DOF, GamepadTeleop6DOFConfig, ROS2Config, ROS2Robot

# Override the default robot and teleoperator creation functions to use
# ROS2-specific implementations.
# This allows us to create our own robots and teleoperators.
orig_make_robot_from_config = lr_rec.make_robot_from_config
orig_make_teleoperator_from_config = lr_rec.make_teleoperator_from_config


def make_my_robot_from_config(config: RobotConfig) -> Robot:
    """Create a robot instance based on the provided configuration."""
    if not isinstance(config, ROS2Config):
        return orig_make_robot_from_config(config)

    return ROS2Robot(config)


def make_my_teleoperator_from_config(config: TeleoperatorConfig) -> Teleoperator:
    """Create a teleoperator instance based on the provided configuration."""
    if not isinstance(config, GamepadTeleop6DOFConfig):
        return orig_make_teleoperator_from_config(config)

    return GamepadTeleop6DOF(config)


# Replace the default creation function with our ROS2-specific ones
lr_rec.make_robot_from_config = make_my_robot_from_config
lr_rec.make_teleoperator_from_config = make_my_teleoperator_from_config


if __name__ == "__main__":
    lr_rec.record()  # type: ignore
