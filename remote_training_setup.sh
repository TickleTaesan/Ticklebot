#!/bin/bash

# NoMaD 모델 원격 학습 설정 스크립트

echo "Setting up NoMaD model training on remote RTX 3080 machine..."

# Check if CUDA is available
if ! command -v nvidia-smi &> /dev/null; then
    echo "Error: NVIDIA GPU not found or drivers not installed"
    exit 1
fi

# Check CUDA version
CUDA_VERSION=$(nvidia-smi | grep "CUDA Version" | awk '{print $9}' | cut -d'.' -f1-2)
echo "CUDA Version: $CUDA_VERSION"

# Check GPU memory
GPU_MEMORY=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -1)
echo "GPU Memory: ${GPU_MEMORY}MB"

if [ "$GPU_MEMORY" -lt 8000 ]; then
    echo "Warning: GPU memory is less than 8GB. Training might be limited."
fi

# Install PyTorch with CUDA support
echo "Installing PyTorch with CUDA support..."
pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Install additional dependencies for NoMaD training
echo "Installing NoMaD training dependencies..."
pip3 install \
    diffusers \
    transformers \
    accelerate \
    datasets \
    wandb \
    tensorboard \
    matplotlib \
    seaborn \
    tqdm \
    scipy \
    scikit-learn \
    opencv-python \
    pillow \
    numpy \
    pandas

# Verify PyTorch CUDA installation
echo "Verifying PyTorch CUDA installation..."
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
"

echo "Remote training setup completed!"
echo ""
echo "Next steps:"
echo "1. Prepare training data"
echo "2. Configure training parameters"
echo "3. Start training: python3 train/train.py" 