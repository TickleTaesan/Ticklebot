#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd "$DEPLOY_DIR/.." && pwd)"
BAG_ARG="$2"
if [ -n "$BAG_ARG" ] && [ ! -f "$BAG_ARG" ]; then
  if [ -f "$REPO_ROOT/processed_data/$BAG_ARG" ]; then
    BAG_ARG="$REPO_ROOT/processed_data/$BAG_ARG"
  elif [ -f "/root/nomad/processed_data/$BAG_ARG" ]; then
    BAG_ARG="/root/nomad/processed_data/$BAG_ARG"
  fi
fi
# Create a new tmux session
session_name="gnm_locobot_$(date +%s)"
tmux new-session -d -s $session_name

# Split the window into three panes
tmux selectp -t 0    # select the first (0) pane
tmux splitw -v -p 50 # split it into two halves
tmux selectp -t 0    # go back to the first pane
tmux splitw -h -p 50 # split it into two halves

# Run roscore in the first pane
tmux select-pane -t 0
tmux send-keys "export PYTHONPATH=$REPO_ROOT:$REPO_ROOT/diffusion_policy:\$PYTHONPATH" Enter
tmux send-keys "if command -v conda >/dev/null 2>&1; then source \$(conda info --base)/etc/profile.d/conda.sh && conda activate vint_deployment; fi" Enter
tmux send-keys "python $SCRIPT_DIR/create_topomap.py --dt 1 --dir $1" Enter


# Run the create_topoplan.py script with command line args in the second pane
tmux select-pane -t 1
tmux send-keys "conda activate gnm_deployment" Enter
tmux send-keys "python create_topomap.py --dt 1 --dir $1" Enter

# Change the directory to ../topomaps/bags and run the rosbag play command in the third pane
tmux select-pane -t 2
#tmux send-keys "mkdir -p ../topomaps/bags" Enter
#tmux send-keys "cd ../topomaps/bags" Enter
#tmux send-keys "rosbag play -r 1.5 $2" # feel free to change the playback rate to change the edge length in the graph
tmux send-keys "rosbag play -r 1.5 \"$BAG_ARG\"" Enter

# Attach to the tmux session
tmux -2 attach-session -t $session_name
