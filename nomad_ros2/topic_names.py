# ROS2 Topic Names for Nomad

# Image topics
IMAGE_TOPIC = "/usb_cam/image_raw"
IMAGE_COMPRESSED_TOPIC = "/usb_cam/image_raw/compressed"

# Control topics
WAYPOINT_TOPIC = "/waypoint"
SAMPLED_ACTIONS_TOPIC = "/sampled_actions"
CMD_VEL_TOPIC = "/cmd_vel"

# Joystick topics
JOY_TOPIC = "/joy"

# Navigation topics
GOAL_REACHED_TOPIC = "/topoplan/reached_goal"

# Robot-specific topics (configurable)
ROBOT_CMD_VEL_TOPIC = "/cmd_vel"  # Default, can be overridden in config
ROBOT_ODOM_TOPIC = "/odom"        # Default, can be overridden in config 