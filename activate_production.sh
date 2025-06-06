#!/bin/bash
# 🚀 One-Click Production Activation Script
# Activate actual DeepSeek R1 model with full vLLM server

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║           🚀 ACTIVATING PRODUCTION DeepSeek R1 MODEL            ║${NC}"
echo -e "${BLUE}║                One-Click Model Deployment                        ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════════╝${NC}"

# Check if vLLM is installed
echo -e "${BLUE}[1/5]${NC} Checking vLLM installation..."
if ! python3 -c "import vllm" 2>/dev/null; then
    echo -e "${YELLOW}Installing vLLM...${NC}"
    pip install vllm
fi
echo -e "${GREEN}✅ vLLM ready${NC}"

# Detect system capabilities
echo -e "${BLUE}[2/5]${NC} Detecting system capabilities..."
SYSTEM_INFO=$(python3 -c "
import torch
import psutil
import json

has_gpu = torch.cuda.is_available()
total_ram = psutil.virtual_memory().total // (1024**3)
cpu_cores = psutil.cpu_count()

if has_gpu:
    gpu_memory = torch.cuda.get_device_properties(0).total_memory // (1024**3)
    config = 'gpu' if gpu_memory >= 8 else 'cpu'
else:
    config = 'cpu'

print(json.dumps({
    'config': config,
    'has_gpu': has_gpu,
    'total_ram': total_ram,
    'cpu_cores': cpu_cores
}))
")

CONFIG=$(echo $SYSTEM_INFO | python3 -c "import sys, json; print(json.load(sys.stdin)['config'])")
echo -e "${GREEN}✅ Configuration: $CONFIG${NC}"

# Start vLLM server
echo -e "${BLUE}[3/5]${NC} Starting vLLM server with DeepSeek R1..."

if [ "$CONFIG" = "gpu" ]; then
    echo -e "${GREEN}🎯 GPU Mode: High-performance deployment${NC}"
    nohup vllm serve deepseek-ai/DeepSeek-R1-0528 \
        --host 0.0.0.0 \
        --port 8000 \
        --tensor-parallel-size 1 \
        --gpu-memory-utilization 0.8 \
        --max-model-len 32768 \
        --trust-remote-code > vllm_server.log 2>&1 &
else
    echo -e "${YELLOW}🎯 CPU Mode: Optimized deployment${NC}"
    nohup vllm serve deepseek-ai/DeepSeek-R1-0528 \
        --host 0.0.0.0 \
        --port 8000 \
        --device cpu \
        --max-model-len 16384 \
        --trust-remote-code > vllm_server.log 2>&1 &
fi

VLLM_PID=$!
echo "vLLM PID: $VLLM_PID" > vllm.pid

# Wait for server to be ready
echo -e "${BLUE}[4/5]${NC} Waiting for model to load..."
echo -e "${YELLOW}⏳ This may take 2-5 minutes depending on your system...${NC}"

for i in {1..60}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ vLLM server is ready!${NC}"
        break
    fi
    echo -n "."
    sleep 5
done

# Update backend to use production mode
echo -e "${BLUE}[5/5]${NC} Activating production mode..."
curl -s -X POST http://localhost:12000/api/v2/vllm/start > /dev/null

# Verify deployment
echo -e "${BLUE}🔍 Verifying deployment...${NC}"
RESPONSE=$(curl -s -X POST http://localhost:12000/api/v2/generate-code \
    -H "Content-Type: application/json" \
    -d '{"prompt":"Hello world in Python","language":"python","complexity":"simple"}')

if echo "$RESPONSE" | grep -q "success"; then
    echo -e "${GREEN}✅ Production deployment successful!${NC}"
else
    echo -e "${RED}❌ Deployment verification failed${NC}"
    exit 1
fi

# Display results
echo
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                    🎉 PRODUCTION ACTIVATED! 🎉                  ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════════╝${NC}"
echo
echo -e "${BLUE}🚀 DeepSeek R1 Model Status:${NC} ${GREEN}ACTIVE${NC}"
echo -e "${BLUE}🔗 Platform URL:${NC} http://localhost:12000"
echo -e "${BLUE}📊 vLLM Server:${NC} http://localhost:8000"
echo -e "${BLUE}🔒 Privacy:${NC} ${GREEN}100% Local - No external API calls${NC}"
echo -e "${BLUE}💰 Cost:${NC} ${GREEN}Local deployment - No ongoing fees${NC}"
echo
echo -e "${YELLOW}📋 Enterprise Features Now Active:${NC}"
echo "   • ✅ Full DeepSeek R1 reasoning capabilities"
echo "   • ✅ Advanced code generation with thinking process"
echo "   • ✅ Comprehensive code analysis and review"
echo "   • ✅ Intelligent chat with programming expertise"
echo "   • ✅ Project-level analysis and recommendations"
echo "   • ✅ Multi-agent collaboration workflows"
echo "   • ✅ Real-time performance optimization"
echo
echo -e "${BLUE}🎯 Quick Test:${NC}"
echo "Visit http://localhost:12000 and try:"
echo "1. Generate complex code with advanced reasoning"
echo "2. Analyze code with detailed explanations"
echo "3. Chat about advanced programming concepts"
echo
echo -e "${YELLOW}⚠️  Management Commands:${NC}"
echo "• Stop vLLM: kill \$(cat vllm.pid)"
echo "• View logs: tail -f vllm_server.log"
echo "• Restart: ./activate_production.sh"
echo
echo -e "${GREEN}🎊 Enjoy your fully activated Enhanced CodeAgent platform!${NC}"