#!/bin/bash
# Stop Script for Enhanced CodeAgent Integration

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

log_info "Stopping Enhanced CodeAgent Integration..."

# Function to stop service by PID file
stop_service() {
    local service_name=$1
    local pid_file=$2
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 $pid 2>/dev/null; then
            log_info "Stopping $service_name (PID: $pid)..."
            kill $pid
            
            # Wait for process to stop
            for i in {1..10}; do
                if ! kill -0 $pid 2>/dev/null; then
                    log_success "$service_name stopped"
                    break
                fi
                if [ $i -eq 10 ]; then
                    log_warning "Force killing $service_name..."
                    kill -9 $pid 2>/dev/null || true
                fi
                sleep 1
            done
        else
            log_warning "$service_name PID file exists but process not running"
        fi
        rm -f "$pid_file"
    else
        log_info "No PID file found for $service_name"
    fi
}

# Stop API server
stop_service "API server" "logs/api.pid"

# Stop vLLM server
stop_service "vLLM server" "logs/vllm.pid"

# Kill any remaining processes by port
log_info "Checking for remaining processes..."

# Check for processes on vLLM port (8000)
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    log_warning "Found process still using port 8000, attempting to stop..."
    lsof -ti:8000 | xargs kill -9 2>/dev/null || true
fi

# Check for processes on API port (12000)
if lsof -Pi :12000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    log_warning "Found process still using port 12000, attempting to stop..."
    lsof -ti:12000 | xargs kill -9 2>/dev/null || true
fi

# Kill any remaining vLLM processes
pkill -f "vllm.entrypoints.openai.api_server" 2>/dev/null || true
pkill -f "enhanced-codeagent" 2>/dev/null || true

log_success "All services stopped"

# Clean up temporary files
log_info "Cleaning up temporary files..."
rm -f logs/*.pid
rm -f temp/*

log_success "Enhanced CodeAgent Integration stopped successfully"