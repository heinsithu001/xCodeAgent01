#!/bin/bash

# Production Real-Time Setup for DeepSeek R1 0528
# Starts vLLM server and production backend for real-time data processing

set -e

echo "🚀 Starting DeepSeek R1 0528 Production Real-Time Environment"
echo "=================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
VLLM_PORT=8000
BACKEND_PORT=12000
FRONTEND_PORT=12001

# Function to check if port is available
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo -e "${RED}Port $port is already in use${NC}"
        return 1
    fi
    return 0
}

# Function to wait for service to be ready
wait_for_service() {
    local url=$1
    local service_name=$2
    local max_attempts=60
    local attempt=1
    
    echo -e "${YELLOW}Waiting for $service_name to be ready...${NC}"
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s "$url" >/dev/null 2>&1; then
            echo -e "${GREEN}$service_name is ready!${NC}"
            return 0
        fi
        
        echo -n "."
        sleep 5
        attempt=$((attempt + 1))
    done
    
    echo -e "${RED}$service_name failed to start within expected time${NC}"
    return 1
}

# Function to detect system capabilities
detect_system() {
    echo -e "${BLUE}Detecting system capabilities...${NC}"
    
    # Check GPU availability
    if command -v nvidia-smi >/dev/null 2>&1; then
        GPU_COUNT=$(nvidia-smi --list-gpus | wc -l)
        GPU_MEMORY=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -1)
        echo -e "${GREEN}Found $GPU_COUNT GPU(s) with ${GPU_MEMORY}MB memory${NC}"
        USE_GPU=true
    else
        echo -e "${YELLOW}No GPU detected, using CPU mode${NC}"
        USE_GPU=false
    fi
    
    # Check available RAM
    TOTAL_RAM=$(free -g | awk '/^Mem:/{print $2}')
    echo -e "${GREEN}Available RAM: ${TOTAL_RAM}GB${NC}"
    
    # Check CPU cores
    CPU_CORES=$(nproc)
    echo -e "${GREEN}CPU cores: $CPU_CORES${NC}"
}

# Function to start vLLM server
start_vllm_server() {
    echo -e "${BLUE}Starting vLLM server for DeepSeek R1 0528...${NC}"
    
    if ! check_port $VLLM_PORT; then
        echo -e "${RED}vLLM port $VLLM_PORT is already in use. Please stop the existing service.${NC}"
        exit 1
    fi
    
    # Start vLLM server in background
    echo -e "${YELLOW}Launching vLLM server (this may take several minutes for model download)...${NC}"
    
    if [ "$USE_GPU" = true ]; then
        echo -e "${GREEN}Using GPU acceleration${NC}"
        nohup python vllm_server.py > vllm_server.log 2>&1 &
    else
        echo -e "${YELLOW}Using CPU mode (slower but functional)${NC}"
        nohup python vllm_server.py > vllm_server.log 2>&1 &
    fi
    
    VLLM_PID=$!
    echo $VLLM_PID > vllm_server.pid
    echo -e "${GREEN}vLLM server started with PID: $VLLM_PID${NC}"
    
    # Wait for vLLM server to be ready
    if wait_for_service "http://localhost:$VLLM_PORT/health" "vLLM server"; then
        echo -e "${GREEN}✅ vLLM server is operational${NC}"
    else
        echo -e "${RED}❌ vLLM server failed to start${NC}"
        echo -e "${YELLOW}Check vllm_server.log for details${NC}"
        exit 1
    fi
}

# Function to start production backend
start_backend() {
    echo -e "${BLUE}Starting production backend...${NC}"
    
    if ! check_port $BACKEND_PORT; then
        echo -e "${RED}Backend port $BACKEND_PORT is already in use. Please stop the existing service.${NC}"
        exit 1
    fi
    
    # Set environment variables
    export VLLM_SERVER_URL="http://localhost:$VLLM_PORT"
    export BACKEND_HOST="0.0.0.0"
    export BACKEND_PORT=$BACKEND_PORT
    
    # Start backend in background
    nohup python production_backend.py > production_backend.log 2>&1 &
    BACKEND_PID=$!
    echo $BACKEND_PID > production_backend.pid
    echo -e "${GREEN}Production backend started with PID: $BACKEND_PID${NC}"
    
    # Wait for backend to be ready
    if wait_for_service "http://localhost:$BACKEND_PORT/health" "Production backend"; then
        echo -e "${GREEN}✅ Production backend is operational${NC}"
    else
        echo -e "${RED}❌ Production backend failed to start${NC}"
        echo -e "${YELLOW}Check production_backend.log for details${NC}"
        exit 1
    fi
}

