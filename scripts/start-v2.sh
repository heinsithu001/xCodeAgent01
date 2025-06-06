#!/bin/bash
# Enhanced CodeAgent Integration v2.0 Startup Script
# Production-ready deployment with vLLM infrastructure

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
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

log_header() {
    echo -e "${PURPLE}[ENHANCED CODEAGENT V2.0]${NC} $1"
}

# ASCII Art Header
print_header() {
    echo -e "${CYAN}"
    cat << "EOF"
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║     ███████╗███╗   ██╗██╗  ██╗ █████╗ ███╗   ██╗ ██████╗     ║
║     ██╔════╝████╗  ██║██║  ██║██╔══██╗████╗  ██║██╔════╝     ║
║     █████╗  ██╔██╗ ██║███████║███████║██╔██╗ ██║██║          ║
║     ██╔══╝  ██║╚██╗██║██╔══██║██╔══██║██║╚██╗██║██║          ║
║     ███████╗██║ ╚████║██║  ██║██║  ██║██║ ╚████║╚██████╗     ║
║     ╚══════╝╚═╝  ╚═══╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝ ╚═════╝     ║
║                                                               ║
║              CodeAgent Integration v2.0                       ║
║         Production-Ready vLLM Infrastructure                  ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
}

# Check if running from correct directory
check_directory() {
    if [ ! -f "backend-v2/main.py" ]; then
        log_error "Please run this script from the enhanced-codeagent-integration root directory"
        exit 1
    fi
}

# System detection
detect_system() {
    log_info "Detecting system capabilities..."
    
    # Run system detection if config doesn't exist
    if [ ! -f "config/.env" ]; then
        log_warning "No configuration found. Running system detection..."
        python3 scripts/detect_system.py
    fi
    
    # Load configuration
    if [ -f "config/.env" ]; then
        source config/.env
        log_success "Configuration loaded"
        log_info "  - Deployment Type: $DEPLOYMENT_TYPE"
        log_info "  - Performance Tier: $PERFORMANCE_TIER"
        log_info "  - Model: $DEEPSEEK_MODEL"
    else
        log_warning "Using default configuration"
        DEPLOYMENT_TYPE="cpu"
        PERFORMANCE_TIER="standard"
        DEEPSEEK_MODEL="deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B"
    fi
}

# Install dependencies
install_dependencies() {
    log_info "Installing Enhanced CodeAgent v2.0 dependencies..."
    
    # Check if virtual environment exists
    if [ ! -d "venv" ]; then
        log_info "Creating virtual environment..."
        python3 -m venv venv
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install backend dependencies
    log_info "Installing backend dependencies..."
    cd backend-v2
    pip install -r requirements.txt
    cd ..
    
    log_success "Dependencies installed successfully"
}

# Check Docker availability
check_docker() {
    if command -v docker &> /dev/null && command -v docker-compose &> /dev/null; then
        log_success "Docker and Docker Compose available"
        return 0
    else
        log_warning "Docker not available - using direct Python deployment"
        return 1
    fi
}

# Start services based on deployment mode
start_services() {
    local deployment_mode=$1
    
    case $deployment_mode in
        "docker-demo")
            start_docker_demo
            ;;
        "docker-vllm-cpu")
            start_docker_vllm_cpu
            ;;
        "docker-vllm-gpu")
            start_docker_vllm_gpu
            ;;
        "docker-production")
            start_docker_production
            ;;
        "python-demo")
            start_python_demo
            ;;
        *)
            log_error "Unknown deployment mode: $deployment_mode"
            exit 1
            ;;
    esac
}

# Docker deployment modes
start_docker_demo() {
    log_header "Starting Docker Demo Mode (Cost-Free)"
    
    docker-compose -f docker-compose-v2.yml up -d enhanced-backend-v2
    
    log_success "Demo mode started successfully!"
    log_info "  🌐 Backend API: http://localhost:12000"
    log_info "  📚 API Docs: http://localhost:12000/docs"
    log_info "  💰 Cost: Free (Demo Mode)"
    log_info "  🏗️ Infrastructure: Production-Ready"
}

start_docker_vllm_cpu() {
    log_header "Starting Docker with CPU vLLM Server"
    
    docker-compose -f docker-compose-v2.yml --profile vllm-cpu up -d
    
    log_success "CPU vLLM deployment started!"
    log_info "  🌐 Backend API: http://localhost:12000"
    log_info "  🤖 vLLM Server: http://localhost:8000"
    log_info "  📚 API Docs: http://localhost:12000/docs"
    log_info "  💻 Mode: CPU Optimized"
}

