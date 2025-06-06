# xCodeAgent Full Stack Production Guide

## 🚀 **Complete Production Setup with Real DeepSeek-R1-0528**

This guide provides step-by-step instructions for deploying the complete xCodeAgent stack with the real DeepSeek-R1-0528 model via vLLM server for end-to-end validation.

## 📋 **Quick Start**

### **Automated Deployment**
```bash
# One-command deployment
./start_production_full_stack.sh
```

### **Manual Deployment**
```bash
# 1. Install dependencies
pip install -r requirements_production.txt

# 2. Start vLLM server
python3 production_vllm_server.py

# 3. Start backend (in new terminal)
python3 production_unified_backend.py

# 4. Test everything
python3 test_full_stack.py
```

## 🧪 **End-to-End Testing Scenarios**

### **Scenario 1: Basic Chat Functionality**
```bash
# Test production mode chat
curl -X POST http://localhost:12000/api/v3/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Write a Python function to implement quicksort algorithm",
    "execution_mode": "production",
    "temperature": 0.1,
    "max_tokens": 1024
  }'
```

### **Scenario 2: Code Generation**
```bash
# Test code generation
curl -X POST http://localhost:12000/api/v3/generate-code \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Create a FastAPI endpoint for user authentication with JWT tokens",
    "language": "python",
    "complexity": "advanced",
    "include_tests": true
  }'
```

### **Scenario 3: Code Analysis**
```bash
# Test code analysis
curl -X POST http://localhost:12000/api/v3/analyze-code \
  -H "Content-Type: application/json" \
  -d '{
    "code": "def factorial(n):\n    if n <= 1:\n        return 1\n    return n * factorial(n-1)",
    "analysis_type": "performance",
    "include_suggestions": true
  }'
```

## 📊 **Performance Validation**

### **Expected Performance Metrics**
- **vLLM Health Check**: < 1 second
- **Backend Status**: < 2 seconds  
- **Chat Response**: 5-30 seconds (depending on complexity)
- **Code Generation**: 10-60 seconds
- **Code Analysis**: 5-20 seconds

### **Resource Usage**
- **GPU Memory**: 20-40GB (for DeepSeek-R1-0528)
- **System RAM**: 16-32GB
- **CPU Usage**: 20-80% during inference
- **Disk I/O**: High during model loading

## 🔍 **Validation Checklist**

### **Infrastructure Validation**
- [ ] vLLM server starts without errors
- [ ] DeepSeek-R1-0528 model loads successfully
- [ ] Backend connects to vLLM server
- [ ] Frontend serves correctly
- [ ] All ports are accessible

### **API Validation**
- [ ] `/health` endpoints respond
- [ ] `/api/v3/status` shows healthy status
- [ ] `/api/v3/chat` produces real AI responses
- [ ] `/api/v3/generate-code` creates valid code
- [ ] `/api/v3/analyze-code` provides insights

### **Frontend Validation**
- [ ] Frontend loads without JavaScript errors
- [ ] Chat interface is functional
- [ ] Status indicator shows "Connected"
- [ ] Real-time responses work
- [ ] Session management works

### **Integration Validation**
- [ ] Frontend → Backend communication works
- [ ] Backend → vLLM communication works
- [ ] Error handling works correctly
- [ ] Fallback modes function
- [ ] Performance is acceptable

## 🚨 **Common Issues and Solutions**

### **Issue: vLLM Server Won't Start**
**Symptoms**: Connection refused on port 8000
**Solutions**:
```bash
# Check GPU availability
nvidia-smi

# Check memory
free -h

# Try CPU mode
python3 production_vllm_server.py --device cpu

# Check logs
tail -f logs/vllm_server.log
```

### **Issue: Model Loading Takes Too Long**
**Symptoms**: Server starts but health check fails
**Solutions**:
```bash
# Monitor progress
tail -f logs/vllm_server.log | grep -i "loading\|download"

# Check internet connection
ping huggingface.co

# Pre-download model
python3 -c "from transformers import AutoTokenizer; AutoTokenizer.from_pretrained('deepseek-ai/DeepSeek-R1-0528', trust_remote_code=True)"
```

### **Issue: Backend Can't Connect to vLLM**
**Symptoms**: Backend status shows vLLM as unreachable
**Solutions**:
```bash
# Verify vLLM is running
curl http://localhost:8000/health

# Check backend configuration
export VLLM_SERVER_URL="http://localhost:8000"

# Test connection manually
python3 -c "import requests; print(requests.get('http://localhost:8000/health').json())"
```

### **Issue: Frontend Shows "Disconnected"**
**Symptoms**: Status indicator red, API calls fail
**Solutions**:
```bash
# Check backend is running
curl http://localhost:12000/health

# Verify API endpoints
curl http://localhost:12000/api/v3/status

# Check browser console for errors
# Open browser dev tools → Console
```

## 📈 **Performance Optimization**

