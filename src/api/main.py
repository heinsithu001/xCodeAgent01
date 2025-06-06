"""
FastAPI Backend for Enhanced CodeAgent Integration
Provides REST API and WebSocket endpoints for the integrated system.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
import yaml

# Import our components
import sys
sys.path.append(str(Path(__file__).parent.parent))

from agents.enhanced_code_agent import EnhancedCodeAgent, Task, TaskType, TaskResult
from models.deepseek_provider import LocalDeepSeekProvider, GenerationConfig

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pydantic models for API
class TaskRequest(BaseModel):
    type: str
    description: str
    context: Optional[Dict[str, Any]] = None
    priority: int = 1
    language: Optional[str] = None
    files: Optional[List[str]] = None
    requirements: Optional[List[str]] = None

class TaskResponse(BaseModel):
    task_id: str
    status: str
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_time: Optional[float] = None
    created_at: str

class GenerationRequest(BaseModel):
    prompt: str
    temperature: float = 0.6
    max_tokens: int = 2048
    stream: bool = False

class HealthResponse(BaseModel):
    status: str
    deepseek_available: bool
    codeagent_available: bool
    openhands_available: bool
    model_info: Optional[Dict[str, Any]] = None

class SystemInfoResponse(BaseModel):
    deployment_type: str
    performance_tier: str
    model_name: str
    active_tasks: int
    total_tasks_completed: int

# Global state
app = FastAPI(
    title="Enhanced CodeAgent Integration API",
    description="API for the integrated CodeAgent03 + DeepSeek R1 + vLLM system",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables
enhanced_agent: Optional[EnhancedCodeAgent] = None
deepseek_provider: Optional[LocalDeepSeekProvider] = None
websocket_connections: List[WebSocket] = []
config: Dict[str, Any] = {}

async def load_config():
    """Load configuration from files"""
    global config
    
    config_path = Path(__file__).parent.parent.parent / "config"
    
    # Load environment variables
    env_file = config_path / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    config[key] = value
    
    # Load integration config
    integration_config_path = config_path / "integration_config.yaml"
    if integration_config_path.exists():
        with open(integration_config_path) as f:
            integration_config = yaml.safe_load(f)
            config.update(integration_config)

async def initialize_components():
    """Initialize all components"""
    global enhanced_agent, deepseek_provider
    
    try:
        # Load configuration
        await load_config()
        
        # Initialize DeepSeek provider
        deepseek_url = config.get("VLLM_HOST", "localhost")
        deepseek_port = config.get("VLLM_PORT", "8000")
        model_name = config.get("DEEPSEEK_MODEL", "deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B")
        
        base_url = f"http://{deepseek_url}:{deepseek_port}"
        
        deepseek_provider = LocalDeepSeekProvider(
            base_url=base_url,
            model_name=model_name
        )
        await deepseek_provider.__aenter__()
        
        # Initialize Enhanced Agent
        enhanced_agent = EnhancedCodeAgent(
            deepseek_url=base_url,
            model_name=model_name,
            workspace_path="./workspace"
        )
        await enhanced_agent.start()
        
        logger.info("All components initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize components: {e}")
        raise

@app.on_event("startup")
async def startup_event():
    """Application startup"""
    logger.info("Starting Enhanced CodeAgent Integration API...")
    await initialize_components()

@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown"""
    logger.info("Shutting down Enhanced CodeAgent Integration API...")
    
    if enhanced_agent:
        await enhanced_agent.stop()
    
    if deepseek_provider:
        await deepseek_provider.__aexit__(None, None, None)