start_docker_vllm_gpu() {
    log_header "Starting Docker with GPU vLLM Server"
    
    # Check for NVIDIA Docker support
    if ! docker run --rm --gpus all nvidia/cuda:11.8-base-ubuntu20.04 nvidia-smi &>/dev/null; then
        log_error "NVIDIA Docker support not available"
        log_info "Falling back to CPU mode..."
        start_docker_vllm_cpu
        return
    fi
    
    docker-compose -f docker-compose-v2.yml --profile vllm-gpu up -d
    
    log_success "GPU vLLM deployment started!"
    log_info "  🌐 Backend API: http://localhost:12000"
    log_info "  🤖 vLLM Server: http://localhost:8000"
    log_info "  📚 API Docs: http://localhost:12000/docs"
    log_info "  🎮 Mode: GPU Accelerated"
}

start_docker_production() {
    log_header "Starting Full Production Stack"
    
    docker-compose -f docker-compose-v2.yml \
        --profile production \
        --profile cache \
        --profile monitoring \
        --profile frontend \
        up -d
    
    log_success "Production stack started!"
    log_info "  🌐 Frontend: http://localhost:3000"
    log_info "  🔧 Backend API: http://localhost:12000"
    log_info "  📊 Monitoring: http://localhost:3001 (Grafana)"
    log_info "  📈 Metrics: http://localhost:9090 (Prometheus)"
    log_info "  🚀 Load Balancer: http://localhost:80"
}

# Python direct deployment
start_python_demo() {
    log_header "Starting Python Demo Mode (Cost-Free)"
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Start backend
    cd backend-v2
    log_info "Starting Enhanced CodeAgent v2.0 backend..."
    
    # Start in background
    nohup python main.py > ../logs/backend-v2.log 2>&1 &
    BACKEND_PID=$!
    echo $BACKEND_PID > ../logs/backend-v2.pid
    
    cd ..
    
    # Wait for backend to start
    log_info "Waiting for backend to be ready..."
    for i in {1..30}; do
        if curl -s http://localhost:12000/api/v2/status > /dev/null 2>&1; then
            log_success "Backend is ready!"
            break
        fi
        if [ $i -eq 30 ]; then
            log_error "Backend failed to start within 30 seconds"
            log_error "Check logs/backend-v2.log for details"
            exit 1
        fi
        sleep 1
    done
    
    log_success "Python demo mode started successfully!"
    log_info "  🌐 Backend API: http://localhost:12000"
    log_info "  📚 API Docs: http://localhost:12000/docs"
    log_info "  💰 Cost: Free (Demo Mode)"
    log_info "  🏗️ Infrastructure: Production-Ready"
    log_info "  📄 Logs: logs/backend-v2.log"
}

# Show deployment options
show_deployment_options() {
    echo
    log_header "Available Deployment Options"
    echo
    echo "1. 🆓 Demo Mode (Cost-Free)"
    echo "   - Complete vLLM infrastructure demonstration"
    echo "   - No model download required"
    echo "   - Perfect for testing and development"
    echo
    echo "2. 💻 CPU vLLM Server"
    echo "   - Actual DeepSeek R1 model via vLLM"
    echo "   - CPU-optimized deployment"
    echo "   - Requires model download (~3-7GB)"
    echo
    echo "3. 🎮 GPU vLLM Server"
    echo "   - GPU-accelerated DeepSeek R1"
    echo "   - Best performance"
    echo "   - Requires NVIDIA GPU + Docker support"
    echo
    echo "4. 🚀 Production Stack"
    echo "   - Full production deployment"
    echo "   - Load balancing, monitoring, caching"
    echo "   - Frontend + Backend + Infrastructure"
    echo
    echo "5. 🐍 Python Direct (Demo)"
    echo "   - Direct Python execution"
    echo "   - No Docker required"
    echo "   - Demo mode only"
    echo
}

# Interactive deployment selection
select_deployment() {
    show_deployment_options
    
    while true; do
        echo -n "Select deployment option (1-5): "
        read -r choice
        
        case $choice in
            1)
                if check_docker; then
                    start_services "docker-demo"
                else
                    start_services "python-demo"
                fi
                break
                ;;
            2)
                if check_docker; then
                    start_services "docker-vllm-cpu"
                else
                    log_error "Docker required for vLLM deployment"
                    continue
                fi
                break
                ;;
            3)
                if check_docker; then
                    start_services "docker-vllm-gpu"
                else
                    log_error "Docker required for GPU deployment"
                    continue
                fi
                break
                ;;
            4)
                if check_docker; then
                    start_services "docker-production"
                else
                    log_error "Docker required for production deployment"
                    continue
                fi
                break
                ;;
            5)
                start_services "python-demo"
                break
                ;;
            *)
                log_error "Invalid option. Please select 1-5."
                ;;
        esac
    done
}

