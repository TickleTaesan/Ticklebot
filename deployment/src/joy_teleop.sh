#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd "$DEPLOY_DIR/.." && pwd)"

# Create a new tmux session
session_name="teleop_locobot_$(date +%s)"
tmux new-session -d -s $session_name

# Split the window into two panes
tmux selectp -t 0    # select the first (0) pane
tmux splitw -v -p 50 # split it into two halves

# Run the roslaunch command in the first pane
tmux select-pane -t 0
tmux send-keys "roslaunch $SCRIPT_DIR/vint_locobot.launch config_file:=$DEPLOY_DIR/config/cmd_vel_mux.yaml" Enter

# Run the teleop.py script in the second pane
tmux select-pane -t 1
tmux send-keys "export PYTHONPATH=$REPO_ROOT:$REPO_ROOT/diffusion_policy:\$PYTHONPATH" Enter
tmux send-keys "if command -v conda >/dev/null 2>&1; then source \$(conda info --base)/etc/profile.d/conda.sh && conda activate vint_deployment; fi" Enter
tmux send-keys "python $SCRIPT_DIR/joy_teleop.py" Enter


# Attach to the tmux session
tmux -2 attach-session -t $session_name
