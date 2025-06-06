#!/bin/bash
# Start Script for Enhanced CodeAgent Integration
# Automatically detects system and starts appropriate services

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

log_info "Starting Enhanced CodeAgent Integration..."

# Load configuration
if [ ! -f "config/.env" ]; then
    log_warning "No configuration found. Running system detection..."
    python3 scripts/detect_system.py
fi

source config/.env

log_info "Configuration loaded:"
log_info "  - Deployment Type: $DEPLOYMENT_TYPE"
log_info "  - Performance Tier: $PERFORMANCE_TIER"
log_info "  - Model: $DEEPSEEK_MODEL"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    log_warning "Virtual environment not found. Running installation..."
    ./scripts/auto_install.sh
fi

# Activate virtual environment
log_info "Activating virtual environment..."
source venv/bin/activate

# Install missing dependencies if needed
log_info "Checking dependencies..."
pip install -q fastapi uvicorn websockets pydantic aiohttp aiofiles pyyaml

# Create necessary directories
mkdir -p logs workspace models cache temp

# Function to check if port is available
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 1  # Port is in use
    else
        return 0  # Port is available
    fi
}

# Function to start vLLM server
start_vllm_server() {
    log_info "Starting vLLM server..."
    
    # Check if vLLM server is already running
    if check_port $VLLM_PORT; then
        log_info "Starting vLLM server on port $VLLM_PORT..."
        
        # Build vLLM command based on configuration
        VLLM_CMD="python -m vllm.entrypoints.openai.api_server"
        VLLM_CMD="$VLLM_CMD --model $DEEPSEEK_MODEL"
        VLLM_CMD="$VLLM_CMD --host $VLLM_HOST"
        VLLM_CMD="$VLLM_CMD --port $VLLM_PORT"
        VLLM_CMD="$VLLM_CMD --max-model-len $MAX_MODEL_LENGTH"
        VLLM_CMD="$VLLM_CMD --trust-remote-code"
        
        # Add device-specific parameters
        if [ "$ENABLE_GPU" = "true" ]; then
            VLLM_CMD="$VLLM_CMD --tensor-parallel-size ${TENSOR_PARALLEL_SIZE:-1}"
            VLLM_CMD="$VLLM_CMD --gpu-memory-utilization ${GPU_MEMORY_UTILIZATION:-0.8}"
            if [ ! -z "$QUANTIZATION" ]; then
                VLLM_CMD="$VLLM_CMD --quantization $QUANTIZATION"
            fi
        else
            VLLM_CMD="$VLLM_CMD --device cpu"
            if [ ! -z "$CPU_THREADS" ]; then
                export OMP_NUM_THREADS=$CPU_THREADS
            fi
            if [ ! -z "$QUANTIZATION" ]; then
                VLLM_CMD="$VLLM_CMD --quantization $QUANTIZATION"
            fi
        fi
        
        # Start vLLM server in background
        log_info "Executing: $VLLM_CMD"
        nohup $VLLM_CMD > logs/vllm.log 2>&1 &
        VLLM_PID=$!
        echo $VLLM_PID > logs/vllm.pid
        
        log_info "vLLM server starting with PID $VLLM_PID"
        log_info "Waiting for vLLM server to be ready..."
        
        # Wait for server to be ready
        for i in {1..60}; do
            if curl -s http://$VLLM_HOST:$VLLM_PORT/health > /dev/null 2>&1; then
                log_success "vLLM server is ready!"
                break
            fi
            if [ $i -eq 60 ]; then
                log_error "vLLM server failed to start within 60 seconds"
                log_error "Check logs/vllm.log for details"
                exit 1
            fi
            sleep 1
        done
    else
        log_info "vLLM server already running on port $VLLM_PORT"
    fi
}

# Function to start the API server
start_api_server() {
    log_info "Starting API server..."
    
    # Check if API server is already running
    if check_port 12000; then
        log_info "Starting API server on port 12000..."
        
        # Start API server in background
        cd src/api
        nohup python main.py > ../../logs/api.log 2>&1 &
        API_PID=$!
        echo $API_PID > ../../logs/api.pid
        cd ../..
        
        log_info "API server starting with PID $API_PID"
        log_info "Waiting for API server to be ready..."
        
        # Wait for server to be ready
        for i in {1..30}; do
            if curl -s http://localhost:12000/health > /dev/null 2>&1; then
                log_success "API server is ready!"
                break
            fi
            if [ $i -eq 30 ]; then
                log_error "API server failed to start within 30 seconds"
                log_error "Check logs/api.log for details"
                exit 1
            fi
            sleep 1
        done
    else
        log_info "API server already running on port 12000"
    fi
}

# Function to show status
show_status() {
    echo
    log_success "Enhanced CodeAgent Integration is running!"
    echo
    log_info "Services:"
    log_info "  🤖 vLLM Server: http://$VLLM_HOST:$VLLM_PORT"
    log_info "  🌐 API Server: http://localhost:12000"
    log_info "  📱 Web Interface: http://localhost:12000"
    echo
    log_info "Logs:"
    log_info "  📄 vLLM: logs/vllm.log"
    log_info "  📄 API: logs/api.log"
    echo
    log_info "Configuration:"
    log_info "  📊 Model: $DEEPSEEK_MODEL"
    log_info "  🎯 Performance: $PERFORMANCE_TIER"
    log_info "  💻 Device: ${ENABLE_GPU:+GPU}${ENABLE_GPU:-CPU}"
    echo
    log_info "To stop services: ./scripts/stop.sh"
    log_info "To view logs: tail -f logs/vllm.log logs/api.log"
}

# Function to handle cleanup on exit
cleanup() {
    log_info "Shutting down services..."
    
    if [ -f "logs/api.pid" ]; then
        API_PID=$(cat logs/api.pid)
        if kill -0 $API_PID 2>/dev/null; then
            log_info "Stopping API server (PID: $API_PID)..."
            kill $API_PID
        fi
        rm -f logs/api.pid
    fi
    
    if [ -f "logs/vllm.pid" ]; then
        VLLM_PID=$(cat logs/vllm.pid)
        if kill -0 $VLLM_PID 2>/dev/null; then
            log_info "Stopping vLLM server (PID: $VLLM_PID)..."
            kill $VLLM_PID
        fi
        rm -f logs/vllm.pid
    fi
    
    log_info "Cleanup complete"
}

# Set up signal handlers
trap cleanup EXIT INT TERM

# Check if we should run in daemon mode
DAEMON_MODE=false
if [ "$1" = "--daemon" ] || [ "$1" = "-d" ]; then
    DAEMON_MODE=true
    log_info "Running in daemon mode"
fi

# Start services
start_vllm_server
start_api_server

# Show status
show_status

# If not in daemon mode, keep script running and show logs
if [ "$DAEMON_MODE" = "false" ]; then
    log_info "Press Ctrl+C to stop all services"
    echo
    
    # Follow logs
    if [ -f "logs/vllm.log" ] && [ -f "logs/api.log" ]; then
        tail -f logs/vllm.log logs/api.log
    else
        # Keep script running
        while true; do
            sleep 1
        done
    fi
else
    log_info "Services started in daemon mode"
    log_info "Use './scripts/stop.sh' to stop services"
fi