#!/bin/bash
# Browser Testing Setup Script
# Optimized for current environment constraints

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

echo -e "${PURPLE}"
cat << "EOF"
╔══════════════════════════════════════════════════════════════════════════════╗
║                    xCodeAgent Browser Testing Setup                          ║
║                   Production-Like Environment for Testing                    ║
╚══════════════════════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

echo -e "${BLUE}🚀 Starting xCodeAgent for Browser Testing${NC}"

# Create logs directory
mkdir -p logs

# Clean up any existing processes
echo -e "${YELLOW}🧹 Cleaning up existing processes...${NC}"
pkill -f "uvicorn.*:8000" 2>/dev/null || true
pkill -f "uvicorn.*:12000" 2>/dev/null || true
sleep 2

# Install dependencies
echo -e "${YELLOW}📦 Installing dependencies...${NC}"
pip install -q fastapi uvicorn aiohttp psutil pydantic requests

# Start enhanced mock vLLM server (simulates DeepSeek-R1-0528)
echo -e "${BLUE}🤖 Starting Enhanced Mock vLLM Server (DeepSeek-R1-0528 Simulation)...${NC}"
python3 enhanced_mock_vllm_server.py > logs/vllm_mock.log 2>&1 &
VLLM_PID=$!
echo $VLLM_PID > .vllm_browser_pid
echo "Mock vLLM Server PID: $VLLM_PID"

# Wait for vLLM mock server
echo -e "${YELLOW}⏳ Waiting for mock vLLM server...${NC}"
sleep 3

# Test vLLM mock server
if curl -s http://localhost:8000/health > /dev/null; then
    echo -e "${GREEN}✅ Mock vLLM Server is running${NC}"
else
    echo -e "${RED}❌ Mock vLLM Server failed to start${NC}"
    exit 1
fi

# Start production backend (configured for mock vLLM)
echo -e "${BLUE}🔧 Starting Production Backend...${NC}"
export VLLM_SERVER_URL="http://localhost:8000"
export BACKEND_HOST="0.0.0.0"
export BACKEND_PORT="12000"
export PRODUCTION_MODE="true"

python3 production_unified_backend.py > logs/backend.log 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > .backend_browser_pid
echo "Backend Server PID: $BACKEND_PID"

# Wait for backend
echo -e "${YELLOW}⏳ Waiting for backend server...${NC}"
sleep 5

# Test backend
if curl -s http://localhost:12000/health > /dev/null; then
    echo -e "${GREEN}✅ Backend Server is running${NC}"
else
    echo -e "${RED}❌ Backend Server failed to start${NC}"
    exit 1
fi

# Test API endpoints
echo -e "${YELLOW}🧪 Testing API endpoints...${NC}"

# Test status
if curl -s http://localhost:12000/api/v3/status | grep -q "success"; then
    echo -e "${GREEN}✅ Status endpoint working${NC}"
else
    echo -e "${RED}❌ Status endpoint failed${NC}"
fi

# Test chat endpoint
echo -e "${YELLOW}🧪 Testing chat endpoint...${NC}"
CHAT_RESPONSE=$(curl -s -X POST http://localhost:12000/api/v3/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"Hello, test message","execution_mode":"production"}')

if echo "$CHAT_RESPONSE" | grep -q '"success":true'; then
    echo -e "${GREEN}✅ Chat endpoint working${NC}"
else
    echo -e "${RED}❌ Chat endpoint failed${NC}"
fi

# Create stop script
cat > stop_browser_testing.sh << 'EOF'
#!/bin/bash
echo "🛑 Stopping browser testing servers..."

if [ -f .vllm_browser_pid ]; then
    VLLM_PID=$(cat .vllm_browser_pid)
    kill $VLLM_PID 2>/dev/null && echo "✅ Stopped mock vLLM server (PID: $VLLM_PID)"
    rm .vllm_browser_pid
fi

if [ -f .backend_browser_pid ]; then
    BACKEND_PID=$(cat .backend_browser_pid)
    kill $BACKEND_PID 2>/dev/null && echo "✅ Stopped backend server (PID: $BACKEND_PID)"
    rm .backend_browser_pid
fi

pkill -f "uvicorn.*:8000" 2>/dev/null || true
pkill -f "uvicorn.*:12000" 2>/dev/null || true

echo "🎯 All servers stopped"
EOF

chmod +x stop_browser_testing.sh

echo
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                    🎉 BROWSER TESTING READY! 🎉                             ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════════════════════╝${NC}"
echo
echo -e "${BLUE}🌐 Access URLs:${NC}"
echo "   • Frontend Application:  http://localhost:12000"
echo "   • API Documentation:     http://localhost:12000/docs"
echo "   • Backend Status:        http://localhost:12000/api/v3/status"
echo "   • Mock vLLM Health:      http://localhost:8000/health"
echo
echo -e "${BLUE}🧪 Testing Features:${NC}"
echo "   • Chat Interface with AI responses"
echo "   • Code Generation capabilities"
echo "   • Code Analysis features"
echo "   • Real-time status monitoring"
echo "   • Session management"
echo
echo -e "${BLUE}💡 Testing Modes:${NC}"
echo "   • Production Mode: Uses enhanced mock DeepSeek-R1-0528"
echo "   • Demo Mode: Quick responses for UI testing"
echo "   • Hybrid Mode: Fallback capabilities"
echo
echo -e "${BLUE}📋 Logs:${NC}"
echo "   • Mock vLLM: tail -f logs/vllm_mock.log"
echo "   • Backend:   tail -f logs/backend.log"
echo
echo -e "${YELLOW}⚠️  To stop servers: ./stop_browser_testing.sh${NC}"
echo
echo -e "${GREEN}✨ Ready for browser testing! Open http://localhost:12000${NC}"