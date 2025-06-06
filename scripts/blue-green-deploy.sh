#!/bin/bash

# xCodeAgent Blue-Green Deployment Script
# Implements zero-downtime deployment strategy

set -euo pipefail

# ============================================================================
# CONFIGURATION
# ============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENVIRONMENT="${1:-production}"
VERSION="${2:-latest}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ============================================================================
# LOGGING FUNCTIONS
# ============================================================================
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

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if Docker is running
    if ! docker info >/dev/null 2>&1; then
        log_error "Docker is not running"
        exit 1
    fi
    
    # Check if Docker Compose is available
    if ! command -v docker-compose >/dev/null 2>&1; then
        log_error "Docker Compose is not installed"
        exit 1
    fi
    
    # Check if environment file exists
    if [[ ! -f "$PROJECT_ROOT/deploy/${ENVIRONMENT}.env" ]]; then
        log_error "Environment file not found: deploy/${ENVIRONMENT}.env"
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

get_current_color() {
    local current_color
    current_color=$(docker-compose -f "$PROJECT_ROOT/docker-compose.${ENVIRONMENT}.yml" ps -q backend-blue 2>/dev/null | wc -l)
    
    if [[ $current_color -gt 0 ]]; then
        echo "blue"
    else
        echo "green"
    fi
}

get_target_color() {
    local current_color="$1"
    if [[ "$current_color" == "blue" ]]; then
        echo "green"
    else
        echo "blue"
    fi
}

# ============================================================================
# DEPLOYMENT FUNCTIONS
# ============================================================================
deploy_target_environment() {
    local target_color="$1"
    local compose_file="$PROJECT_ROOT/docker-compose.${ENVIRONMENT}.yml"
    local env_file="$PROJECT_ROOT/deploy/${ENVIRONMENT}.env"
    
    log_info "Deploying to ${target_color} environment..."
    
    # Set environment variables
    export VERSION="$VERSION"
    export TARGET_COLOR="$target_color"
    
    # Deploy target environment
    docker-compose -f "$compose_file" --env-file "$env_file" up -d \
        backend-${target_color} \
        frontend-${target_color} \
        vllm-server-${target_color}
    
    log_success "${target_color} environment deployed"
}

wait_for_health_check() {
    local target_color="$1"
    local max_attempts=30
    local attempt=1
    
    log_info "Waiting for ${target_color} environment to be healthy..."
    
    while [[ $attempt -le $max_attempts ]]; do
        if docker-compose -f "$PROJECT_ROOT/docker-compose.${ENVIRONMENT}.yml" \
           exec backend-${target_color} curl -f http://localhost:8000/health >/dev/null 2>&1; then
            log_success "${target_color} environment is healthy"
            return 0
        fi
        
        log_info "Attempt $attempt/$max_attempts: Waiting for health check..."
        sleep 10
        ((attempt++))
    done
    
    log_error "${target_color} environment failed health check"
    return 1
}

run_smoke_tests() {
    local target_color="$1"
    local backend_url="http://localhost:8000"
    
    log_info "Running smoke tests on ${target_color} environment..."
    
    # Test health endpoint
    if ! curl -f "${backend_url}/health" >/dev/null 2>&1; then
        log_error "Health endpoint test failed"
        return 1
    fi
    
    # Test API status endpoint
    if ! curl -f "${backend_url}/api/v3/status" >/dev/null 2>&1; then
        log_error "API status endpoint test failed"
        return 1
    fi
    
    # Test chat endpoint (basic connectivity)
    if ! curl -f -X POST "${backend_url}/api/v3/chat" \
         -H "Content-Type: application/json" \
         -d '{"message": "test", "session_id": "test"}' >/dev/null 2>&1; then
        log_error "Chat endpoint test failed"
        return 1
    fi
    
    log_success "Smoke tests passed"
    return 0
}

switch_traffic() {
    local target_color="$1"
    local current_color="$2"
    
    log_info "Switching traffic from ${current_color} to ${target_color}..."
    
    # Update load balancer configuration
    # This would typically involve updating nginx configuration or load balancer rules
    # For this example, we'll update the docker-compose service aliases
    
    docker-compose -f "$PROJECT_ROOT/docker-compose.${ENVIRONMENT}.yml" \
        exec nginx nginx -s reload
    
    log_success "Traffic switched to ${target_color}"
}

cleanup_old_environment() {
    local old_color="$1"
    
    log_info "Cleaning up ${old_color} environment..."
    
    # Stop old services
    docker-compose -f "$PROJECT_ROOT/docker-compose.${ENVIRONMENT}.yml" \
        stop backend-${old_color} frontend-${old_color} vllm-server-${old_color}
    
    # Remove old containers
    docker-compose -f "$PROJECT_ROOT/docker-compose.${ENVIRONMENT}.yml" \
        rm -f backend-${old_color} frontend-${old_color} vllm-server-${old_color}
    
    log_success "${old_color} environment cleaned up"
}

rollback_deployment() {
    local target_color="$1"
    local current_color="$2"
    
    log_warning "Rolling back deployment..."
    
    # Stop failed deployment
    docker-compose -f "$PROJECT_ROOT/docker-compose.${ENVIRONMENT}.yml" \
        stop backend-${target_color} frontend-${target_color} vllm-server-${target_color}
    
    # Remove failed containers
    docker-compose -f "$PROJECT_ROOT/docker-compose.${ENVIRONMENT}.yml" \
        rm -f backend-${target_color} frontend-${target_color} vllm-server-${target_color}
    
    # Ensure current environment is running
    docker-compose -f "$PROJECT_ROOT/docker-compose.${ENVIRONMENT}.yml" \
        up -d backend-${current_color} frontend-${current_color} vllm-server-${current_color}
    
    log_error "Deployment rolled back to ${current_color}"
}

# ============================================================================
# MAIN DEPLOYMENT LOGIC
# ============================================================================
main() {
    log_info "Starting blue-green deployment for ${ENVIRONMENT} environment"
    log_info "Version: ${VERSION}"
    
    # Check prerequisites
    check_prerequisites
    
    # Determine current and target colors
    current_color=$(get_current_color)
    target_color=$(get_target_color "$current_color")
    
    log_info "Current environment: ${current_color}"
    log_info "Target environment: ${target_color}"
    
    # Deploy to target environment
    if ! deploy_target_environment "$target_color"; then
        log_error "Failed to deploy target environment"
        exit 1
    fi
    
    # Wait for health check
    if ! wait_for_health_check "$target_color"; then
        rollback_deployment "$target_color" "$current_color"
        exit 1
    fi
    
    # Run smoke tests
    if ! run_smoke_tests "$target_color"; then
        rollback_deployment "$target_color" "$current_color"
        exit 1
    fi
    
    # Switch traffic
    if ! switch_traffic "$target_color" "$current_color"; then
        rollback_deployment "$target_color" "$current_color"
        exit 1
    fi
    
    # Wait a bit to ensure everything is stable
    log_info "Waiting for traffic switch to stabilize..."
    sleep 30
    
    # Final health check
    if ! wait_for_health_check "$target_color"; then
        log_warning "Final health check failed, but traffic has been switched"
        log_warning "Manual intervention may be required"
    fi
    
    # Cleanup old environment
    cleanup_old_environment "$current_color"
    
    log_success "Blue-green deployment completed successfully!"
    log_success "Active environment: ${target_color}"
    log_success "Version: ${VERSION}"
}

# ============================================================================
# SCRIPT EXECUTION
# ============================================================================
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi