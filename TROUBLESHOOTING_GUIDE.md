# xCodeAgent Troubleshooting Guide

## 🔍 Issues Identified and Fixed

### 1. **API Endpoint Mismatch** ✅ FIXED
- **Problem**: Frontend called `/api/v3/status` and `/api/v3/chat` but backends used `/api/v1/` or `/api/v2/`
- **Solution**: Created `unified_backend.py` with correct `/api/v3/` endpoints

### 2. **Hardcoded Remote API URL** ✅ FIXED
- **Problem**: Frontend had hardcoded remote URL instead of localhost
- **Solution**: Created `config.js` with automatic environment detection

### 3. **vLLM Server Connection Issues** ✅ FIXED
- **Problem**: Backend couldn't connect to vLLM server
- **Solution**: Created `enhanced_mock_vllm_server.py` for testing

### 4. **Multiple Backend Confusion** ✅ FIXED
- **Problem**: Multiple backend files with different APIs
- **Solution**: Unified all functionality in `unified_backend.py`

## 🚀 Quick Start (Fixed Version)

### Option 1: Simple Local Setup
```bash
# Start both servers with one command
./start_local.sh

# Access the application
open http://localhost:12000
```

### Option 2: Manual Setup
```bash
# Terminal 1: Start vLLM Mock Server
python3 enhanced_mock_vllm_server.py

# Terminal 2: Start Backend
python3 unified_backend.py

# Access: http://localhost:12000
```

## 🧪 Testing the Fix

### 1. Test Backend Health
```bash
curl http://localhost:12000/health
# Expected: {"status":"healthy","timestamp":"..."}
```

### 2. Test API Status
```bash
curl http://localhost:12000/api/v3/status
# Expected: {"success":true,"status":"operational",...}
```

### 3. Test Chat Endpoint
```bash
curl -X POST http://localhost:12000/api/v3/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"Hello, write a Python function"}'
# Expected: {"success":true,"session_id":"...","data":{"response":"..."}}
```

### 4. Test vLLM Mock Server
```bash
curl http://localhost:8000/health
# Expected: {"status":"healthy","model":"deepseek-ai/DeepSeek-R1-0528",...}
```

## 🔧 Configuration Files

### Frontend Configuration (`frontend-v2/config.js`)
- Automatically detects environment (localhost vs production)
- Sets correct API base URL
- Enables debug mode for localhost

### Backend Configuration (`unified_backend.py`)
- Unified API with correct endpoints
- Proper CORS configuration
- vLLM client with fallback to demo mode
- Session management

### Mock vLLM Server (`enhanced_mock_vllm_server.py`)
- Simulates DeepSeek R1 responses
- Context-aware responses based on prompt type
- Compatible with vLLM API format

## 🐛 Common Issues and Solutions

### Issue: "Connection refused" on port 8000
**Solution**: Start the vLLM mock server first
```bash
python3 enhanced_mock_vllm_server.py
```

### Issue: "Connection refused" on port 12000
**Solution**: Start the unified backend
```bash
python3 unified_backend.py
```

### Issue: Frontend shows "Disconnected"
**Causes**:
1. Backend not running on port 12000
2. API endpoints not matching
3. CORS issues

**Solution**: Use the fixed setup with `unified_backend.py`

### Issue: Chat not working
**Check**:
1. Backend logs for errors
2. Browser console for JavaScript errors
3. API endpoint responses

### Issue: vLLM server connection failed
**Solutions**:
1. Use mock server for testing: `python3 enhanced_mock_vllm_server.py`
2. Check if real vLLM server is running on port 8000
3. Backend will fallback to demo mode if vLLM fails

## 📊 Service Architecture (Fixed)

```
Frontend (Browser)
    ↓ HTTP requests to localhost:12000
Unified Backend (port 12000)
    ↓ HTTP requests to localhost:8000
vLLM Server / Mock Server (port 8000)
```

### API Endpoints (Fixed)
- `GET /` - Serves frontend
- `GET /health` - Backend health check
- `GET /api/v3/status` - System status (matches frontend)
- `POST /api/v3/chat` - Chat endpoint (matches frontend)
- `POST /api/v3/generate-code` - Code generation
- `GET /docs` - API documentation

## 🔄 Environment Variables

### Backend (`unified_backend.py`)
```bash
VLLM_SERVER_URL=http://localhost:8000  # vLLM server URL
BACKEND_HOST=0.0.0.0                   # Backend host
BACKEND_PORT=12000                     # Backend port
```

### Frontend (automatic detection)
- Localhost: `http://localhost:12000`
- Production: Uses current hostname

## 📝 Development Workflow

### 1. Start Development Environment
```bash
./start_local.sh
```

### 2. Make Changes
- Frontend: Edit `frontend-v2/index.html`
- Backend: Edit `unified_backend.py`
- vLLM: Edit `enhanced_mock_vllm_server.py`

### 3. Restart Services
```bash
./stop_local.sh
./start_local.sh
```

### 4. Test Changes
- Open http://localhost:12000
- Check browser console for errors
- Test API endpoints with curl

## 🚨 Emergency Fixes

### If nothing works:
1. Kill all processes: `pkill -f uvicorn`
2. Install dependencies: `pip install -r requirements_fixed.txt`
3. Start fresh: `./start_local.sh`

### If ports are busy:
```bash
# Find processes using ports
lsof -i :8000
lsof -i :12000

# Kill specific processes
kill -9 <PID>
```

### If frontend doesn't load:
1. Check if `frontend-v2/index.html` exists
2. Check if `frontend-v2/config.js` exists
3. Restart backend: `python3 unified_backend.py`

## 📈 Performance Tips

### For better performance:
1. Use real vLLM server instead of mock
2. Enable caching in backend
3. Use production ASGI server (gunicorn)
4. Add Redis for session storage

### For production deployment:
1. Use Docker containers
2. Set up reverse proxy (nginx)
3. Enable HTTPS
4. Configure monitoring

## 🎯 Success Indicators

✅ **All systems working when you see**:
- Mock vLLM Server: "Starting Enhanced Mock vLLM Server on port 8000"
- Backend: "Starting xCodeAgent Unified Backend"
- Frontend loads at http://localhost:12000
- Status indicator shows "Connected"
- Chat responses work

## 📞 Support

If you encounter issues not covered here:
1. Check the logs in terminal
2. Test individual components
3. Verify all files are in place
4. Try the emergency fixes above