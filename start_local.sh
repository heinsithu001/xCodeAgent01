#!/bin/bash
# Simple Local Startup Script for xCodeAgent
# Fixes frontend-backend integration issues

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting xCodeAgent Local Development Environment${NC}"
echo

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 is required but not installed${NC}"
    exit 1
fi

# Install dependencies if needed
echo -e "${YELLOW}📦 Installing dependencies...${NC}"
pip install -q fastapi uvicorn aiohttp psutil pydantic

# Kill any existing processes on our ports
echo -e "${YELLOW}🧹 Cleaning up existing processes...${NC}"
pkill -f "uvicorn.*:8000" 2>/dev/null || true
pkill -f "uvicorn.*:12000" 2>/dev/null || true
sleep 2

# Start vLLM mock server
echo -e "${BLUE}🤖 Starting Mock vLLM Server on port 8000...${NC}"
python3 enhanced_mock_vllm_server.py &
VLLM_PID=$!
echo "Mock vLLM Server PID: $VLLM_PID"

# Wait for vLLM server to start
echo -e "${YELLOW}⏳ Waiting for vLLM server to start...${NC}"
sleep 3

# Test vLLM server
if curl -s http://localhost:8000/health > /dev/null; then
    echo -e "${GREEN}✅ Mock vLLM Server is running${NC}"
else
    echo -e "${RED}❌ Mock vLLM Server failed to start${NC}"
    kill $VLLM_PID 2>/dev/null || true
    exit 1
fi

# Start backend server
echo -e "${BLUE}🔧 Starting Unified Backend on port 12000...${NC}"
python3 unified_backend.py &
BACKEND_PID=$!
echo "Backend Server PID: $BACKEND_PID"

# Wait for backend server to start
echo -e "${YELLOW}⏳ Waiting for backend server to start...${NC}"
sleep 3

# Test backend server
if curl -s http://localhost:12000/health > /dev/null; then
    echo -e "${GREEN}✅ Backend Server is running${NC}"
else
    echo -e "${RED}❌ Backend Server failed to start${NC}"
    kill $VLLM_PID $BACKEND_PID 2>/dev/null || true
    exit 1
fi

# Test API endpoints
echo -e "${YELLOW}🧪 Testing API endpoints...${NC}"

# Test status endpoint
if curl -s http://localhost:12000/api/v3/status | grep -q "success"; then
    echo -e "${GREEN}✅ Status endpoint working${NC}"
else
    echo -e "${RED}❌ Status endpoint failed${NC}"
fi

# Save process IDs for cleanup
echo "$VLLM_PID" > .vllm_pid
echo "$BACKEND_PID" > .backend_pid

echo
echo -e "${GREEN}🎉 xCodeAgent is now running!${NC}"
echo
echo -e "${BLUE}📊 Service URLs:${NC}"
echo "   • Frontend:     http://localhost:12000"
echo "   • Backend API:  http://localhost:12000/api/v3"
echo "   • API Docs:     http://localhost:12000/docs"
echo "   • vLLM Mock:    http://localhost:8000"
echo
echo -e "${BLUE}🔧 Test Commands:${NC}"
echo "   • Status:       curl http://localhost:12000/api/v3/status"
echo "   • Chat Test:    curl -X POST http://localhost:12000/api/v3/chat -H 'Content-Type: application/json' -d '{\"message\":\"Hello\"}'"
echo
echo -e "${YELLOW}⚠️  To stop the servers, run: ./stop_local.sh${NC}"
echo

# Create stop script
cat > stop_local.sh << 'EOF'
#!/bin/bash
echo "🛑 Stopping xCodeAgent servers..."

if [ -f .vllm_pid ]; then
    VLLM_PID=$(cat .vllm_pid)
    kill $VLLM_PID 2>/dev/null && echo "✅ Stopped vLLM server (PID: $VLLM_PID)"
    rm .vllm_pid
fi

if [ -f .backend_pid ]; then
    BACKEND_PID=$(cat .backend_pid)
    kill $BACKEND_PID 2>/dev/null && echo "✅ Stopped backend server (PID: $BACKEND_PID)"
    rm .backend_pid
fi

# Cleanup any remaining processes
pkill -f "uvicorn.*:8000" 2>/dev/null || true
pkill -f "uvicorn.*:12000" 2>/dev/null || true

echo "🎯 All servers stopped"
EOF

chmod +x stop_local.sh

echo -e "${GREEN}✨ Setup complete! Open http://localhost:12000 in your browser${NC}"