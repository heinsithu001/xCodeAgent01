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
