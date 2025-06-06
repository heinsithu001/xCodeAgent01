#!/bin/bash
# Auto-Installation Script for Enhanced CodeAgent Integration
# Adaptive installation based on system capabilities

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running from correct directory
if [ ! -f "scripts/detect_system.py" ]; then
    log_error "Please run this script from the enhanced-codeagent-integration root directory"
    exit 1
fi

log_info "Starting Enhanced CodeAgent Integration Installation..."

# Load configuration if available
if [ -f "config/.env" ]; then
    log_info "Loading system configuration..."
    source config/.env
else
    log_warning "No configuration found. Running system detection first..."
    python3 scripts/detect_system.py
    source config/.env
fi

log_info "Detected deployment type: $DEPLOYMENT_TYPE"
log_info "Performance tier: $PERFORMANCE_TIER"

# Update system packages
log_info "Updating system packages..."
if command -v apt-get &> /dev/null; then
    sudo apt-get update -qq
    sudo apt-get install -y curl wget git build-essential python3-dev
elif command -v yum &> /dev/null; then
    sudo yum update -y
    sudo yum install -y curl wget git gcc gcc-c++ python3-devel
else
    log_warning "Package manager not detected. Please install curl, wget, git, and build tools manually."
fi

# Install Python dependencies based on system capabilities
log_info "Installing Python dependencies..."

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    log_info "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install base dependencies
log_info "Installing base dependencies..."
pip install psutil requests aiohttp fastapi uvicorn websockets pydantic

# Install PyTorch based on system capabilities
if [ "$ENABLE_GPU" = "true" ]; then
    log_info "Installing GPU-optimized PyTorch..."
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
else
    log_info "Installing CPU-optimized PyTorch..."
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
fi

# Install vLLM based on system capabilities
log_info "Installing vLLM..."
if [ "$ENABLE_GPU" = "true" ]; then
    pip install vllm
else
    # For CPU-only systems, we'll use a lighter alternative or CPU-optimized vLLM
    pip install vllm || {
        log_warning "vLLM installation failed. Installing alternative CPU inference engine..."
        pip install transformers accelerate
    }
fi

# Install additional ML dependencies
log_info "Installing additional ML dependencies..."
pip install transformers accelerate datasets tokenizers huggingface-hub

# Install web framework dependencies
log_info "Installing web framework dependencies..."
pip install fastapi uvicorn websockets jinja2 aiofiles

# Install development dependencies
log_info "Installing development dependencies..."
pip install pytest pytest-asyncio black flake8 mypy

# Install CodeAgent03 dependencies
log_info "Installing CodeAgent03 dependencies..."
cd repositories/CodeAgent03
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
elif [ -f "pyproject.toml" ]; then
    pip install -e .
else
    log_warning "No requirements file found in CodeAgent03. Installing common dependencies..."
    pip install openai anthropic litellm
fi
cd ../..

# Install Docker if not available and user has sudo access
if [ "$DOCKER_AVAILABLE" != "true" ] && command -v sudo &> /dev/null; then
    log_info "Installing Docker..."
    
    # Install Docker based on OS
    if command -v apt-get &> /dev/null; then
        # Ubuntu/Debian
        sudo apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
        echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
        sudo apt-get update
        sudo apt-get install -y docker-ce docker-ce-cli containerd.io
        sudo usermod -aG docker $USER
        log_success "Docker installed. Please log out and back in to use Docker without sudo."
    elif command -v yum &> /dev/null; then
        # CentOS/RHEL
        sudo yum install -y yum-utils
        sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
        sudo yum install -y docker-ce docker-ce-cli containerd.io
        sudo systemctl start docker
        sudo systemctl enable docker
        sudo usermod -aG docker $USER
        log_success "Docker installed and started."
    else
        log_warning "Could not install Docker automatically. Please install Docker manually."
    fi
fi

# Create necessary directories
log_info "Creating project directories..."
mkdir -p {logs,data,models,cache,temp}

# Download model if specified and system has enough resources
if [ "$PERFORMANCE_TIER" != "minimal" ]; then
    log_info "Pre-downloading model for better performance..."
    python3 -c "
from huggingface_hub import snapshot_download
import os
try:
    model_name = os.environ.get('DEEPSEEK_MODEL', 'deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B')
    print(f'Downloading {model_name}...')
    snapshot_download(repo_id=model_name, cache_dir='./models')
    print('Model downloaded successfully!')
except Exception as e:
    print(f'Model download failed: {e}')
    print('Model will be downloaded on first use.')
"
fi

# Set up configuration files
log_info "Setting up configuration files..."

# Create vLLM configuration
cat > config/vllm_config.json << EOF
{
    "model": "$DEEPSEEK_MODEL",
    "host": "$VLLM_HOST",
    "port": $VLLM_PORT,
    "max_model_len": $MAX_MODEL_LENGTH,
    "max_num_seqs": $MAX_CONCURRENT_REQUESTS,
    "trust_remote_code": true,
    "device": "${DEVICE_TYPE:-auto}",
    "tensor_parallel_size": ${TENSOR_PARALLEL_SIZE:-1},
    "gpu_memory_utilization": ${GPU_MEMORY_UTILIZATION:-0.8}
}
EOF

# Create integration configuration
cat > config/integration_config.yaml << EOF
# Enhanced CodeAgent Integration Configuration
system:
  deployment_type: $DEPLOYMENT_TYPE
  performance_tier: $PERFORMANCE_TIER
  cpu_cores: $CPU_CORES
  total_ram_gb: $TOTAL_RAM_GB

model:
  name: $DEEPSEEK_MODEL
  max_length: $MAX_MODEL_LENGTH
  batch_size: $BATCH_SIZE
  temperature: 0.6
  top_p: 0.95

server:
  host: $VLLM_HOST
  port: $VLLM_PORT
  max_concurrent_requests: $MAX_CONCURRENT_REQUESTS
  timeout: 300

codeagent:
  repository_path: "./repositories/CodeAgent03"
  config_path: "./config/codeagent03.yaml"
  
openhands:
  config_path: "./config/openhands.json"
  
logging:
  level: $LOG_LEVEL
  file: "./logs/integration.log"
EOF

# Make scripts executable
chmod +x scripts/*.sh scripts/*.py

log_success "Installation completed successfully!"
log_info "Configuration summary:"
log_info "  - Deployment Type: $DEPLOYMENT_TYPE"
log_info "  - Performance Tier: $PERFORMANCE_TIER"
log_info "  - Model: $DEEPSEEK_MODEL"
log_info "  - Max Context: $MAX_MODEL_LENGTH tokens"

echo
log_info "Next steps:"
log_info "1. Activate virtual environment: source venv/bin/activate"
log_info "2. Start the integration: ./scripts/start.sh"
log_info "3. Access web interface: http://localhost:8080"

if [ "$DOCKER_AVAILABLE" != "true" ]; then
    log_warning "Docker is not available. Some features may be limited."
fi

if [ "$PERFORMANCE_TIER" = "minimal" ]; then
    log_warning "Running in minimal performance mode due to limited resources."
    log_warning "Consider upgrading hardware for better performance."
fi

log_success "Enhanced CodeAgent Integration is ready to use!"