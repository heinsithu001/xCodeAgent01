#!/bin/bash
# Production Full Stack Startup Script
# Starts vLLM server with DeepSeek-R1-0528 and production backend

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
VLLM_PORT=8000
BACKEND_PORT=12000
MODEL_NAME="deepseek-ai/DeepSeek-R1-0528"
LOG_DIR="./logs"

# Create logs directory
mkdir -p $LOG_DIR

# Logging functions
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
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

# Banner
echo -e "${PURPLE}"
cat << "EOF"
╔══════════════════════════════════════════════════════════════════════════════╗
║                    xCodeAgent Production Full Stack                          ║
║                   DeepSeek-R1-0528 + vLLM + Backend                         ║
╚══════════════════════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

# System checks
log "🔍 Performing system checks..."

# Check Python
if ! command -v python3 &> /dev/null; then
    log_error "Python 3 is required but not installed"
    exit 1
fi

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
log "Python version: $PYTHON_VERSION"

# Check available memory
TOTAL_RAM=$(python3 -c "import psutil; print(int(psutil.virtual_memory().total / (1024**3)))")
AVAILABLE_RAM=$(python3 -c "import psutil; print(int(psutil.virtual_memory().available / (1024**3)))")

log "System RAM: ${TOTAL_RAM}GB total, ${AVAILABLE_RAM}GB available"

if [ $AVAILABLE_RAM -lt 16 ]; then
    log_warning "Low available RAM detected. DeepSeek-R1-0528 requires significant memory."
    log_warning "Consider closing other applications or using a smaller model."
fi

# Check GPU availability
if command -v nvidia-smi &> /dev/null; then
    GPU_INFO=$(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader,nounits | head -1)
    log "GPU detected: $GPU_INFO"
    USE_GPU=true
else
    log_warning "No NVIDIA GPU detected. Will use CPU mode (slower)."
    USE_GPU=false
fi

# Check disk space
FREE_SPACE=$(df -BG . | awk 'NR==2 {print $4}' | sed 's/G//')
log "Free disk space: ${FREE_SPACE}GB"

if [ $FREE_SPACE -lt 50 ]; then
    log_error "Insufficient disk space. Model download requires ~50GB+"
    exit 1
fi

# Install dependencies
log "📦 Installing/updating dependencies..."

# Install core dependencies
pip install -q --upgrade pip
pip install -q fastapi uvicorn aiohttp psutil pydantic requests

# Install PyTorch (required for vLLM)
if $USE_GPU; then
    log "Installing PyTorch with CUDA support..."
    pip install -q torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
else
    log "Installing PyTorch for CPU..."
    pip install -q torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
fi

# Install vLLM
log "Installing vLLM..."
if $USE_GPU; then
    pip install -q vllm
else
    # For CPU, we might need specific build
    pip install -q vllm
fi

# Clean up any existing processes
log "🧹 Cleaning up existing processes..."
pkill -f "vllm.*api_server" 2>/dev/null || true
pkill -f "uvicorn.*:$VLLM_PORT" 2>/dev/null || true
pkill -f "uvicorn.*:$BACKEND_PORT" 2>/dev/null || true
sleep 3

# Start vLLM server
log "🤖 Starting vLLM server with DeepSeek-R1-0528..."

# Build vLLM command
VLLM_CMD="python3 -m vllm.entrypoints.openai.api_server"
VLLM_CMD="$VLLM_CMD --model $MODEL_NAME"
VLLM_CMD="$VLLM_CMD --host 0.0.0.0"
VLLM_CMD="$VLLM_CMD --port $VLLM_PORT"
VLLM_CMD="$VLLM_CMD --trust-remote-code"

if $USE_GPU; then
    # GPU-specific settings
    GPU_COUNT=$(nvidia-smi --list-gpus | wc -l)
    if [ $GPU_COUNT -gt 1 ]; then
        TENSOR_PARALLEL_SIZE=2
    else
        TENSOR_PARALLEL_SIZE=1
    fi
    
    VLLM_CMD="$VLLM_CMD --tensor-parallel-size $TENSOR_PARALLEL_SIZE"
    VLLM_CMD="$VLLM_CMD --gpu-memory-utilization 0.85"
    
    log "GPU configuration: $GPU_COUNT GPU(s), tensor-parallel-size: $TENSOR_PARALLEL_SIZE"
