from lerobot import replay as lr_rec
from lerobot.robots import Robot, RobotConfig

from lerobot_ros import (
    ROS2Config,
    ROS2Robot,
    DualSO100RosConfig,
    DualSO100RosRobot,
)

# Override the default robot creation functions to use ROS2-specific
#  implementations. This allows us to create our own robots.
orig_make_robot_from_config = lr_rec.make_robot_from_config


def make_my_robot_from_config(config: RobotConfig) -> Robot:
    """Create a robot instance based on the provided configuration."""
    if isinstance(config, DualSO100RosConfig):
        return DualSO100RosRobot(config)
    if isinstance(config, ROS2Config):
        return ROS2Robot(config)
    return orig_make_robot_from_config(config)


# Replace the default creation function with our ROS2-specific ones
lr_rec.make_robot_from_config = make_my_robot_from_config


if __name__ == "__main__":
    lr_rec.replay()  # type: ignore
