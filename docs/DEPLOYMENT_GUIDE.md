# Enhanced CodeAgent Integration - Deployment Guide

This guide provides comprehensive instructions for deploying the Enhanced CodeAgent Integration system in various environments.

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Quick Start](#quick-start)
3. [Manual Installation](#manual-installation)
4. [Docker Deployment](#docker-deployment)
5. [Configuration](#configuration)
6. [Performance Optimization](#performance-optimization)
7. [Troubleshooting](#troubleshooting)
8. [Monitoring](#monitoring)

## System Requirements

### Minimum Requirements (CPU-only)
- **OS**: Linux, macOS, or Windows with WSL2
- **CPU**: 4+ cores
- **RAM**: 8GB (16GB recommended)
- **Storage**: 20GB free space
- **Python**: 3.9+
- **Network**: Internet connection for model downloads

### Recommended Requirements (GPU)
- **GPU**: NVIDIA GPU with 8GB+ VRAM
- **CUDA**: 11.8 or 12.1
- **RAM**: 16GB+ system RAM
- **Storage**: 50GB+ free space (for models and cache)

### Optimal Requirements (High Performance)
- **GPU**: NVIDIA GPU with 24GB+ VRAM (RTX 4090, A100, etc.)
- **RAM**: 32GB+ system RAM
- **Storage**: 100GB+ NVMe SSD
- **Network**: High-speed internet for model downloads

## Quick Start

### 1. Clone and Setup
```bash
git clone <repository-url>
cd enhanced-codeagent-integration

# Run system detection
python3 scripts/detect_system.py

# Install dependencies
./scripts/auto_install.sh

# Start services
./scripts/start.sh
```

### 2. Access the Interface
- **Web Interface**: http://localhost:12000
- **API Documentation**: http://localhost:12000/docs
- **Health Check**: http://localhost:12000/health

## Manual Installation

### 1. System Detection
```bash
# Detect system capabilities and generate configuration
python3 scripts/detect_system.py
```

This will create:
- `config/system_info.json` - System capabilities
- `config/deployment_config.json` - Deployment configuration
- `config/.env` - Environment variables

### 2. Install Dependencies

#### For GPU Systems:
```bash
# Install PyTorch with CUDA support
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Install vLLM
pip install vllm

# Install other dependencies
pip install -r requirements.txt
```

#### For CPU Systems:
```bash
# Install CPU-optimized PyTorch
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# Install vLLM (CPU version)
pip install vllm

# Install other dependencies
pip install -r requirements.txt
```

### 3. Start Services Manually

#### Start vLLM Server:
```bash
# For GPU systems
python -m vllm.entrypoints.openai.api_server \
    --model deepseek-ai/DeepSeek-R1-Distill-Qwen-7B \
    --host 0.0.0.0 \
    --port 8000 \
    --tensor-parallel-size 1 \
    --gpu-memory-utilization 0.8 \
    --trust-remote-code

# For CPU systems
python -m vllm.entrypoints.openai.api_server \
    --model deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B \
    --host 0.0.0.0 \
    --port 8000 \
    --device cpu \
    --trust-remote-code
```

#### Start API Server:
```bash
cd src/api
python main.py
```

## Docker Deployment

### 1. Using Docker Compose (Recommended)

#### For GPU Systems:
```bash
# Copy environment template
cp config/.env.example config/.env

# Edit configuration as needed
nano config/.env

# Start GPU deployment
docker-compose --profile gpu up -d
```

#### For CPU Systems:
```bash
# Start CPU deployment
docker-compose --profile cpu up -d
```

### 2. Manual Docker Build
```bash
# Build the image
docker build -f docker/Dockerfile -t enhanced-codeagent .

# Run the container
docker run -d \
    --name enhanced-codeagent \
    -p 8000:8000 \
    -p 12000:12000 \
    -v $(pwd)/workspace:/app/workspace \
    -v $(pwd)/logs:/app/logs \
    enhanced-codeagent
```

### 3. GPU Docker Deployment
```bash
# Ensure NVIDIA Docker runtime is installed
docker run --rm --gpus all nvidia/cuda:11.8-base-ubuntu20.04 nvidia-smi

# Run with GPU support
docker run -d \
    --name enhanced-codeagent-gpu \
    --gpus all \
    -p 8000:8000 \
    -p 12000:12000 \
    -v $(pwd)/workspace:/app/workspace \
    enhanced-codeagent
```

## Configuration

### Environment Variables

Key configuration options in `config/.env`:

```bash
# Deployment Configuration
DEPLOYMENT_TYPE=cpu|gpu_low|gpu_standard|gpu_high
PERFORMANCE_TIER=minimal|standard|high

# Model Configuration
DEEPSEEK_MODEL=deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B
MAX_MODEL_LENGTH=4096
BATCH_SIZE=2

# Server Configuration
VLLM_HOST=0.0.0.0
VLLM_PORT=8000
MAX_CONCURRENT_REQUESTS=2

# GPU Configuration (if applicable)
ENABLE_GPU=true
TENSOR_PARALLEL_SIZE=1
GPU_MEMORY_UTILIZATION=0.8

# CPU Configuration (if applicable)
CPU_THREADS=2
```

### Model Selection by System

| System Type | Recommended Model | Context Length | Performance |
|-------------|------------------|----------------|-------------|
| CPU (8GB RAM) | DeepSeek-R1-Distill-Qwen-1.5B | 4K | Basic |
| CPU (16GB+ RAM) | DeepSeek-R1-Distill-Qwen-7B | 8K | Good |
| GPU (8GB VRAM) | DeepSeek-R1-Distill-Qwen-7B | 8K | Good |
| GPU (16GB+ VRAM) | DeepSeek-R1-Distill-Qwen-14B | 16K | Excellent |
| GPU (24GB+ VRAM) | DeepSeek-R1-Distill-Qwen-32B | 32K | Outstanding |

## Performance Optimization

### 1. Model Optimization

#### Quantization (for limited resources):
```bash
# Add to vLLM command
--quantization awq  # For GPU systems with limited VRAM
--quantization gptq # For CPU systems with limited RAM
```

#### Memory Management:
```bash
# GPU memory optimization
--gpu-memory-utilization 0.7  # Reduce if running other GPU tasks
--max-model-len 8192          # Reduce context length if needed

# CPU optimization
export OMP_NUM_THREADS=4      # Set based on CPU cores
--max-num-seqs 2              # Limit concurrent requests
```

### 2. System Optimization

#### For CPU Systems:
```bash
# Set CPU affinity
taskset -c 0-3 python -m vllm.entrypoints.openai.api_server ...

# Optimize memory allocation
export MALLOC_ARENA_MAX=4
```

#### For GPU Systems:
```bash
# Set GPU memory growth
export CUDA_MEMORY_FRACTION=0.8

# Enable mixed precision
--dtype float16  # or bfloat16 for newer GPUs
```

### 3. Network Optimization
```bash
# Increase connection limits
ulimit -n 65536

# Optimize TCP settings
echo 'net.core.somaxconn = 65536' >> /etc/sysctl.conf
```

## Troubleshooting

### Common Issues

#### 1. vLLM Server Won't Start
```bash
# Check logs
tail -f logs/vllm.log

# Common solutions:
# - Reduce max_model_len
# - Enable quantization
# - Check GPU memory usage: nvidia-smi
# - Verify model exists: huggingface-cli download model-name
```

#### 2. Out of Memory Errors
```bash
# For GPU:
--gpu-memory-utilization 0.6  # Reduce GPU memory usage
--max-model-len 4096          # Reduce context length

# For CPU:
--max-num-seqs 1              # Reduce concurrent requests
export OMP_NUM_THREADS=2      # Reduce CPU threads
```

#### 3. Slow Performance
```bash
# Check system resources
htop                          # CPU usage
nvidia-smi                    # GPU usage (if applicable)
iotop                         # Disk I/O

# Optimization:
# - Use SSD storage for models
# - Increase batch size if memory allows
# - Use quantization for faster inference
```

#### 4. Model Download Issues
```bash
# Set HuggingFace cache directory
export HF_HOME=/path/to/large/storage

# Download manually
huggingface-cli download deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B

# Use mirror (if needed)
export HF_ENDPOINT=https://hf-mirror.com
```

### Debug Mode

Enable debug logging:
```bash
export LOG_LEVEL=DEBUG
./scripts/start.sh
```

Check all logs:
```bash
tail -f logs/vllm.log logs/api.log
```

## Monitoring

### 1. Health Checks
```bash
# Check vLLM server
curl http://localhost:8000/health

# Check API server
curl http://localhost:12000/health

# Check system resources
curl http://localhost:12000/system/info
```

### 2. Performance Monitoring
```bash
# Monitor GPU usage (if applicable)
watch -n 1 nvidia-smi

# Monitor CPU and memory
htop

# Monitor network
netstat -tulpn | grep :8000
```

### 3. Log Analysis
```bash
# vLLM performance logs
grep "throughput" logs/vllm.log

# API response times
grep "execution_time" logs/api.log

# Error analysis
grep "ERROR" logs/*.log
```

### 4. Metrics Collection

The system exposes metrics at:
- `/metrics` - Prometheus-compatible metrics
- `/system/info` - System information
- `/tasks` - Task execution history

## Production Deployment

### 1. Security Considerations
```bash
# Use environment variables for secrets
export HUGGINGFACE_TOKEN=your_token

# Restrict network access
--host 127.0.0.1  # Local access only

# Use reverse proxy (nginx/traefik)
# Enable HTTPS
# Set up authentication
```

### 2. Scaling
```bash
# Multiple vLLM instances
docker-compose scale vllm-server=3

# Load balancing
# Use nginx or HAProxy

# Horizontal scaling
# Deploy on multiple nodes
```

### 3. Backup and Recovery
```bash
# Backup configuration
tar -czf config-backup.tar.gz config/

# Backup workspace
tar -czf workspace-backup.tar.gz workspace/

# Model cache backup
tar -czf models-backup.tar.gz models/
```

## Support

For issues and questions:
1. Check the logs: `logs/vllm.log` and `logs/api.log`
2. Review this deployment guide
3. Check system requirements
4. Verify configuration files
5. Test with minimal configuration first

## Next Steps

After successful deployment:
1. Explore the web interface at http://localhost:12000
2. Try the API endpoints at http://localhost:12000/docs
3. Run the test suite: `python -m pytest tests/`
4. Customize configuration for your use case
5. Set up monitoring and alerting for production use