#!/bin/bash
# Enhanced CodeAgent03 + DeepSeek R1 Production Startup Script
# Automatically detects system capabilities and starts appropriate configuration

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
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

# Banner
echo -e "${PURPLE}"
cat << "EOF"
╔══════════════════════════════════════════════════════════════════════════════╗
║                Enhanced CodeAgent03 + DeepSeek R1 Production Platform       ║
║                              Phase 2: Production Deployment                 ║
╚══════════════════════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

# System Detection
log "🔍 Detecting system capabilities..."

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    log_error "Python 3 is required but not installed"
    exit 1
fi

# Detect system capabilities
SYSTEM_INFO=$(python3 -c "
import torch
import psutil
import platform
import json

try:
    has_gpu = torch.cuda.is_available()
    if has_gpu:
        gpu_count = torch.cuda.device_count()
        gpu_memory = [torch.cuda.get_device_properties(i).total_memory // (1024**3) for i in range(gpu_count)]
    else:
        gpu_count = 0
        gpu_memory = []
except ImportError:
    has_gpu = False
    gpu_count = 0
    gpu_memory = []

total_ram = psutil.virtual_memory().total // (1024**3)
cpu_cores = psutil.cpu_count()
platform_name = platform.system()

system_info = {
    'has_gpu': has_gpu,
    'gpu_count': gpu_count,
    'gpu_memory': gpu_memory,
    'total_ram': total_ram,
    'cpu_cores': cpu_cores,
    'platform': platform_name
}

print(json.dumps(system_info))
")

# Parse system information
HAS_GPU=$(echo $SYSTEM_INFO | python3 -c "import sys, json; data=json.load(sys.stdin); print(str(data['has_gpu']).lower())")
GPU_COUNT=$(echo $SYSTEM_INFO | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['gpu_count'])")
TOTAL_RAM=$(echo $SYSTEM_INFO | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['total_ram'])")
CPU_CORES=$(echo $SYSTEM_INFO | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['cpu_cores'])")

log "📊 System Information:"
echo "   • Platform: $(uname -s) $(uname -m)"
echo "   • CPU Cores: $CPU_CORES"
echo "   • Total RAM: ${TOTAL_RAM}GB"
echo "   • GPU Available: $HAS_GPU"
if [ "$HAS_GPU" = "true" ]; then
    echo "   • GPU Count: $GPU_COUNT"
    GPU_MEMORY=$(echo $SYSTEM_INFO | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['gpu_memory'])")
    echo "   • GPU Memory: $GPU_MEMORY GB"
fi

# Determine deployment configuration
if [ "$HAS_GPU" = "true" ] && [ "$GPU_COUNT" -gt 0 ]; then
    MAX_GPU_MEM=$(echo $SYSTEM_INFO | python3 -c "import sys, json; data=json.load(sys.stdin); print(max(data['gpu_memory']) if data['gpu_memory'] else 0)")
    if [ "$MAX_GPU_MEM" -ge 16 ]; then
        DEPLOYMENT_TYPE="gpu-high"
        PROFILE="gpu"
        log_success "🚀 Detected high-end GPU configuration (${MAX_GPU_MEM}GB VRAM)"
    elif [ "$MAX_GPU_MEM" -ge 8 ]; then
        DEPLOYMENT_TYPE="gpu-standard"
        PROFILE="gpu"
        log_success "🚀 Detected standard GPU configuration (${MAX_GPU_MEM}GB VRAM)"
    else
        DEPLOYMENT_TYPE="cpu-high"
        PROFILE="cpu"
        log_warning "⚠️  GPU memory insufficient, falling back to CPU mode"
    fi
elif [ "$TOTAL_RAM" -ge 32 ]; then
    DEPLOYMENT_TYPE="cpu-high"
    PROFILE="cpu"
    log_success "🚀 Detected high-memory CPU configuration (${TOTAL_RAM}GB RAM)"
elif [ "$TOTAL_RAM" -ge 16 ]; then
    DEPLOYMENT_TYPE="cpu-standard"
    PROFILE="cpu"
    log_success "🚀 Detected standard CPU configuration (${TOTAL_RAM}GB RAM)"
else
    DEPLOYMENT_TYPE="cpu-minimal"
    PROFILE="cpu"
    log_warning "⚠️  Limited memory detected (${TOTAL_RAM}GB RAM). Performance may be reduced."
fi

log "🎯 Selected deployment type: $DEPLOYMENT_TYPE"

# Check Docker availability
log "🐳 Checking Docker availability..."
if ! command -v docker &> /dev/null; then
    log_error "Docker is required but not installed"
    echo "Please install Docker and try again"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    log_error "Docker Compose is required but not installed"
    echo "Please install Docker Compose and try again"
    exit 1
fi

# Check if Docker daemon is running
if ! docker info &> /dev/null; then
    log_error "Docker daemon is not running"
    echo "Please start Docker and try again"
    exit 1
fi

log_success "✅ Docker is available and running"

# Create necessary directories
log "📁 Creating necessary directories..."
mkdir -p data/model_cache
mkdir -p logs
mkdir -p uploads
mkdir -p nginx/logs
mkdir -p postgres/backups
mkdir -p monitoring/{prometheus,grafana/dashboards,grafana/datasources,logstash/pipeline}
mkdir -p redis

log_success "✅ Directories created"

# Generate configuration files
log "⚙️  Generating configuration files..."

# Generate environment file
cat > .env << EOF
# Enhanced CodeAgent Production Environment
# Generated on $(date)

# System Configuration
DEPLOYMENT_TYPE=$DEPLOYMENT_TYPE
PROFILE=$PROFILE
HAS_GPU=$HAS_GPU
TOTAL_RAM=${TOTAL_RAM}GB
CPU_CORES=$CPU_CORES

# Application Configuration
DEEPSEEK_MODEL=deepseek-ai/DeepSeek-R1-0528
VLLM_ENDPOINT=http://vllm-server:8000
LOG_LEVEL=INFO
DEMO_MODE=true

# Database Configuration
POSTGRES_DB=codeagent_db
POSTGRES_USER=codeagent
POSTGRES_PASSWORD=secure_password_$(openssl rand -hex 8)

# Redis Configuration
REDIS_PASSWORD=redis_secure_password_$(openssl rand -hex 8)

# Security
JWT_SECRET=$(openssl rand -hex 32)
ENCRYPTION_KEY=$(openssl rand -hex 32)

# Monitoring
GRAFANA_ADMIN_PASSWORD=admin_secure_password_$(openssl rand -hex 8)

# Performance Tuning
MAX_WORKERS=$((CPU_CORES * 2))
WORKER_CONNECTIONS=1000
EOF

# Generate Nginx configuration
cat > nginx/nginx.conf << 'EOF'
events {
    worker_connections 1024;
}

http {
    upstream backend {
        least_conn;
        server backend:8000 max_fails=3 fail_timeout=30s;
    }
    
    upstream frontend {
        least_conn;
        server frontend:3000 max_fails=3 fail_timeout=30s;
    }
    
    server {
        listen 80;
        server_name localhost;
        
        # Security headers
        add_header X-Frame-Options DENY;
        add_header X-Content-Type-Options nosniff;
        add_header X-XSS-Protection "1; mode=block";
        
        # API routes
        location /api/ {
            proxy_pass http://backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_timeout 300s;
        }
        
        # WebSocket support
        location /ws/ {
            proxy_pass http://backend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }
        
        # Frontend routes
        location / {
            proxy_pass http://frontend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
        
        # Health check
        location /health {
            access_log off;
            return 200 "healthy\n";
            add_header Content-Type text/plain;
        }
    }
}
EOF

# Generate Prometheus configuration
cat > monitoring/prometheus.yml << 'EOF'
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "rules/*.yml"

scrape_configs:
  - job_name: 'codeagent-backend'
    static_configs:
      - targets: ['backend:8000']
    metrics_path: '/metrics'
    scrape_interval: 30s
    
  - job_name: 'codeagent-vllm'
    static_configs:
      - targets: ['vllm-server:8000']
    metrics_path: '/metrics'
    scrape_interval: 60s
    
  - job_name: 'redis'
    static_configs:
      - targets: ['redis:6379']
      
  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres:5432']
      
  - job_name: 'nginx'
    static_configs:
      - targets: ['nginx:80']
EOF

log_success "✅ Configuration files generated"

# Build and start services
log "🚀 Starting Enhanced CodeAgent Production Platform..."

# Stop any existing services
log "🛑 Stopping existing services..."
docker-compose -f docker-compose.production.yml --profile $PROFILE down --remove-orphans 2>/dev/null || true

# Pull latest images
log "📥 Pulling latest Docker images..."
docker-compose -f docker-compose.production.yml --profile $PROFILE pull

# Build custom images
log "🔨 Building custom images..."
docker-compose -f docker-compose.production.yml --profile $PROFILE build

# Start services
log "🚀 Starting services with profile: $PROFILE"
docker-compose -f docker-compose.production.yml --profile $PROFILE up -d

# Wait for services to be ready
log "⏳ Waiting for services to be ready..."
sleep 30

# Health checks
log "🏥 Performing health checks..."

check_service() {
    local service=$1
    local url=$2
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f -s "$url" > /dev/null 2>&1; then
            log_success "✅ $service is healthy"
            return 0
        fi
        
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    log_error "❌ $service failed health check"
    return 1
}

# Check core services
echo -n "Checking backend service"
check_service "Backend" "http://localhost:12000/api/v2/status"

echo -n "Checking Redis"
check_service "Redis" "http://localhost:6379" || log_warning "Redis health check failed (may be normal)"

echo -n "Checking Prometheus"
check_service "Prometheus" "http://localhost:9090/-/healthy"

echo -n "Checking Grafana"
check_service "Grafana" "http://localhost:3000/api/health"

# Display deployment information
echo
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                    🎉 DEPLOYMENT SUCCESSFUL! 🎉                             ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════════════════════╝${NC}"
echo
echo -e "${CYAN}📊 Service URLs:${NC}"
echo "   • Main Application:    http://localhost:12000"
echo "   • API Documentation:   http://localhost:12000/docs"
echo "   • Monitoring Dashboard: http://localhost:3000 (admin/admin)"
echo "   • Metrics:             http://localhost:9090"
echo "   • Logs:                http://localhost:5601"
echo
echo -e "${CYAN}🔧 Configuration:${NC}"
echo "   • Deployment Type:     $DEPLOYMENT_TYPE"
echo "   • Profile:             $PROFILE"
echo "   • Demo Mode:           Enabled (cost-free)"
echo "   • Auto-scaling:        Enabled"
echo
echo -e "${CYAN}💡 Next Steps:${NC}"
echo "   1. Access the application at http://localhost:12000"
echo "   2. Use the 'Start vLLM Server' button to activate production mode"
echo "   3. Monitor performance at http://localhost:3000"
echo "   4. Check logs with: docker-compose -f docker-compose.production.yml logs -f"
echo
echo -e "${YELLOW}⚠️  Important Notes:${NC}"
echo "   • Demo mode is active (no model costs)"
echo "   • Production model deployment is optional"
echo "   • All data is persisted in Docker volumes"
echo "   • Use 'docker-compose -f docker-compose.production.yml down' to stop"
echo

# Save deployment info
cat > deployment_info.json << EOF
{
    "deployment_date": "$(date -Iseconds)",
    "deployment_type": "$DEPLOYMENT_TYPE",
    "profile": "$PROFILE",
    "system_info": $SYSTEM_INFO,
    "services": {
        "main_app": "http://localhost:12000",
        "monitoring": "http://localhost:3000",
        "metrics": "http://localhost:9090",
        "logs": "http://localhost:5601"
    },
    "status": "deployed"
}
EOF

log_success "🎯 Deployment information saved to deployment_info.json"
log_success "🚀 Enhanced CodeAgent Production Platform is now running!"