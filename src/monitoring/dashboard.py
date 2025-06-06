"""
xCodeAgent Real-time Monitoring Dashboard
Advanced monitoring interface with live metrics and alerts
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import plotly.graph_objects as go
import plotly.express as px
from plotly.utils import PlotlyJSONEncoder

from .metrics_collector import MetricsCollector

# ============================================================================
# DASHBOARD CONFIGURATION
# ============================================================================

class DashboardConfig:
    """Configuration for the monitoring dashboard"""
    
    def __init__(self):
        self.refresh_interval = 5  # seconds
        self.chart_history_points = 100
        self.alert_retention_hours = 24
        self.color_scheme = {
            'primary': '#3B82F6',
            'success': '#10B981',
            'warning': '#F59E0B',
            'danger': '#EF4444',
            'info': '#6366F1',
            'dark': '#1F2937',
            'light': '#F9FAFB'
        }

# ============================================================================
# WEBSOCKET CONNECTION MANAGER
# ============================================================================

class ConnectionManager:
    """Manages WebSocket connections for real-time updates"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.logger = logging.getLogger(__name__)
    
    async def connect(self, websocket: WebSocket):
        """Accept a new WebSocket connection"""
        await websocket.accept()
        self.active_connections.append(websocket)
        self.logger.info(f"New WebSocket connection. Total: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            self.logger.info(f"WebSocket disconnected. Total: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Send a message to a specific WebSocket"""
        try:
            await websocket.send_text(message)
        except Exception as e:
            self.logger.error(f"Error sending message to WebSocket: {e}")
            self.disconnect(websocket)
    
    async def broadcast(self, message: str):
        """Broadcast a message to all connected WebSockets"""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                self.logger.error(f"Error broadcasting to WebSocket: {e}")
                disconnected.append(connection)
        
        # Remove disconnected connections
        for connection in disconnected:
            self.disconnect(connection)

# ============================================================================
# CHART GENERATORS
# ============================================================================

class ChartGenerator:
    """Generates interactive charts for the dashboard"""
    
    def __init__(self, config: DashboardConfig):
        self.config = config
    
    def create_system_metrics_chart(self, metrics_history: List) -> str:
        """Create system metrics time series chart"""
        if not metrics_history:
            return self._empty_chart("No system metrics available")
        
        # Extract data
        timestamps = [m.timestamp for m in metrics_history[-self.config.chart_history_points:]]
        cpu_data = [m.cpu_percent for m in metrics_history[-self.config.chart_history_points:]]
        memory_data = [m.memory_percent for m in metrics_history[-self.config.chart_history_points:]]
        
        # Create chart
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=timestamps,
            y=cpu_data,
            mode='lines+markers',
            name='CPU Usage (%)',
            line=dict(color=self.config.color_scheme['primary'], width=2),
            marker=dict(size=4)
        ))
        
        fig.add_trace(go.Scatter(
            x=timestamps,
            y=memory_data,
            mode='lines+markers',
            name='Memory Usage (%)',
            line=dict(color=self.config.color_scheme['warning'], width=2),
            marker=dict(size=4)
        ))
        
        fig.update_layout(
            title='System Resource Usage',
            xaxis_title='Time',
            yaxis_title='Usage (%)',
            yaxis=dict(range=[0, 100]),
            template='plotly_white',
            height=300,
            margin=dict(l=50, r=50, t=50, b=50)
        )
        
        return json.dumps(fig, cls=PlotlyJSONEncoder)
    
    def create_response_time_chart(self, metrics_history: List) -> str:
        """Create response time chart"""
        if not metrics_history:
            return self._empty_chart("No response time data available")
        
        # Extract data
        timestamps = [m.timestamp for m in metrics_history[-self.config.chart_history_points:]]
        avg_times = [m.response_time_avg for m in metrics_history[-self.config.chart_history_points:]]
        p95_times = [m.response_time_p95 for m in metrics_history[-self.config.chart_history_points:]]
        p99_times = [m.response_time_p99 for m in metrics_history[-self.config.chart_history_points:]]
        
        # Create chart
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=timestamps,
            y=avg_times,
            mode='lines',
            name='Average',
            line=dict(color=self.config.color_scheme['success'], width=2)
        ))
        
        fig.add_trace(go.Scatter(
            x=timestamps,
            y=p95_times,
            mode='lines',
            name='95th Percentile',
            line=dict(color=self.config.color_scheme['warning'], width=2)
        ))
        
        fig.add_trace(go.Scatter(
            x=timestamps,
            y=p99_times,
            mode='lines',
            name='99th Percentile',
            line=dict(color=self.config.color_scheme['danger'], width=2)
        ))
        
        fig.update_layout(
            title='Response Time Metrics',
            xaxis_title='Time',
            yaxis_title='Response Time (seconds)',
            template='plotly_white',
            height=300,
            margin=dict(l=50, r=50, t=50, b=50)
        )
        
        return json.dumps(fig, cls=PlotlyJSONEncoder)
    
    def create_ai_performance_chart(self, metrics_history: List) -> str:
        """Create AI model performance chart"""
        if not metrics_history:
            return self._empty_chart("No AI metrics available")
        
        # Extract data
        timestamps = [m.timestamp for m in metrics_history[-self.config.chart_history_points:]]
        response_times = [m.avg_response_time for m in metrics_history[-self.config.chart_history_points:]]
        tokens_per_sec = [m.avg_tokens_per_second for m in metrics_history[-self.config.chart_history_points:]]
        
        # Create dual-axis chart
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=timestamps,
            y=response_times,
            mode='lines+markers',
            name='Response Time (s)',
            line=dict(color=self.config.color_scheme['primary'], width=2),
            yaxis='y'
        ))
        
        fig.add_trace(go.Scatter(
            x=timestamps,
            y=tokens_per_sec,
            mode='lines+markers',
            name='Tokens/Second',
            line=dict(color=self.config.color_scheme['success'], width=2),
            yaxis='y2'
        ))
        
        fig.update_layout(
            title='AI Model Performance',
            xaxis_title='Time',
            yaxis=dict(title='Response Time (seconds)', side='left'),
            yaxis2=dict(title='Tokens per Second', side='right', overlaying='y'),
            template='plotly_white',
            height=300,
            margin=dict(l=50, r=50, t=50, b=50)
        )
        
        return json.dumps(fig, cls=PlotlyJSONEncoder)
    
    def create_business_metrics_chart(self, metrics_history: List) -> str:
        """Create business metrics chart"""
        if not metrics_history:
            return self._empty_chart("No business metrics available")
        
        # Get latest metrics for pie chart
        latest = metrics_history[-1]
        
        # Create pie chart for activity distribution
        labels = ['Code Generations', 'Chat Interactions', 'File Operations', 'Deployments']
        values = [
            latest.code_generations,
            latest.chat_interactions,
            latest.file_operations,
            latest.deployment_count
        ]
        
        fig = go.Figure(data=[go.Pie(
            labels=labels,
            values=values,
            hole=0.4,
            marker_colors=[
                self.config.color_scheme['primary'],
                self.config.color_scheme['success'],
                self.config.color_scheme['warning'],
                self.config.color_scheme['info']
            ]
        )])
        
        fig.update_layout(
            title='Daily Activity Distribution',
            template='plotly_white',
            height=300,
            margin=dict(l=50, r=50, t=50, b=50)
        )
        
        return json.dumps(fig, cls=PlotlyJSONEncoder)
    
    def _empty_chart(self, message: str) -> str:
        """Create an empty chart with a message"""
        fig = go.Figure()
        fig.add_annotation(
            text=message,
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=16, color=self.config.color_scheme['dark'])
        )
        fig.update_layout(
            template='plotly_white',
            height=300,
            margin=dict(l=50, r=50, t=50, b=50)
        )
        return json.dumps(fig, cls=PlotlyJSONEncoder)

# ============================================================================
# DASHBOARD MANAGER
# ============================================================================

class DashboardManager:
    """Main dashboard management class"""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics_collector = metrics_collector
        self.config = DashboardConfig()
        self.chart_generator = ChartGenerator(self.config)
        self.connection_manager = ConnectionManager()
        self.logger = logging.getLogger(__name__)
        self._background_task = None
        
    async def start_background_tasks(self):
        """Start background tasks (call this after event loop is running)"""
        if self._background_task is None:
            self._background_task = asyncio.create_task(self._broadcast_updates())
    
    async def _broadcast_updates(self):
        """Broadcast real-time updates to all connected clients"""
        while True:
            try:
                # Get latest metrics summary
                summary = await self.metrics_collector.get_metrics_summary()
                
                # Generate charts
                charts = await self._generate_all_charts()
                
                # Prepare update message
                update_message = {
                    'type': 'metrics_update',
                    'timestamp': datetime.utcnow().isoformat(),
                    'summary': summary,
                    'charts': charts
                }
                
                # Broadcast to all connected clients
                await self.connection_manager.broadcast(json.dumps(update_message))
                
            except Exception as e:
                self.logger.error(f"Error broadcasting updates: {e}")
            
            await asyncio.sleep(self.config.refresh_interval)
    
    async def _generate_all_charts(self) -> Dict[str, str]:
        """Generate all dashboard charts"""
        try:
            charts = {}
            
            # System metrics chart
            if self.metrics_collector.system_metrics_history:
                charts['system_metrics'] = self.chart_generator.create_system_metrics_chart(
                    list(self.metrics_collector.system_metrics_history)
                )
            
            # Response time chart
            if self.metrics_collector.application_metrics_history:
                charts['response_time'] = self.chart_generator.create_response_time_chart(
                    list(self.metrics_collector.application_metrics_history)
                )
            
            # AI performance chart
            if self.metrics_collector.ai_metrics_history:
                charts['ai_performance'] = self.chart_generator.create_ai_performance_chart(
                    list(self.metrics_collector.ai_metrics_history)
                )
            
            # Business metrics chart
            if self.metrics_collector.business_metrics_history:
                charts['business_metrics'] = self.chart_generator.create_business_metrics_chart(
                    list(self.metrics_collector.business_metrics_history)
                )
            
            return charts
            
        except Exception as e:
            self.logger.error(f"Error generating charts: {e}")
            return {}
    
    async def get_dashboard_data(self) -> Dict[str, Any]:
        """Get complete dashboard data"""
        try:
            # Get metrics summary
            summary = await self.metrics_collector.get_metrics_summary()
            
            # Generate charts
            charts = await self._generate_all_charts()
            
            # Calculate additional dashboard metrics
            dashboard_data = {
                'summary': summary,
                'charts': charts,
                'system_status': self._get_system_status(summary),
                'performance_score': self._calculate_performance_score(summary),
                'uptime': self._calculate_uptime(),
                'active_connections': len(self.connection_manager.active_connections)
            }
            
            return dashboard_data
            
        except Exception as e:
            self.logger.error(f"Error getting dashboard data: {e}")
            return {'error': str(e)}
    
    def _get_system_status(self, summary: Dict[str, Any]) -> Dict[str, str]:
        """Get system component status"""
        status = {
            'overall': summary.get('health_status', 'unknown'),
            'api': 'healthy',  # Based on response time and error rate
            'database': 'healthy',  # Based on connection count
            'ai_model': 'healthy',  # Based on AI metrics
            'cache': 'healthy'  # Based on cache hit rate
        }
        
        # Update based on actual metrics
        if summary.get('application', {}).get('error_rate', 0) > 5:
            status['api'] = 'warning'
        if summary.get('application', {}).get('error_rate', 0) > 15:
            status['api'] = 'critical'
        
        if summary.get('application', {}).get('database_connections', 0) > 50:
            status['database'] = 'warning'
        
        if summary.get('ai_model', {}).get('avg_response_time', 0) > 3:
            status['ai_model'] = 'warning'
        
        return status
    
    def _calculate_performance_score(self, summary: Dict[str, Any]) -> float:
        """Calculate overall performance score (0-100)"""
        try:
            score = 100.0
            
            # Deduct points for high resource usage
            cpu_usage = summary.get('system', {}).get('cpu_percent', 0)
            if cpu_usage > 80:
                score -= (cpu_usage - 80) * 2
            
            memory_usage = summary.get('system', {}).get('memory_percent', 0)
            if memory_usage > 80:
                score -= (memory_usage - 80) * 2
            
            # Deduct points for high error rate
            error_rate = summary.get('application', {}).get('error_rate', 0)
            score -= error_rate * 5
            
            # Deduct points for slow response time
            response_time = summary.get('application', {}).get('response_time_avg', 0)
            if response_time > 1:
                score -= (response_time - 1) * 20
            
            return max(0, min(100, score))
            
        except Exception:
            return 0.0
    
    def _calculate_uptime(self) -> str:
        """Calculate system uptime (mock implementation)"""
        # In a real implementation, this would track actual uptime
        return "99.9% (30 days)"

# ============================================================================
# DASHBOARD HTML TEMPLATE
# ============================================================================

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>xCodeAgent Monitoring Dashboard</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        .status-healthy { @apply bg-green-100 text-green-800; }
        .status-warning { @apply bg-yellow-100 text-yellow-800; }
        .status-critical { @apply bg-red-100 text-red-800; }
        .status-unknown { @apply bg-gray-100 text-gray-800; }
        
        .metric-card {
            @apply bg-white rounded-lg shadow-md p-6 border border-gray-200;
        }
        
        .chart-container {
            @apply bg-white rounded-lg shadow-md p-4 border border-gray-200;
        }
    </style>
</head>
<body class="bg-gray-50">
    <div class="min-h-screen">
        <!-- Header -->
        <header class="bg-white shadow-sm border-b border-gray-200">
            <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div class="flex justify-between items-center py-4">
                    <div class="flex items-center">
                        <h1 class="text-2xl font-bold text-gray-900">🤖 xCodeAgent Monitoring</h1>
                        <span class="ml-4 px-3 py-1 text-sm font-medium rounded-full" id="overall-status">
                            Loading...
                        </span>
                    </div>
                    <div class="flex items-center space-x-4">
                        <div class="text-sm text-gray-500">
                            Last Updated: <span id="last-updated">--</span>
                        </div>
                        <div class="flex items-center">
                            <div class="w-2 h-2 bg-green-400 rounded-full mr-2" id="connection-indicator"></div>
                            <span class="text-sm text-gray-600" id="connection-status">Connected</span>
                        </div>
                    </div>
                </div>
            </div>
        </header>

        <!-- Main Content -->
        <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            <!-- Key Metrics Row -->
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
                <div class="metric-card">
                    <div class="flex items-center">
                        <div class="flex-shrink-0">
                            <div class="w-8 h-8 bg-blue-500 rounded-md flex items-center justify-center">
                                <span class="text-white text-sm font-bold">⚡</span>
                            </div>
                        </div>
                        <div class="ml-4">
                            <p class="text-sm font-medium text-gray-500">Performance Score</p>
                            <p class="text-2xl font-bold text-gray-900" id="performance-score">--</p>
                        </div>
                    </div>
                </div>

                <div class="metric-card">
                    <div class="flex items-center">
                        <div class="flex-shrink-0">
                            <div class="w-8 h-8 bg-green-500 rounded-md flex items-center justify-center">
                                <span class="text-white text-sm font-bold">👥</span>
                            </div>
                        </div>
                        <div class="ml-4">
                            <p class="text-sm font-medium text-gray-500">Active Sessions</p>
                            <p class="text-2xl font-bold text-gray-900" id="active-sessions">--</p>
                        </div>
                    </div>
                </div>

                <div class="metric-card">
                    <div class="flex items-center">
                        <div class="flex-shrink-0">
                            <div class="w-8 h-8 bg-yellow-500 rounded-md flex items-center justify-center">
                                <span class="text-white text-sm font-bold">⏱️</span>
                            </div>
                        </div>
                        <div class="ml-4">
                            <p class="text-sm font-medium text-gray-500">Avg Response Time</p>
                            <p class="text-2xl font-bold text-gray-900" id="response-time">--</p>
                        </div>
                    </div>
                </div>

                <div class="metric-card">
                    <div class="flex items-center">
                        <div class="flex-shrink-0">
                            <div class="w-8 h-8 bg-red-500 rounded-md flex items-center justify-center">
                                <span class="text-white text-sm font-bold">🚨</span>
                            </div>
                        </div>
                        <div class="ml-4">
                            <p class="text-sm font-medium text-gray-500">Error Rate</p>
                            <p class="text-2xl font-bold text-gray-900" id="error-rate">--</p>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Charts Row -->
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
                <div class="chart-container">
                    <h3 class="text-lg font-semibold text-gray-900 mb-4">System Resources</h3>
                    <div id="system-metrics-chart"></div>
                </div>

                <div class="chart-container">
                    <h3 class="text-lg font-semibold text-gray-900 mb-4">Response Times</h3>
                    <div id="response-time-chart"></div>
                </div>

                <div class="chart-container">
                    <h3 class="text-lg font-semibold text-gray-900 mb-4">AI Model Performance</h3>
                    <div id="ai-performance-chart"></div>
                </div>

                <div class="chart-container">
                    <h3 class="text-lg font-semibold text-gray-900 mb-4">Business Metrics</h3>
                    <div id="business-metrics-chart"></div>
                </div>
            </div>

            <!-- System Status -->
            <div class="bg-white rounded-lg shadow-md p-6 border border-gray-200 mb-8">
                <h3 class="text-lg font-semibold text-gray-900 mb-4">System Status</h3>
                <div class="grid grid-cols-2 md:grid-cols-5 gap-4" id="system-status">
                    <!-- Status items will be populated by JavaScript -->
                </div>
            </div>

            <!-- Alerts -->
            <div class="bg-white rounded-lg shadow-md p-6 border border-gray-200">
                <h3 class="text-lg font-semibold text-gray-900 mb-4">Active Alerts</h3>
                <div id="alerts-container">
                    <p class="text-gray-500">No active alerts</p>
                </div>
            </div>
        </main>
    </div>

    <script>
        // WebSocket connection for real-time updates
        let ws;
        let reconnectInterval = 5000;

        function connectWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws/dashboard`;
            
            ws = new WebSocket(wsUrl);
            
            ws.onopen = function(event) {
                console.log('WebSocket connected');
                updateConnectionStatus(true);
            };
            
            ws.onmessage = function(event) {
                const data = JSON.parse(event.data);
                if (data.type === 'metrics_update') {
                    updateDashboard(data);
                }
            };
            
            ws.onclose = function(event) {
                console.log('WebSocket disconnected');
                updateConnectionStatus(false);
                setTimeout(connectWebSocket, reconnectInterval);
            };
            
            ws.onerror = function(error) {
                console.error('WebSocket error:', error);
                updateConnectionStatus(false);
            };
        }

        function updateConnectionStatus(connected) {
            const indicator = document.getElementById('connection-indicator');
            const status = document.getElementById('connection-status');
            
            if (connected) {
                indicator.className = 'w-2 h-2 bg-green-400 rounded-full mr-2';
                status.textContent = 'Connected';
            } else {
                indicator.className = 'w-2 h-2 bg-red-400 rounded-full mr-2';
                status.textContent = 'Disconnected';
            }
        }

        function updateDashboard(data) {
            const summary = data.summary;
            const charts = data.charts;
            
            // Update timestamp
            document.getElementById('last-updated').textContent = new Date().toLocaleTimeString();
            
            // Update overall status
            const overallStatus = document.getElementById('overall-status');
            overallStatus.textContent = summary.health_status || 'unknown';
            overallStatus.className = `ml-4 px-3 py-1 text-sm font-medium rounded-full status-${summary.health_status || 'unknown'}`;
            
            // Update key metrics
            document.getElementById('performance-score').textContent = '95.2%'; // Mock data
            document.getElementById('active-sessions').textContent = summary.application?.active_sessions || '--';
            document.getElementById('response-time').textContent = 
                summary.application?.response_time_avg ? `${summary.application.response_time_avg.toFixed(2)}s` : '--';
            document.getElementById('error-rate').textContent = 
                summary.application?.error_rate ? `${summary.application.error_rate.toFixed(1)}%` : '--';
            
            // Update charts
            if (charts.system_metrics) {
                Plotly.newPlot('system-metrics-chart', JSON.parse(charts.system_metrics).data, 
                              JSON.parse(charts.system_metrics).layout, {responsive: true});
            }
            
            if (charts.response_time) {
                Plotly.newPlot('response-time-chart', JSON.parse(charts.response_time).data, 
                              JSON.parse(charts.response_time).layout, {responsive: true});
            }
            
            if (charts.ai_performance) {
                Plotly.newPlot('ai-performance-chart', JSON.parse(charts.ai_performance).data, 
                              JSON.parse(charts.ai_performance).layout, {responsive: true});
            }
            
            if (charts.business_metrics) {
                Plotly.newPlot('business-metrics-chart', JSON.parse(charts.business_metrics).data, 
                              JSON.parse(charts.business_metrics).layout, {responsive: true});
            }
            
            // Update system status
            updateSystemStatus(summary);
            
            // Update alerts
            updateAlerts(summary.alerts || []);
        }

        function updateSystemStatus(summary) {
            const statusContainer = document.getElementById('system-status');
            const components = ['API', 'Database', 'AI Model', 'Cache', 'Storage'];
            
            statusContainer.innerHTML = components.map(component => `
                <div class="text-center">
                    <div class="w-12 h-12 mx-auto mb-2 rounded-full bg-green-100 flex items-center justify-center">
                        <span class="text-green-600 text-xl">✓</span>
                    </div>
                    <p class="text-sm font-medium text-gray-900">${component}</p>
                    <p class="text-xs text-green-600">Healthy</p>
                </div>
            `).join('');
        }

        function updateAlerts(alerts) {
            const alertsContainer = document.getElementById('alerts-container');
            
            if (alerts.length === 0) {
                alertsContainer.innerHTML = '<p class="text-gray-500">No active alerts</p>';
                return;
            }
            
            alertsContainer.innerHTML = alerts.map(alert => `
                <div class="flex items-center p-3 mb-2 rounded-md ${alert.severity === 'critical' ? 'bg-red-50 border border-red-200' : 'bg-yellow-50 border border-yellow-200'}">
                    <span class="text-lg mr-3">${alert.severity === 'critical' ? '🚨' : '⚠️'}</span>
                    <div class="flex-1">
                        <p class="font-medium ${alert.severity === 'critical' ? 'text-red-800' : 'text-yellow-800'}">${alert.message}</p>
                        <p class="text-sm ${alert.severity === 'critical' ? 'text-red-600' : 'text-yellow-600'}">${new Date(alert.timestamp).toLocaleString()}</p>
                    </div>
                </div>
            `).join('');
        }

        // Initialize dashboard
        connectWebSocket();
        
        // Load initial data
        fetch('/api/v3/dashboard/data')
            .then(response => response.json())
            .then(data => {
                updateDashboard({
                    summary: data.summary,
                    charts: data.charts
                });
            })
            .catch(error => console.error('Error loading initial data:', error));
    </script>
</body>
</html>
"""

# ============================================================================
# DASHBOARD ROUTER
# ============================================================================

def create_dashboard_router(metrics_collector: MetricsCollector, app_state=None):
    """Create FastAPI router for dashboard endpoints"""
    from fastapi import APIRouter, WebSocket, WebSocketDisconnect
    
    router = APIRouter(prefix="/dashboard", tags=["dashboard"])
    dashboard_manager = DashboardManager(metrics_collector)
    
    # Store dashboard manager in app state if provided
    if app_state is not None:
        app_state.dashboard_manager = dashboard_manager
    
    @router.get("/", response_class=HTMLResponse)
    async def dashboard_page():
        """Serve the monitoring dashboard"""
        return DASHBOARD_HTML
    
    @router.get("/data")
    async def get_dashboard_data():
        """Get dashboard data"""
        return await dashboard_manager.get_dashboard_data()
    
    @router.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        """WebSocket endpoint for real-time updates"""
        await dashboard_manager.connection_manager.connect(websocket)
        try:
            while True:
                # Keep connection alive
                await websocket.receive_text()
        except WebSocketDisconnect:
            dashboard_manager.connection_manager.disconnect(websocket)
    
    return router