# Show system status
show_status() {
    echo
    log_header "System Status"
    echo
    
    # Check backend
    if curl -s http://localhost:12000/api/v2/status > /dev/null 2>&1; then
        log_success "✅ Backend API: Online"
        
        # Get detailed status
        STATUS=$(curl -s http://localhost:12000/api/v2/status | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f\"   Mode: {'Production' if not data.get('demo_mode', True) else 'Demo'}\"
    print(f\"   Infrastructure: {data.get('infrastructure', 'Unknown')}\")
    print(f\"   Cost: {data.get('cost', 'Unknown')}\")
except:
    pass
")
        echo "$STATUS"
    else
        log_error "❌ Backend API: Offline"
    fi
    
    # Check vLLM server
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        log_success "✅ vLLM Server: Online"
    else
        log_info "⏸️ vLLM Server: Not running (Demo mode)"
    fi
    
    # Check Docker containers
    if command -v docker &> /dev/null; then
        CONTAINERS=$(docker ps --filter "name=enhanced-codeagent" --format "table {{.Names}}\t{{.Status}}" 2>/dev/null || echo "")
        if [ ! -z "$CONTAINERS" ]; then
            echo
            log_info "Docker Containers:"
            echo "$CONTAINERS"
        fi
    fi
    
    echo
    log_info "Access Points:"
    log_info "  🌐 Main Interface: http://localhost:12000"
    log_info "  📚 API Documentation: http://localhost:12000/docs"
    log_info "  🔧 System Status: http://localhost:12000/api/v2/status"
    
    if curl -s http://localhost:3000 > /dev/null 2>&1; then
        log_info "  🎨 Frontend: http://localhost:3000"
    fi
    
    if curl -s http://localhost:3001 > /dev/null 2>&1; then
        log_info "  📊 Monitoring: http://localhost:3001"
    fi
}

# Main execution
main() {
    print_header
    
    # Parse command line arguments
    case "${1:-}" in
        "demo")
            check_directory
            detect_system
            install_dependencies
            if check_docker; then
                start_services "docker-demo"
            else
                start_services "python-demo"
            fi
            ;;
        "cpu")
            check_directory
            detect_system
            install_dependencies
            start_services "docker-vllm-cpu"
            ;;
        "gpu")
            check_directory
            detect_system
            install_dependencies
            start_services "docker-vllm-gpu"
            ;;
        "production")
            check_directory
            detect_system
            install_dependencies
            start_services "docker-production"
            ;;
        "status")
            show_status
            exit 0
            ;;
        "stop")
            log_info "Stopping Enhanced CodeAgent v2.0..."
            docker-compose -f docker-compose-v2.yml down 2>/dev/null || true
            pkill -f "backend-v2/main.py" 2>/dev/null || true
            log_success "Services stopped"
            exit 0
            ;;
        "help"|"-h"|"--help")
            echo "Enhanced CodeAgent Integration v2.0 Startup Script"
            echo
            echo "Usage: $0 [COMMAND]"
            echo
            echo "Commands:"
            echo "  demo        Start in demo mode (cost-free)"
            echo "  cpu         Start with CPU vLLM server"
            echo "  gpu         Start with GPU vLLM server"
            echo "  production  Start full production stack"
            echo "  status      Show system status"
            echo "  stop        Stop all services"
            echo "  help        Show this help message"
            echo
            echo "If no command is provided, interactive mode will be used."
            exit 0
            ;;
        "")
            # Interactive mode
            check_directory
            detect_system
            install_dependencies
            select_deployment
            ;;
        *)
            log_error "Unknown command: $1"
            log_info "Use '$0 help' for usage information"
            exit 1
            ;;
    esac
    
    # Show final status
    sleep 3
    show_status
    
    echo
    log_success "Enhanced CodeAgent Integration v2.0 is ready!"
    log_info "🎉 Production-ready vLLM infrastructure deployed"
    log_info "💰 Cost-optimized architecture with demo mode"
    log_info "🚀 Ready for seamless production scaling"
}

# Execute main function
main "$@"