### **GPU Optimization**
```bash
# Use multiple GPUs
--tensor-parallel-size 2

# Optimize memory usage
--gpu-memory-utilization 0.85

# Enable optimizations
--enable-chunked-prefill
```

### **Backend Optimization**
```python
# Increase timeout for large models
self.timeout = 120

# Optimize batch processing
max_num_seqs = 256
max_num_batched_tokens = 8192
```

### **Frontend Optimization**
```javascript
// Increase timeout for production mode
const PRODUCTION_TIMEOUT = 120000; // 2 minutes

// Add loading indicators
showLoadingSpinner();
```

## 🔄 **Continuous Testing**

### **Automated Testing Script**
```bash
#!/bin/bash
# continuous_test.sh

while true; do
    echo "Running full stack tests..."
    python3 test_full_stack.py --output test_results_$(date +%Y%m%d_%H%M%S).json
    
    if [ $? -eq 0 ]; then
        echo "✅ All tests passed"
    else
        echo "❌ Some tests failed"
        # Send alert or notification
    fi
    
    sleep 300  # Test every 5 minutes
done
```

### **Health Monitoring**
```bash
#!/bin/bash
# health_monitor.sh

check_service() {
    local service=$1
    local url=$2
    
    if curl -s "$url" > /dev/null; then
        echo "✅ $service is healthy"
        return 0
    else
        echo "❌ $service is down"
        return 1
    fi
}

check_service "vLLM Server" "http://localhost:8000/health"
check_service "Backend" "http://localhost:12000/health"
check_service "API Status" "http://localhost:12000/api/v3/status"
```

## 📊 **Monitoring Dashboard**

### **Key Metrics to Monitor**
1. **Response Times**
   - vLLM health check: < 1s
   - Backend status: < 2s
   - Chat responses: < 30s

2. **Resource Usage**
   - GPU utilization: 70-90%
   - GPU memory: < 95%
   - System RAM: < 80%
   - CPU usage: < 90%

3. **Error Rates**
   - API success rate: > 95%
   - Model inference success: > 98%
   - Frontend load success: > 99%

4. **Throughput**
   - Requests per minute
   - Tokens per second
   - Concurrent users

### **Monitoring Commands**
```bash
# GPU monitoring
watch -n 1 nvidia-smi

# System monitoring
htop

# Network monitoring
netstat -tulpn | grep -E "(8000|12000)"

# Log monitoring
tail -f logs/vllm_server.log logs/backend.log
```

## 🎯 **Success Criteria**

Your full stack deployment is successful when:

### **Technical Criteria**
- ✅ All services start without errors
- ✅ Health checks pass consistently
- ✅ API endpoints respond correctly
- ✅ Real AI responses are generated
- ✅ Performance meets expectations
- ✅ Error handling works properly

### **Functional Criteria**
- ✅ Users can chat with the AI
- ✅ Code generation produces valid code
- ✅ Code analysis provides insights
- ✅ Session management works
- ✅ Frontend is responsive and functional

### **Performance Criteria**
- ✅ Response times are acceptable
- ✅ Resource usage is within limits
- ✅ System remains stable under load
- ✅ No memory leaks or crashes

## 🚀 **Next Steps After Successful Deployment**

1. **Load Testing**
   ```bash
   # Install load testing tools
   pip install locust
   
   # Run load tests
   locust -f load_test.py --host http://localhost:12000
   ```

2. **Security Hardening**
   - Enable HTTPS
   - Add authentication
   - Implement rate limiting
   - Set up firewall rules

3. **Production Monitoring**
   - Set up Prometheus/Grafana
   - Configure alerting
   - Implement log aggregation
   - Add health checks

4. **Scaling Preparation**
   - Document current performance
   - Plan horizontal scaling
   - Prepare load balancing
   - Design backup strategies

## 📞 **Support and Troubleshooting**

If you encounter issues:

1. **Check the logs**:
   ```bash
   tail -f logs/vllm_server.log
   tail -f logs/backend.log
   ```

2. **Run diagnostics**:
   ```bash
   python3 test_full_stack.py --output diagnostics.json
   ```

3. **Verify system resources**:
   ```bash
   nvidia-smi  # GPU status
   free -h     # Memory usage
   df -h       # Disk space
   ```

4. **Test individual components**:
   ```bash
   curl http://localhost:8000/health    # vLLM
   curl http://localhost:12000/health   # Backend
   curl http://localhost:12000/         # Frontend
   ```

## 🎉 **Congratulations!**

If you've successfully completed this guide, you now have a fully functional xCodeAgent production environment with:

- ✅ Real DeepSeek-R1-0528 model running via vLLM
- ✅ Production backend with comprehensive API
- ✅ Functional frontend interface
- ✅ End-to-end integration and testing
- ✅ Monitoring and troubleshooting capabilities

Your system is ready for real-world AI-powered coding assistance!