# Function to start frontend (if available)
start_frontend() {
    if [ -d "frontend-v2" ]; then
        echo -e "${BLUE}Starting frontend...${NC}"
        
        if ! check_port $FRONTEND_PORT; then
            echo -e "${YELLOW}Frontend port $FRONTEND_PORT is already in use, skipping frontend startup${NC}"
            return 0
        fi
        
        cd frontend-v2
        
        # Install dependencies if needed
        if [ ! -d "node_modules" ]; then
            echo -e "${YELLOW}Installing frontend dependencies...${NC}"
            npm install
        fi
        
        # Start frontend
        export VITE_API_BASE_URL="http://localhost:$BACKEND_PORT/api/v1"
        nohup npm run dev -- --host 0.0.0.0 --port $FRONTEND_PORT > ../frontend.log 2>&1 &
        FRONTEND_PID=$!
        echo $FRONTEND_PID > ../frontend.pid
        echo -e "${GREEN}Frontend started with PID: $FRONTEND_PID${NC}"
        
        cd ..
        
        # Wait for frontend to be ready
        if wait_for_service "http://localhost:$FRONTEND_PORT" "Frontend"; then
            echo -e "${GREEN}✅ Frontend is operational${NC}"
        else
            echo -e "${YELLOW}⚠️  Frontend may still be starting${NC}"
        fi
    else
        echo -e "${YELLOW}Frontend directory not found, skipping frontend startup${NC}"
    fi
}

# Function to display status
show_status() {
    echo ""
    echo -e "${GREEN}🎉 DeepSeek R1 0528 Production Environment is Ready!${NC}"
    echo "=================================================="
    echo ""
    echo -e "${BLUE}📊 Service Status:${NC}"
    echo -e "  vLLM Server:      ${GREEN}✅ Running on port $VLLM_PORT${NC}"
    echo -e "  Production API:   ${GREEN}✅ Running on port $BACKEND_PORT${NC}"
    
    if [ -f "frontend.pid" ]; then
        echo -e "  Frontend:         ${GREEN}✅ Running on port $FRONTEND_PORT${NC}"
    fi
    
    echo ""
    echo -e "${BLUE}🌐 Access URLs:${NC}"
    echo -e "  Main Application: ${YELLOW}https://work-1-nrbspfazbqxywbea.prod-runtime.all-hands.dev${NC}"
    echo -e "  API Documentation: ${YELLOW}http://localhost:$BACKEND_PORT/docs${NC}"
    echo -e "  vLLM Server:      ${YELLOW}http://localhost:$VLLM_PORT/health${NC}"
    echo -e "  System Status:    ${YELLOW}http://localhost:$BACKEND_PORT/api/v1/status${NC}"
    
    if [ -f "frontend.pid" ]; then
        echo -e "  Frontend:         ${YELLOW}https://work-2-nrbspfazbqxywbea.prod-runtime.all-hands.dev${NC}"
    fi
    
    echo ""
    echo -e "${BLUE}📈 Real-Time Features:${NC}"
    echo -e "  ✅ Real-time data processing"
    echo -e "  ✅ WebSocket streaming"
    echo -e "  ✅ Live code generation"
    echo -e "  ✅ Interactive chat"
    echo -e "  ✅ Performance monitoring"
    echo ""
    echo -e "${BLUE}🔧 Management Commands:${NC}"
    echo -e "  Stop all services: ${YELLOW}./stop_production.sh${NC}"
    echo -e "  View logs:         ${YELLOW}tail -f *.log${NC}"
    echo -e "  Check status:      ${YELLOW}curl http://localhost:$BACKEND_PORT/health${NC}"
    echo ""
    echo -e "${GREEN}Ready for real-time DeepSeek R1 0528 testing! 🚀${NC}"
}

# Function to create stop script
create_stop_script() {
    cat > stop_production.sh << 'EOF'
#!/bin/bash

echo "🛑 Stopping DeepSeek R1 Production Environment..."

# Stop services
for service in vllm_server production_backend frontend; do
    if [ -f "${service}.pid" ]; then
        PID=$(cat "${service}.pid")
        if kill -0 $PID 2>/dev/null; then
            echo "Stopping $service (PID: $PID)..."
            kill $PID
            sleep 2
            if kill -0 $PID 2>/dev/null; then
                echo "Force killing $service..."
                kill -9 $PID
            fi
        fi
        rm -f "${service}.pid"
    fi
done

echo "✅ All services stopped"
EOF

    chmod +x stop_production.sh
}

# Main execution
main() {
    echo -e "${GREEN}Starting DeepSeek R1 0528 Production Real-Time Environment${NC}"
    echo ""
    
    # Detect system capabilities
    detect_system
    echo ""
    
    # Create stop script
    create_stop_script
    
    # Start services
    start_vllm_server
    echo ""
    
    start_backend
    echo ""
    
    start_frontend
    echo ""
    
    # Show final status
    show_status
    
    # Keep script running to monitor services
    echo -e "${BLUE}Monitoring services... Press Ctrl+C to stop${NC}"
    
    trap 'echo -e "\n${YELLOW}Shutting down services...${NC}"; ./stop_production.sh; exit 0' INT
    
    while true; do
        sleep 30
        
        # Check if services are still running
        for service in vllm_server production_backend; do
            if [ -f "${service}.pid" ]; then
                PID=$(cat "${service}.pid")
                if ! kill -0 $PID 2>/dev/null; then
                    echo -e "${RED}⚠️  $service has stopped unexpectedly${NC}"
                fi
            fi
        done
    done
}

# Run main function
main "$@"