else
    # CPU-specific settings
    VLLM_CMD="$VLLM_CMD --device cpu"
    VLLM_CMD="$VLLM_CMD --max-model-len 8192"  # Reduced for CPU
    
    log "CPU configuration: max-model-len reduced to 8192"
fi

# Add memory optimizations
VLLM_CMD="$VLLM_CMD --max-num-seqs 256"
VLLM_CMD="$VLLM_CMD --max-num-batched-tokens 8192"
VLLM_CMD="$VLLM_CMD --block-size 16"

log "vLLM command: $VLLM_CMD"

# Set environment variables
export CUDA_VISIBLE_DEVICES=0
export HF_HOME="$HOME/.cache/huggingface"
export VLLM_LOGGING_LEVEL=INFO

# Start vLLM server in background
log "Starting vLLM server (this may take several minutes for model download/loading)..."
nohup $VLLM_CMD > $LOG_DIR/vllm_server.log 2>&1 &
VLLM_PID=$!
echo $VLLM_PID > .vllm_production_pid

log "vLLM server started with PID: $VLLM_PID"
log "📋 vLLM logs: tail -f $LOG_DIR/vllm_server.log"

# Wait for vLLM server to start
log "⏳ Waiting for vLLM server to initialize..."
log "💡 This may take 5-15 minutes depending on your system and internet speed"

VLLM_READY=false
MAX_WAIT=1800  # 30 minutes max wait
WAIT_TIME=0

while [ $WAIT_TIME -lt $MAX_WAIT ]; do
    if curl -s http://localhost:$VLLM_PORT/health > /dev/null 2>&1; then
        VLLM_READY=true
        break
    fi
    
    # Show progress every 30 seconds
    if [ $((WAIT_TIME % 30)) -eq 0 ]; then
        log "Still waiting for vLLM server... (${WAIT_TIME}s elapsed)"
        log "💡 Check logs: tail -f $LOG_DIR/vllm_server.log"
    fi
    
    sleep 10
    WAIT_TIME=$((WAIT_TIME + 10))
done