# Health check endpoint
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Check system health"""
    deepseek_available = False
    model_info = None
    
    if deepseek_provider:
        deepseek_available = await deepseek_provider.health_check()
        if deepseek_available:
            model_info = await deepseek_provider.get_model_info()
    
    return HealthResponse(
        status="healthy" if deepseek_available else "degraded",
        deepseek_available=deepseek_available,
        codeagent_available=enhanced_agent is not None,
        openhands_available=True,  # Placeholder
        model_info=model_info
    )

# System info endpoint
@app.get("/system/info", response_model=SystemInfoResponse)
async def get_system_info():
    """Get system information"""
    if not enhanced_agent:
        raise HTTPException(status_code=503, detail="Enhanced agent not available")
    
    active_tasks = len(enhanced_agent.get_active_tasks())
    total_tasks = len(enhanced_agent.get_task_history())
    
    return SystemInfoResponse(
        deployment_type=config.get("DEPLOYMENT_TYPE", "unknown"),
        performance_tier=config.get("PERFORMANCE_TIER", "unknown"),
        model_name=config.get("DEEPSEEK_MODEL", "unknown"),
        active_tasks=active_tasks,
        total_tasks_completed=total_tasks
    )

# Task execution endpoints
@app.post("/tasks/execute", response_model=TaskResponse)
async def execute_task(task_request: TaskRequest, background_tasks: BackgroundTasks):
    """Execute a single task"""
    if not enhanced_agent:
        raise HTTPException(status_code=503, detail="Enhanced agent not available")
    
    # Create task
    task_id = str(uuid.uuid4())
    
    try:
        task_type = TaskType(task_request.type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid task type: {task_request.type}")
    
    task = Task(
        id=task_id,
        type=task_type,
        description=task_request.description,
        context=task_request.context,
        priority=task_request.priority,
        language=task_request.language,
        files=task_request.files,
        requirements=task_request.requirements
    )
    
    # Execute task in background
    background_tasks.add_task(execute_task_background, task)
    
    return TaskResponse(
        task_id=task_id,
        status="queued",
        created_at=datetime.now().isoformat()
    )

async def execute_task_background(task: Task):
    """Execute task in background and notify via WebSocket"""
    if not enhanced_agent:
        return
    
    try:
        result = await enhanced_agent.execute_task(task)
        
        # Notify WebSocket clients
        message = {
            "type": "task_completed",
            "task_id": task.id,
            "success": result.success,
            "result": result.result,
            "error": result.error,
            "execution_time": result.execution_time
        }
        
        await broadcast_to_websockets(message)
        
    except Exception as e:
        logger.error(f"Error executing task {task.id}: {e}")
        
        message = {
            "type": "task_error",
            "task_id": task.id,
            "error": str(e)
        }
        
        await broadcast_to_websockets(message)

@app.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task_status(task_id: str):
    """Get task status and result"""
    if not enhanced_agent:
        raise HTTPException(status_code=503, detail="Enhanced agent not available")
    
    # Check active tasks
    active_tasks = enhanced_agent.get_active_tasks()
    if task_id in active_tasks:
        return TaskResponse(
            task_id=task_id,
            status="running",
            created_at=datetime.now().isoformat()
        )
    
    # Check completed tasks
    task_history = enhanced_agent.get_task_history()
    for task_result in task_history:
        if task_result.task_id == task_id:
            return TaskResponse(
                task_id=task_id,
                status="completed" if task_result.success else "failed",
                result=task_result.result,
                error=task_result.error,
                execution_time=task_result.execution_time,
                created_at=datetime.now().isoformat()
            )
    
    raise HTTPException(status_code=404, detail="Task not found")

@app.get("/tasks", response_model=List[TaskResponse])
async def list_tasks():
    """List all tasks"""
    if not enhanced_agent:
        raise HTTPException(status_code=503, detail="Enhanced agent not available")
    
    tasks = []
    
    # Add active tasks
    active_tasks = enhanced_agent.get_active_tasks()
    for task_id, task in active_tasks.items():
        tasks.append(TaskResponse(
            task_id=task_id,
            status="running",
            created_at=datetime.now().isoformat()
        ))
    
    # Add completed tasks
    task_history = enhanced_agent.get_task_history()
    for task_result in task_history:
        tasks.append(TaskResponse(
            task_id=task_result.task_id,
            status="completed" if task_result.success else "failed",
            result=task_result.result,
            error=task_result.error,
            execution_time=task_result.execution_time,
            created_at=datetime.now().isoformat()
        ))
    
    return tasks

# Direct generation endpoints
@app.post("/generate")
async def generate_text(request: GenerationRequest):
    """Generate text directly using DeepSeek"""
    if not deepseek_provider:
        raise HTTPException(status_code=503, detail="DeepSeek provider not available")
    
    config = GenerationConfig(
        temperature=request.temperature,
        max_tokens=request.max_tokens,
        stream=request.stream
    )
    
    try:
        if request.stream:
            # For streaming, we'll return a simple response for now
            # In a real implementation, you'd use Server-Sent Events
            response = await deepseek_provider.generate_completion(request.prompt, config)
            return {"content": response.content, "streaming": False}
        else:
            response = await deepseek_provider.generate_completion(request.prompt, config)
            return {
                "content": response.content,
                "usage": response.usage,
                "model": response.model,
                "response_time": response.response_time
            }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time communication"""
    await websocket.accept()
    websocket_connections.append(websocket)
    
    try:
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle different message types
            if message.get("type") == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
            
    except WebSocketDisconnect:
        websocket_connections.remove(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        if websocket in websocket_connections:
            websocket_connections.remove(websocket)

async def broadcast_to_websockets(message: Dict[str, Any]):
    """Broadcast message to all connected WebSocket clients"""
    if not websocket_connections:
        return
    
    message_str = json.dumps(message)
    disconnected = []
    
    for websocket in websocket_connections:
        try:
            await websocket.send_text(message_str)
        except Exception:
            disconnected.append(websocket)
    
    # Remove disconnected clients
    for websocket in disconnected:
        websocket_connections.remove(websocket)

# Static files and frontend
@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serve the main frontend page"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Enhanced CodeAgent Integration</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .container { max-width: 1200px; margin: 0 auto; }
            .header { text-align: center; margin-bottom: 30px; }
            .status { padding: 10px; border-radius: 5px; margin-bottom: 20px; }
            .status.healthy { background-color: #d4edda; color: #155724; }
            .status.degraded { background-color: #fff3cd; color: #856404; }
            .section { margin-bottom: 30px; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }
            .form-group { margin-bottom: 15px; }
            label { display: block; margin-bottom: 5px; font-weight: bold; }
            input, select, textarea { width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; }
            button { background-color: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; }
            button:hover { background-color: #0056b3; }
            .result { background-color: #f8f9fa; padding: 15px; border-radius: 4px; margin-top: 15px; }
            .error { background-color: #f8d7da; color: #721c24; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Enhanced CodeAgent Integration</h1>
                <p>CodeAgent03 + DeepSeek R1 + vLLM Local Deployment</p>
                <div id="status" class="status">Checking status...</div>
            </div>
            
            <div class="section">
                <h2>Quick Text Generation</h2>
                <div class="form-group">
                    <label for="prompt">Prompt:</label>
                    <textarea id="prompt" rows="4" placeholder="Enter your prompt here..."></textarea>
                </div>
                <div class="form-group">
                    <label for="temperature">Temperature:</label>
                    <input type="number" id="temperature" value="0.6" min="0" max="2" step="0.1">
                </div>
                <button onclick="generateText()">Generate</button>
                <div id="generation-result" class="result" style="display: none;"></div>
            </div>
            
            <div class="section">
                <h2>Code Tasks</h2>
                <div class="form-group">
                    <label for="task-type">Task Type:</label>
                    <select id="task-type">
                        <option value="code_generation">Code Generation</option>
                        <option value="code_review">Code Review</option>
                        <option value="code_debugging">Code Debugging</option>
                        <option value="code_optimization">Code Optimization</option>
                        <option value="code_explanation">Code Explanation</option>
                        <option value="test_generation">Test Generation</option>
                        <option value="documentation">Documentation</option>
                        <option value="refactoring">Refactoring</option>
                    </select>
                </div>
                <div class="form-group">
                    <label for="task-description">Description:</label>
                    <textarea id="task-description" rows="3" placeholder="Describe the task..."></textarea>
                </div>
                <div class="form-group">
                    <label for="task-language">Language (optional):</label>
                    <input type="text" id="task-language" placeholder="e.g., python, javascript">
                </div>
                <div class="form-group">
                    <label for="task-code">Code (for review/debug/etc.):</label>
                    <textarea id="task-code" rows="6" placeholder="Paste code here if needed..."></textarea>
                </div>
                <button onclick="executeTask()">Execute Task</button>
                <div id="task-result" class="result" style="display: none;"></div>
            </div>
            
            <div class="section">
                <h2>System Information</h2>
                <div id="system-info">Loading...</div>
            </div>
        </div>
        
        <script>
            // Check system status
            async function checkStatus() {
                try {
                    const response = await fetch('/health');
                    const data = await response.json();
                    const statusDiv = document.getElementById('status');
                    
                    if (data.status === 'healthy') {
                        statusDiv.className = 'status healthy';
                        statusDiv.textContent = '✅ System is healthy and ready';
                    } else {
                        statusDiv.className = 'status degraded';
                        statusDiv.textContent = '⚠️ System is degraded - some features may not work';
                    }
                } catch (error) {
                    const statusDiv = document.getElementById('status');
                    statusDiv.className = 'status error';
                    statusDiv.textContent = '❌ Cannot connect to backend';
                }
            }
            
            // Generate text
            async function generateText() {
                const prompt = document.getElementById('prompt').value;
                const temperature = parseFloat(document.getElementById('temperature').value);
                const resultDiv = document.getElementById('generation-result');
                
                if (!prompt.trim()) {
                    alert('Please enter a prompt');
                    return;
                }
                
                resultDiv.style.display = 'block';
                resultDiv.textContent = 'Generating...';
                
                try {
                    const response = await fetch('/generate', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ prompt, temperature })
                    });
                    
                    const data = await response.json();
                    resultDiv.innerHTML = '<strong>Generated Text:</strong><br><pre>' + data.content + '</pre>';
                } catch (error) {
                    resultDiv.className = 'result error';
                    resultDiv.textContent = 'Error: ' + error.message;
                }
            }
            
            // Execute task
            async function executeTask() {
                const taskType = document.getElementById('task-type').value;
                const description = document.getElementById('task-description').value;
                const language = document.getElementById('task-language').value;
                const code = document.getElementById('task-code').value;
                const resultDiv = document.getElementById('task-result');
                
                if (!description.trim()) {
                    alert('Please enter a task description');
                    return;
                }
                
                const context = {};
                if (code.trim()) {
                    context.code = code;
                }
                
                const taskRequest = {
                    type: taskType,
                    description: description,
                    language: language || null,
                    context: Object.keys(context).length > 0 ? context : null
                };
                
                resultDiv.style.display = 'block';
                resultDiv.textContent = 'Executing task...';
                
                try {
                    const response = await fetch('/tasks/execute', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(taskRequest)
                    });
                    
                    const data = await response.json();
                    const taskId = data.task_id;
                    
                    // Poll for result
                    pollTaskResult(taskId, resultDiv);
                } catch (error) {
                    resultDiv.className = 'result error';
                    resultDiv.textContent = 'Error: ' + error.message;
                }
            }
            
            // Poll task result
            async function pollTaskResult(taskId, resultDiv) {
                try {
                    const response = await fetch(`/tasks/${taskId}`);
                    const data = await response.json();
                    
                    if (data.status === 'running' || data.status === 'queued') {
                        setTimeout(() => pollTaskResult(taskId, resultDiv), 1000);
                        return;
                    }
                    
                    if (data.status === 'completed') {
                        resultDiv.className = 'result';
                        resultDiv.innerHTML = '<strong>Task Result:</strong><br><pre>' + data.result + '</pre>';
                    } else {
                        resultDiv.className = 'result error';
                        resultDiv.textContent = 'Task failed: ' + (data.error || 'Unknown error');
                    }
                } catch (error) {
                    resultDiv.className = 'result error';
                    resultDiv.textContent = 'Error checking task status: ' + error.message;
                }
            }
            
            // Load system info
            async function loadSystemInfo() {
                try {
                    const response = await fetch('/system/info');
                    const data = await response.json();
                    const infoDiv = document.getElementById('system-info');
                    
                    infoDiv.innerHTML = `
                        <p><strong>Deployment Type:</strong> ${data.deployment_type}</p>
                        <p><strong>Performance Tier:</strong> ${data.performance_tier}</p>
                        <p><strong>Model:</strong> ${data.model_name}</p>
                        <p><strong>Active Tasks:</strong> ${data.active_tasks}</p>
                        <p><strong>Completed Tasks:</strong> ${data.total_tasks_completed}</p>
                    `;
                } catch (error) {
                    document.getElementById('system-info').textContent = 'Error loading system info';
                }
            }
            
            // Initialize
            checkStatus();
            loadSystemInfo();
            setInterval(checkStatus, 30000); // Check status every 30 seconds
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=12000,  # Use the provided port
        reload=True,
        log_level="info"
    )