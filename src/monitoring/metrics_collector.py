"""
xCodeAgent Advanced Metrics Collection System
Comprehensive monitoring and analytics for production deployment
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import psutil
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, generate_latest
from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

# ============================================================================
# METRICS DATA STRUCTURES
# ============================================================================

@dataclass
class SystemMetrics:
    """System-level performance metrics"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    disk_usage_percent: float
    network_io_bytes: Dict[str, int]
    process_count: int
    load_average: List[float]

@dataclass
class ApplicationMetrics:
    """Application-level performance metrics"""
    timestamp: datetime
    active_sessions: int
    total_requests: int
    error_rate: float
    response_time_avg: float
    response_time_p95: float
    response_time_p99: float
    cache_hit_rate: float
    database_connections: int

@dataclass
class AIModelMetrics:
    """AI model performance metrics"""
    timestamp: datetime
    model_name: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_response_time: float
    avg_tokens_per_second: float
    memory_usage_mb: float
    gpu_utilization: float

@dataclass
class BusinessMetrics:
    """Business-level metrics and KPIs"""
    timestamp: datetime
    daily_active_users: int
    code_generations: int
    chat_interactions: int
    file_operations: int
    deployment_count: int
    user_satisfaction_score: float

# ============================================================================
# PROMETHEUS METRICS SETUP
# ============================================================================

class PrometheusMetrics:
    """Prometheus metrics collector"""
    
    def __init__(self):
        self.registry = CollectorRegistry()
        
        # HTTP Metrics
        self.http_requests_total = Counter(
            'http_requests_total',
            'Total HTTP requests',
            ['method', 'endpoint', 'status_code'],
            registry=self.registry
        )
        
        self.http_request_duration = Histogram(
            'http_request_duration_seconds',
            'HTTP request duration',
            ['method', 'endpoint'],
            registry=self.registry
        )
        
        # System Metrics
        self.system_cpu_usage = Gauge(
            'system_cpu_usage_percent',
            'System CPU usage percentage',
            registry=self.registry
        )
        
        self.system_memory_usage = Gauge(
            'system_memory_usage_percent',
            'System memory usage percentage',
            registry=self.registry
        )
        
        self.system_disk_usage = Gauge(
            'system_disk_usage_percent',
            'System disk usage percentage',
            registry=self.registry
        )
        
        # Application Metrics
        self.active_sessions = Gauge(
            'active_sessions_total',
            'Number of active user sessions',
            registry=self.registry
        )
        
        self.database_connections = Gauge(
            'database_connections_active',
            'Number of active database connections',
            registry=self.registry
        )
        
        self.cache_hit_rate = Gauge(
            'cache_hit_rate_percent',
            'Cache hit rate percentage',
            registry=self.registry
        )
        
        # AI Model Metrics
        self.ai_requests_total = Counter(
            'ai_requests_total',
            'Total AI model requests',
            ['model', 'status'],
            registry=self.registry
        )
        
        self.ai_response_time = Histogram(
            'ai_response_time_seconds',
            'AI model response time',
            ['model'],
            registry=self.registry
        )
        
        self.ai_tokens_per_second = Gauge(
            'ai_tokens_per_second',
            'AI model tokens per second',
            ['model'],
            registry=self.registry
        )

# ============================================================================
# METRICS COLLECTION MIDDLEWARE
# ============================================================================

class MetricsMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for collecting HTTP metrics"""
    
    def __init__(self, app: FastAPI, metrics: PrometheusMetrics):
        super().__init__(app)
        self.metrics = metrics
        
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Extract metrics labels
        method = request.method
        endpoint = request.url.path
        status_code = str(response.status_code)
        
        # Update metrics
        self.metrics.http_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status_code=status_code
        ).inc()
        
        self.metrics.http_request_duration.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)
        
        return response

# ============================================================================
# COMPREHENSIVE METRICS COLLECTOR
# ============================================================================

class MetricsCollector:
    """Main metrics collection and aggregation system"""
    
    def __init__(self):
        self.prometheus_metrics = PrometheusMetrics()
        self.logger = logging.getLogger(__name__)
        
        # In-memory metrics storage
        self.system_metrics_history = deque(maxlen=1000)
        self.application_metrics_history = deque(maxlen=1000)
        self.ai_metrics_history = deque(maxlen=1000)
        self.business_metrics_history = deque(maxlen=1000)
        
        # Aggregated metrics
        self.hourly_aggregates = defaultdict(dict)
        self.daily_aggregates = defaultdict(dict)
        
        # Collection intervals
        self.system_collection_interval = 30  # seconds
        self.application_collection_interval = 60  # seconds
        self.ai_collection_interval = 30  # seconds
        self.business_collection_interval = 300  # seconds
        
        # Mock data for demonstration
        self.mock_active_sessions = 15
        self.mock_total_requests = 1250
        self.mock_error_count = 12
        
    async def initialize(self):
        """Initialize connections and start collection tasks"""
        try:
            # Start collection tasks
            asyncio.create_task(self.collect_system_metrics())
            asyncio.create_task(self.collect_application_metrics())
            asyncio.create_task(self.collect_ai_metrics())
            asyncio.create_task(self.collect_business_metrics())
            asyncio.create_task(self.aggregate_metrics())
            
            self.logger.info("Metrics collector initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize metrics collector: {e}")
            raise
    
    async def collect_system_metrics(self):
        """Collect system-level performance metrics"""
        while True:
            try:
                # Collect system metrics
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage('/')
                network = psutil.net_io_counters()
                load_avg = psutil.getloadavg() if hasattr(psutil, 'getloadavg') else [0.0, 0.0, 0.0]
                
                metrics = SystemMetrics(
                    timestamp=datetime.utcnow(),
                    cpu_percent=cpu_percent,
                    memory_percent=memory.percent,
                    disk_usage_percent=(disk.used / disk.total) * 100,
                    network_io_bytes={
                        'bytes_sent': network.bytes_sent,
                        'bytes_recv': network.bytes_recv
                    },
                    process_count=len(psutil.pids()),
                    load_average=list(load_avg)
                )
                
                # Store in memory
                self.system_metrics_history.append(metrics)
                
                # Update Prometheus metrics
                self.prometheus_metrics.system_cpu_usage.set(cpu_percent)
                self.prometheus_metrics.system_memory_usage.set(memory.percent)
                self.prometheus_metrics.system_disk_usage.set((disk.used / disk.total) * 100)
                
                self.logger.debug(f"System metrics collected: CPU {cpu_percent}%, Memory {memory.percent}%")
                
            except Exception as e:
                self.logger.error(f"Error collecting system metrics: {e}")
            
            await asyncio.sleep(self.system_collection_interval)
    
    async def collect_application_metrics(self):
        """Collect application-level performance metrics"""
        while True:
            try:
                # Mock application metrics for demonstration
                self.mock_active_sessions += (-2 + (time.time() % 5))  # Simulate fluctuation
                self.mock_total_requests += 5
                self.mock_error_count += (1 if time.time() % 10 < 1 else 0)
                
                active_sessions = max(1, int(self.mock_active_sessions))
                total_requests = int(self.mock_total_requests)
                error_rate = (self.mock_error_count / total_requests) * 100 if total_requests > 0 else 0
                
                # Simulate response times
                import random
                response_times = [random.uniform(0.1, 2.0) for _ in range(100)]
                response_times.sort()
                avg_response_time = sum(response_times) / len(response_times)
                response_time_p95 = response_times[95]
                response_time_p99 = response_times[99]
                
                metrics = ApplicationMetrics(
                    timestamp=datetime.utcnow(),
                    active_sessions=active_sessions,
                    total_requests=total_requests,
                    error_rate=error_rate,
                    response_time_avg=avg_response_time,
                    response_time_p95=response_time_p95,
                    response_time_p99=response_time_p99,
                    cache_hit_rate=85.5,  # Mock cache hit rate
                    database_connections=8  # Mock DB connections
                )
                
                # Store in memory
                self.application_metrics_history.append(metrics)
                
                # Update Prometheus metrics
                self.prometheus_metrics.active_sessions.set(active_sessions)
                self.prometheus_metrics.database_connections.set(8)
                self.prometheus_metrics.cache_hit_rate.set(85.5)
                
                self.logger.debug(f"Application metrics collected: {active_sessions} sessions, {error_rate:.2f}% error rate")
                
            except Exception as e:
                self.logger.error(f"Error collecting application metrics: {e}")
            
            await asyncio.sleep(self.application_collection_interval)
    
    async def collect_ai_metrics(self):
        """Collect AI model performance metrics"""
        while True:
            try:
                # Mock AI metrics for demonstration
                import random
                
                total_requests = random.randint(50, 200)
                successful_requests = int(total_requests * 0.98)
                failed_requests = total_requests - successful_requests
                avg_response_time = random.uniform(0.8, 1.2)
                avg_tokens_per_second = random.uniform(45, 65)
                memory_usage = random.uniform(2000, 4000)
                gpu_utilization = random.uniform(60, 85)
                
                metrics = AIModelMetrics(
                    timestamp=datetime.utcnow(),
                    model_name='deepseek-r1-0528',
                    total_requests=total_requests,
                    successful_requests=successful_requests,
                    failed_requests=failed_requests,
                    avg_response_time=avg_response_time,
                    avg_tokens_per_second=avg_tokens_per_second,
                    memory_usage_mb=memory_usage,
                    gpu_utilization=gpu_utilization
                )
                
                # Store in memory
                self.ai_metrics_history.append(metrics)
                
                # Update Prometheus metrics
                self.prometheus_metrics.ai_tokens_per_second.labels(model='deepseek-r1-0528').set(avg_tokens_per_second)
                
                self.logger.debug(f"AI metrics collected: {total_requests} requests, {avg_response_time:.2f}s avg response time")
                
            except Exception as e:
                self.logger.error(f"Error collecting AI metrics: {e}")
            
            await asyncio.sleep(self.ai_collection_interval)
    
    async def collect_business_metrics(self):
        """Collect business-level metrics and KPIs"""
        while True:
            try:
                # Mock business metrics for demonstration
                import random
                
                metrics = BusinessMetrics(
                    timestamp=datetime.utcnow(),
                    daily_active_users=random.randint(150, 300),
                    code_generations=random.randint(500, 1200),
                    chat_interactions=random.randint(800, 2000),
                    file_operations=random.randint(300, 800),
                    deployment_count=random.randint(20, 50),
                    user_satisfaction_score=random.uniform(4.2, 4.8)
                )
                
                # Store in memory
                self.business_metrics_history.append(metrics)
                
                self.logger.debug(f"Business metrics collected: {metrics.daily_active_users} DAU, {metrics.code_generations} code generations")
                
            except Exception as e:
                self.logger.error(f"Error collecting business metrics: {e}")
            
            await asyncio.sleep(self.business_collection_interval)
    
    async def aggregate_metrics(self):
        """Aggregate metrics for historical analysis"""
        while True:
            try:
                current_time = datetime.utcnow()
                hour_key = current_time.strftime('%Y-%m-%d-%H')
                day_key = current_time.strftime('%Y-%m-%d')
                
                # Aggregate hourly metrics
                if hour_key not in self.hourly_aggregates:
                    await self._create_hourly_aggregate(hour_key)
                
                # Aggregate daily metrics (at the start of each day)
                if current_time.hour == 0 and day_key not in self.daily_aggregates:
                    await self._create_daily_aggregate(day_key)
                
                # Clean up old aggregates (keep 30 days)
                cutoff_date = current_time - timedelta(days=30)
                cutoff_key = cutoff_date.strftime('%Y-%m-%d')
                
                # Remove old daily aggregates
                keys_to_remove = [k for k in self.daily_aggregates.keys() if k < cutoff_key]
                for key in keys_to_remove:
                    del self.daily_aggregates[key]
                
                self.logger.debug(f"Metrics aggregated for {hour_key}")
                
            except Exception as e:
                self.logger.error(f"Error aggregating metrics: {e}")
            
            await asyncio.sleep(3600)  # Run every hour
    
    async def _create_hourly_aggregate(self, hour_key: str):
        """Create hourly aggregate from recent metrics"""
        try:
            # Get metrics from the last hour
            cutoff_time = datetime.utcnow() - timedelta(hours=1)
            
            # System metrics aggregation
            recent_system = [m for m in self.system_metrics_history if m.timestamp >= cutoff_time]
            if recent_system:
                system_agg = {
                    'avg_cpu': sum(m.cpu_percent for m in recent_system) / len(recent_system),
                    'avg_memory': sum(m.memory_percent for m in recent_system) / len(recent_system),
                    'avg_disk': sum(m.disk_usage_percent for m in recent_system) / len(recent_system),
                    'max_cpu': max(m.cpu_percent for m in recent_system),
                    'max_memory': max(m.memory_percent for m in recent_system),
                }
            else:
                system_agg = {}
            
            # Application metrics aggregation
            recent_app = [m for m in self.application_metrics_history if m.timestamp >= cutoff_time]
            if recent_app:
                app_agg = {
                    'avg_sessions': sum(m.active_sessions for m in recent_app) / len(recent_app),
                    'avg_response_time': sum(m.response_time_avg for m in recent_app) / len(recent_app),
                    'avg_error_rate': sum(m.error_rate for m in recent_app) / len(recent_app),
                    'total_requests': sum(m.total_requests for m in recent_app),
                }
            else:
                app_agg = {}
            
            # Store aggregated data
            self.hourly_aggregates[hour_key] = {
                'system': system_agg,
                'application': app_agg,
                'timestamp': hour_key
            }
            
        except Exception as e:
            self.logger.error(f"Error creating hourly aggregate: {e}")
    
    async def _create_daily_aggregate(self, day_key: str):
        """Create daily aggregate from hourly data"""
        try:
            # Get all hourly aggregates for the day
            hourly_keys = [f"{day_key}-{h:02d}" for h in range(24)]
            daily_data = []
            
            for hour_key in hourly_keys:
                if hour_key in self.hourly_aggregates:
                    daily_data.append(self.hourly_aggregates[hour_key])
            
            if daily_data:
                # Aggregate daily metrics
                daily_agg = {
                    'system': {
                        'avg_cpu': sum(d['system'].get('avg_cpu', 0) for d in daily_data) / len(daily_data),
                        'max_cpu': max(d['system'].get('max_cpu', 0) for d in daily_data),
                        'avg_memory': sum(d['system'].get('avg_memory', 0) for d in daily_data) / len(daily_data),
                        'max_memory': max(d['system'].get('max_memory', 0) for d in daily_data),
                    },
                    'application': {
                        'avg_sessions': sum(d['application'].get('avg_sessions', 0) for d in daily_data) / len(daily_data),
                        'total_requests': sum(d['application'].get('total_requests', 0) for d in daily_data),
                        'avg_response_time': sum(d['application'].get('avg_response_time', 0) for d in daily_data) / len(daily_data),
                    },
                    'timestamp': day_key
                }
                
                self.daily_aggregates[day_key] = daily_agg
            
        except Exception as e:
            self.logger.error(f"Error creating daily aggregate: {e}")
    
    async def get_metrics_summary(self) -> Dict[str, Any]:
        """Get comprehensive metrics summary"""
        try:
            # Get latest metrics
            latest_system = self.system_metrics_history[-1] if self.system_metrics_history else None
            latest_app = self.application_metrics_history[-1] if self.application_metrics_history else None
            latest_ai = self.ai_metrics_history[-1] if self.ai_metrics_history else None
            latest_business = self.business_metrics_history[-1] if self.business_metrics_history else None
            
            summary = {
                'timestamp': datetime.utcnow().isoformat(),
                'system': asdict(latest_system) if latest_system else {},
                'application': asdict(latest_app) if latest_app else {},
                'ai_model': asdict(latest_ai) if latest_ai else {},
                'business': asdict(latest_business) if latest_business else {},
                'health_status': self._calculate_health_status(),
                'alerts': await self._get_active_alerts()
            }
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error getting metrics summary: {e}")
            return {'error': str(e)}
    
    def _calculate_health_status(self) -> str:
        """Calculate overall system health status"""
        try:
            if not self.system_metrics_history or not self.application_metrics_history:
                return 'unknown'
            
            latest_system = self.system_metrics_history[-1]
            latest_app = self.application_metrics_history[-1]
            
            # Health criteria
            cpu_healthy = latest_system.cpu_percent < 80
            memory_healthy = latest_system.memory_percent < 85
            error_rate_healthy = latest_app.error_rate < 5
            response_time_healthy = latest_app.response_time_avg < 2.0
            
            if all([cpu_healthy, memory_healthy, error_rate_healthy, response_time_healthy]):
                return 'healthy'
            elif latest_system.cpu_percent > 95 or latest_system.memory_percent > 95 or latest_app.error_rate > 20:
                return 'critical'
            else:
                return 'warning'
                
        except Exception:
            return 'unknown'
    
    async def _get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get list of active alerts"""
        try:
            alerts = []
            
            if self.system_metrics_history:
                latest_system = self.system_metrics_history[-1]
                
                if latest_system.cpu_percent > 90:
                    alerts.append({
                        'type': 'system',
                        'severity': 'critical',
                        'message': f'High CPU usage: {latest_system.cpu_percent:.1f}%',
                        'timestamp': latest_system.timestamp.isoformat()
                    })
                
                if latest_system.memory_percent > 90:
                    alerts.append({
                        'type': 'system',
                        'severity': 'critical',
                        'message': f'High memory usage: {latest_system.memory_percent:.1f}%',
                        'timestamp': latest_system.timestamp.isoformat()
                    })
            
            if self.application_metrics_history:
                latest_app = self.application_metrics_history[-1]
                
                if latest_app.error_rate > 10:
                    alerts.append({
                        'type': 'application',
                        'severity': 'warning',
                        'message': f'High error rate: {latest_app.error_rate:.1f}%',
                        'timestamp': latest_app.timestamp.isoformat()
                    })
                
                if latest_app.response_time_avg > 5:
                    alerts.append({
                        'type': 'application',
                        'severity': 'warning',
                        'message': f'Slow response time: {latest_app.response_time_avg:.2f}s',
                        'timestamp': latest_app.timestamp.isoformat()
                    })
            
            return alerts
            
        except Exception as e:
            self.logger.error(f"Error getting active alerts: {e}")
            return []
    
    def get_prometheus_metrics(self) -> str:
        """Get Prometheus-formatted metrics"""
        return generate_latest(self.prometheus_metrics.registry)

# ============================================================================
# METRICS API ENDPOINTS
# ============================================================================

def create_metrics_router(metrics_collector: MetricsCollector):
    """Create FastAPI router for metrics endpoints"""
    from fastapi import APIRouter
    
    router = APIRouter(prefix="/metrics", tags=["metrics"])
    
    @router.get("/")
    async def get_prometheus_metrics():
        """Prometheus metrics endpoint"""
        return Response(
            content=metrics_collector.get_prometheus_metrics(),
            media_type="text/plain"
        )
    
    @router.get("/summary")
    async def get_metrics_summary():
        """Get comprehensive metrics summary"""
        return await metrics_collector.get_metrics_summary()
    
    @router.get("/health")
    async def get_health_status():
        """Get system health status"""
        summary = await metrics_collector.get_metrics_summary()
        return {
            'status': summary.get('health_status', 'unknown'),
            'timestamp': summary.get('timestamp'),
            'alerts': summary.get('alerts', [])
        }
    
    return router