if [ "$VLLM_READY" = true ]; then
    log_success "vLLM server is ready!"
    
    # Test the server
    log "🧪 Testing vLLM server..."
    HEALTH_RESPONSE=$(curl -s http://localhost:$VLLM_PORT/health)
    log "Health check response: $HEALTH_RESPONSE"
    
    # Test models endpoint
    MODELS_RESPONSE=$(curl -s http://localhost:$VLLM_PORT/v1/models)
    if echo "$MODELS_RESPONSE" | grep -q "deepseek"; then
        log_success "DeepSeek model is loaded and available"
    else
        log_warning "DeepSeek model may not be properly loaded"
    fi
else
    log_error "vLLM server failed to start within $MAX_WAIT seconds"
    log_error "Check the logs: cat $LOG_DIR/vllm_server.log"
    exit 1
fi

# Start production backend
log "🔧 Starting production backend..."

# Set environment variables for backend
export VLLM_SERVER_URL="http://localhost:$VLLM_PORT"
export BACKEND_HOST="0.0.0.0"
export BACKEND_PORT="$BACKEND_PORT"
export PRODUCTION_MODE="true"

# Start backend server
nohup python3 production_unified_backend.py > $LOG_DIR/backend.log 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > .backend_production_pid

log "Backend server started with PID: $BACKEND_PID"
log "📋 Backend logs: tail -f $LOG_DIR/backend.log"

# Wait for backend to start
log "⏳ Waiting for backend server to start..."
BACKEND_READY=false
WAIT_TIME=0
MAX_WAIT=60

while [ $WAIT_TIME -lt $MAX_WAIT ]; do
    if curl -s http://localhost:$BACKEND_PORT/health > /dev/null 2>&1; then
        BACKEND_READY=true
        break
    fi
    sleep 2
    WAIT_TIME=$((WAIT_TIME + 2))
done

if [ "$BACKEND_READY" = true ]; then
    log_success "Backend server is ready!"
    
    # Test backend
    log "🧪 Testing backend server..."
    STATUS_RESPONSE=$(curl -s http://localhost:$BACKEND_PORT/api/v3/status)
    if echo "$STATUS_RESPONSE" | grep -q '"success":true'; then
        log_success "Backend API is working correctly"
    else
        log_warning "Backend API may have issues"
    fi
else
    log_error "Backend server failed to start"
    log_error "Check the logs: cat $LOG_DIR/backend.log"
    exit 1
fi

# Run comprehensive tests
log "🧪 Running full stack tests..."
if [ -f "test_full_stack.py" ]; then
    python3 test_full_stack.py --output $LOG_DIR/test_results.json
    TEST_EXIT_CODE=$?
    
    if [ $TEST_EXIT_CODE -eq 0 ]; then
        log_success "All tests passed!"
    else
        log_warning "Some tests failed. Check test_results.json for details."
    fi
else
    log_warning "Test suite not found. Skipping automated tests."
fi

# Create stop script
cat > stop_production_full_stack.sh << 'EOF'
#!/bin/bash
echo "🛑 Stopping xCodeAgent Production Full Stack..."

if [ -f .vllm_production_pid ]; then
    VLLM_PID=$(cat .vllm_production_pid)
    kill $VLLM_PID 2>/dev/null && echo "✅ Stopped vLLM server (PID: $VLLM_PID)"
    rm .vllm_production_pid
fi

if [ -f .backend_production_pid ]; then
    BACKEND_PID=$(cat .backend_production_pid)
    kill $BACKEND_PID 2>/dev/null && echo "✅ Stopped backend server (PID: $BACKEND_PID)"
    rm .backend_production_pid
fi

# Cleanup any remaining processes
pkill -f "vllm.*api_server" 2>/dev/null || true
pkill -f "uvicorn.*:8000" 2>/dev/null || true
pkill -f "uvicorn.*:12000" 2>/dev/null || true

echo "🎯 All servers stopped"
EOF

chmod +x stop_production_full_stack.sh

# Success message
echo
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                    🎉 PRODUCTION DEPLOYMENT SUCCESSFUL! 🎉                  ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════════════════════╝${NC}"
echo
echo -e "${CYAN}📊 Service URLs:${NC}"
echo "   • Frontend Application:  http://localhost:$BACKEND_PORT"
echo "   • Backend API:           http://localhost:$BACKEND_PORT/api/v3"
echo "   • API Documentation:     http://localhost:$BACKEND_PORT/docs"
echo "   • vLLM OpenAI API:       http://localhost:$VLLM_PORT/v1"
echo "   • vLLM Health:           http://localhost:$VLLM_PORT/health"
echo
echo -e "${CYAN}🔧 Configuration:${NC}"
echo "   • Model: $MODEL_NAME"
echo "   • GPU Mode: $USE_GPU"
echo "   • System RAM: ${TOTAL_RAM}GB"
echo "   • Production Mode: Enabled"
echo
echo -e "${CYAN}📋 Monitoring:${NC}"
echo "   • vLLM Logs:     tail -f $LOG_DIR/vllm_server.log"
echo "   • Backend Logs:  tail -f $LOG_DIR/backend.log"
echo "   • Test Results:  cat $LOG_DIR/test_results.json"
echo
echo -e "${CYAN}🧪 Quick Tests:${NC}"
echo "   • Status:        curl http://localhost:$BACKEND_PORT/api/v3/status"
echo "   • Chat Test:     curl -X POST http://localhost:$BACKEND_PORT/api/v3/chat -H 'Content-Type: application/json' -d '{\"message\":\"Hello\",\"execution_mode\":\"production\"}'"
echo "   • Full Test:     python3 test_full_stack.py"
echo
echo -e "${CYAN}💡 Next Steps:${NC}"
echo "   1. Open http://localhost:$BACKEND_PORT in your browser"
echo "   2. Test the chat interface with production mode"
echo "   3. Monitor performance and logs"
echo "   4. Run comprehensive tests: python3 test_full_stack.py"
echo
echo -e "${YELLOW}⚠️  Important Notes:${NC}"
echo "   • First model inference may be slow (model warming up)"
echo "   • Monitor GPU/CPU usage and memory consumption"
echo "   • Use './stop_production_full_stack.sh' to stop all services"
echo "   • Check logs if you encounter any issues"
echo

log_success "🚀 xCodeAgent Production Full Stack is now running with DeepSeek-R1-0528!"
log "🎯 Ready for end-to-end testing and validation"