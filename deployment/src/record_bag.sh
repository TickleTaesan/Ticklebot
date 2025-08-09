#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd "$DEPLOY_DIR/.." && pwd)"

# Create a new tmux session
session_name="record_bag_$(date +%s)"
tmux new-session -d -s $session_name

# Split the window into three panes
tmux selectp -t 0    # select the first (0) pane
tmux splitw -v -p 50 # split it into two halves
tmux selectp -t 0    # go back to the first pane
tmux splitw -h -p 50 # split it into two halves

# Run the roslaunch command in the first pane
tmux select-pane -t 0
tmux send-keys "roslaunch $SCRIPT_DIR/vint_locobot.launch config_file:=$DEPLOY_DIR/config/cmd_vel_mux.yaml" Enter

# Run the teleop.py script in the second pane
tmux select-pane -t 1
tmux send-keys "export PYTHONPATH=$REPO_ROOT:$REPO_ROOT/diffusion_policy:\$PYTHONPATH" Enter
tmux send-keys "if command -v conda >/dev/null 2>&1; then source \$(conda info --base)/etc/profile.d/conda.sh && conda activate vint_deployment; fi" Enter
tmux send-keys "python $SCRIPT_DIR/joy_teleop.py" Enter


# Change the directory to ../topomaps/bags and run the rosbag record command in the third pane
tmux select-pane -t 2
tmux send-keys "cd ../topomaps/bags" Enter
tmux send-keys "rosbag record /usb_cam/image_raw -o $1" # change topic if necessary

# Attach to the tmux session
tmux -2 attach-session -t $session_name
