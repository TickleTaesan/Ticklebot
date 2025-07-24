#!/bin/bash

# NoMaD 모델 학습 실행 스크립트

echo "Starting NoMaD model training..."

# Check if CUDA is available
if ! command -v nvidia-smi &> /dev/null; then
    echo "Error: NVIDIA GPU not found!"
    exit 1
fi

# Check GPU memory
GPU_MEMORY=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -1)
echo "GPU Memory: ${GPU_MEMORY}MB"

# Activate conda environment
echo "Activating conda environment..."
source ~/miniconda3/etc/profile.d/conda.sh
conda activate nomad_train

# Check if environment is activated
if [ "$CONDA_DEFAULT_ENV" != "nomad_train" ]; then
    echo "Error: Failed to activate nomad_train environment"
    exit 1
fi

echo "Conda environment activated: $CONDA_DEFAULT_ENV"

# Verify PyTorch CUDA
echo "Verifying PyTorch CUDA..."
python3 -c "
import torch
print(f'PyTorch version: {torch.__version__}')
print(f'CUDA available: {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'CUDA version: {torch.version.cuda}')
    print(f'GPU count: {torch.cuda.device_count()}')
    print(f'Current GPU: {torch.cuda.get_device_name(0)}')
    print(f'GPU memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB')
else:
    print('CUDA not available!')
    exit(1)
"

if [ $? -ne 0 ]; then
    echo "Error: PyTorch CUDA verification failed"
    exit 1
fi

# Change to train directory
cd train

# Check if config file exists
if [ ! -f "config/nomad_simple.yaml" ]; then
    echo "Error: config/nomad_simple.yaml not found"
    exit 1
fi

# Check if data paths are set correctly
echo "Checking data paths in config..."
python3 -c "
import yaml
with open('config/nomad_simple.yaml', 'r') as f:
    config = yaml.safe_load(f)
    
for dataset_name, dataset_config in config['datasets'].items():
    data_folder = dataset_config['data_folder']
    train_path = dataset_config['train']
    test_path = dataset_config['test']
    
    print(f'Dataset: {dataset_name}')
    print(f'  Data folder: {data_folder}')
    print(f'  Train path: {train_path}')
    print(f'  Test path: {test_path}')
    
    if '/path/to/your/' in data_folder:
        print('  ⚠️  WARNING: Data paths need to be updated!')
        exit(1)
    else:
        print('  ✓ Data paths look correct')
"

if [ $? -ne 0 ]; then
    echo ""
    echo "Please update the data paths in config/nomad_simple.yaml"
    echo "Example:"
    echo "  data_folder: /home/username/nomad_dataset/recon"
    echo "  train: /home/username/data_splits/recon/train/"
    echo "  test: /home/username/data_splits/recon/test/"
    exit 1
fi

# Start training
echo ""
echo "Starting NoMaD training..."
echo "Config: config/nomad_simple.yaml"
echo "Logs will be saved to: logs/nomad_simple/"

# Run training with nohup for background execution
nohup python3 train.py --config config/nomad_simple.yaml > training.log 2>&1 &

# Get the process ID
TRAINING_PID=$!
echo "Training started with PID: $TRAINING_PID"
echo "Log file: training.log"

# Show how to monitor training
echo ""
echo "To monitor training progress:"
echo "1. Check logs: tail -f training.log"
echo "2. Check GPU usage: watch -n 1 nvidia-smi"
echo "3. Check process: ps aux | grep train.py"
echo ""
echo "To stop training: kill $TRAINING_PID"
echo ""
echo "Training is running in background..." 