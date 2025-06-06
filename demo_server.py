#!/usr/bin/env python3
"""
Demo Server for Enhanced CodeAgent Integration
A simplified version to demonstrate the system without requiring vLLM.
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pydantic models
class TaskRequest(BaseModel):
    type: str
    description: str
    context: Dict[str, Any] = {}
    language: str = "python"

class HealthResponse(BaseModel):
    status: str
    message: str
    timestamp: str

# Create FastAPI app
app = FastAPI(
    title="Enhanced CodeAgent Integration - Demo",
    description="Demo version of the integrated system",
    version="1.0.0-demo"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        message="Enhanced CodeAgent Integration Demo is running",
        timestamp=datetime.now().isoformat()
    )

@app.get("/system/info")
async def get_system_info():
    """Get system information"""
    return {
        "deployment_type": "demo",
        "performance_tier": "demo",
        "model_name": "demo-model",
        "active_tasks": 0,
        "total_tasks_completed": 0,
        "features": [
            "Code Generation",
            "Code Review",
            "Code Debugging",
            "Documentation",
            "Test Generation"
        ]
    }

@app.post("/tasks/execute")
async def execute_task(task_request: TaskRequest):
    """Execute a task (demo version)"""
    
    # Simulate task processing
    await asyncio.sleep(1)  # Simulate processing time
    
    # Generate demo responses based on task type
    if task_request.type == "code_generation":
        result = f"""# Generated {task_request.language} code for: {task_request.description}

def example_function():
    \"\"\"
    {task_request.description}
    \"\"\"
    # TODO: Implement the actual functionality
    print("This is a demo implementation")
    return "demo_result"

# Example usage
if __name__ == "__main__":
    result = example_function()
    print(f"Result: {{result}}")
"""
    
    elif task_request.type == "code_review":
        code = task_request.context.get("code", "No code provided")
        result = f"""# Code Review Results

## Code Analysis
The provided code has been analyzed:

```
{code[:200]}...
```

## Findings:
✅ **Strengths:**
- Code structure is readable
- Basic functionality appears correct

⚠️ **Suggestions:**
- Add error handling
- Include type hints
- Add unit tests
- Consider edge cases

## Overall Rating: 7/10
The code is functional but could benefit from additional robustness and testing.
"""
    
    elif task_request.type == "documentation":
        result = f"""# Documentation for: {task_request.description}

## Overview
This module provides functionality for {task_request.description.lower()}.

## Installation
```bash
pip install required-package
```

## Usage
```python
from module import function

# Example usage
result = function()
print(result)
```

## API Reference
### Functions
- `function()`: Main function that performs the task

## Examples
See the examples directory for more detailed usage examples.
"""
    
    else:
        result = f"""# {task_request.type.replace('_', ' ').title()} Result

Task: {task_request.description}
Type: {task_request.type}
Language: {task_request.language}

This is a demo response showing that the system can handle various task types.
In a full deployment, this would be processed by the DeepSeek R1 model.
"""
    
    return {
        "task_id": f"demo-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        "status": "completed",
        "result": result,
        "execution_time": 1.0,
        "created_at": datetime.now().isoformat()
    }

@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serve the demo interface"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Enhanced CodeAgent Integration - Demo</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
            .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .header { text-align: center; margin-bottom: 30px; }
            .header h1 { color: #2c3e50; margin-bottom: 10px; }
            .header p { color: #7f8c8d; font-size: 18px; }
            .status { padding: 15px; border-radius: 8px; margin-bottom: 20px; text-align: center; }
            .status.healthy { background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
            .section { margin-bottom: 30px; padding: 20px; border: 1px solid #e9ecef; border-radius: 8px; background: #f8f9fa; }
            .section h2 { color: #495057; margin-top: 0; }
            .form-group { margin-bottom: 15px; }
            label { display: block; margin-bottom: 5px; font-weight: bold; color: #495057; }
            input, select, textarea { width: 100%; padding: 10px; border: 1px solid #ced4da; border-radius: 5px; font-size: 14px; }
            button { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 12px 24px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; font-weight: bold; }
            button:hover { transform: translateY(-2px); box-shadow: 0 4px 8px rgba(0,0,0,0.2); }
            .result { background-color: #ffffff; padding: 20px; border-radius: 8px; margin-top: 15px; border: 1px solid #dee2e6; }
            .result pre { background: #f8f9fa; padding: 15px; border-radius: 5px; overflow-x: auto; }
            .features { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px; margin-top: 20px; }
            .feature { background: white; padding: 15px; border-radius: 8px; border: 1px solid #e9ecef; text-align: center; }
            .feature h3 { color: #495057; margin-top: 0; }
            .demo-badge { background: linear-gradient(135deg, #ff6b6b, #ee5a24); color: white; padding: 5px 15px; border-radius: 20px; font-size: 12px; font-weight: bold; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🚀 Enhanced CodeAgent Integration</h1>
                <p>CodeAgent03 + DeepSeek R1 + vLLM Local Deployment</p>
                <span class="demo-badge">DEMO MODE</span>
                <div id="status" class="status healthy">✅ Demo system is running and ready</div>
            </div>
            
            <div class="section">
                <h2>🎯 System Features</h2>
                <div class="features">
                    <div class="feature">
                        <h3>🔧 Code Generation</h3>
                        <p>Generate code from natural language descriptions</p>
                    </div>
                    <div class="feature">
                        <h3>📝 Code Review</h3>
                        <p>Analyze code quality and suggest improvements</p>
                    </div>
                    <div class="feature">
                        <h3>🐛 Debugging</h3>
                        <p>Identify and fix code issues</p>
                    </div>
                    <div class="feature">
                        <h3>📚 Documentation</h3>
                        <p>Generate comprehensive documentation</p>
                    </div>
                    <div class="feature">
                        <h3>🧪 Test Generation</h3>
                        <p>Create unit tests for your code</p>
                    </div>
                    <div class="feature">
                        <h3>⚡ Optimization</h3>
                        <p>Improve code performance and efficiency</p>
                    </div>
                </div>
            </div>
            
            <div class="section">
                <h2>🛠️ Try the System</h2>
                <div class="form-group">
                    <label for="task-type">Task Type:</label>
                    <select id="task-type">
                        <option value="code_generation">Code Generation</option>
                        <option value="code_review">Code Review</option>
                        <option value="documentation">Documentation</option>
                        <option value="test_generation">Test Generation</option>
                    </select>
                </div>
                <div class="form-group">
                    <label for="task-description">Description:</label>
                    <textarea id="task-description" rows="3" placeholder="Describe what you want to accomplish...">Create a Python function to calculate the factorial of a number</textarea>
                </div>
                <div class="form-group">
                    <label for="task-language">Programming Language:</label>
                    <input type="text" id="task-language" value="python" placeholder="e.g., python, javascript, java">
                </div>
                <div class="form-group" id="code-group" style="display: none;">
                    <label for="task-code">Code (for review/debugging):</label>
                    <textarea id="task-code" rows="6" placeholder="Paste your code here..."></textarea>
                </div>
                <button onclick="executeTask()">🚀 Execute Task</button>
                <div id="task-result" class="result" style="display: none;"></div>
            </div>
            
            <div class="section">
                <h2>📊 System Information</h2>
                <div id="system-info">Loading...</div>
            </div>
        </div>
        
        <script>
            // Show/hide code input based on task type
            document.getElementById('task-type').addEventListener('change', function() {
                const codeGroup = document.getElementById('code-group');
                const taskType = this.value;
                if (taskType === 'code_review' || taskType === 'debugging') {
                    codeGroup.style.display = 'block';
                } else {
                    codeGroup.style.display = 'none';
                }
            });
            
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
                if (code.trim() && (taskType === 'code_review' || taskType === 'debugging')) {
                    context.code = code;
                }
                
                const taskRequest = {
                    type: taskType,
                    description: description,
                    language: language,
                    context: context
                };
                
                resultDiv.style.display = 'block';
                resultDiv.innerHTML = '<p>🔄 Processing task...</p>';
                
                try {
                    const response = await fetch('/tasks/execute', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(taskRequest)
                    });
                    
                    const data = await response.json();
                    
                    resultDiv.innerHTML = `
                        <h3>✅ Task Completed</h3>
                        <p><strong>Task ID:</strong> ${data.task_id}</p>
                        <p><strong>Execution Time:</strong> ${data.execution_time}s</p>
                        <h4>Result:</h4>
                        <pre>${data.result}</pre>
                    `;
                } catch (error) {
                    resultDiv.innerHTML = `<p style="color: red;">❌ Error: ${error.message}</p>`;
                }
            }
            
            // Load system info
            async function loadSystemInfo() {
                try {
                    const response = await fetch('/system/info');
                    const data = await response.json();
                    const infoDiv = document.getElementById('system-info');
                    
                    infoDiv.innerHTML = `
                        <p><strong>🏗️ Deployment Type:</strong> ${data.deployment_type}</p>
                        <p><strong>⚡ Performance Tier:</strong> ${data.performance_tier}</p>
                        <p><strong>🤖 Model:</strong> ${data.model_name}</p>
                        <p><strong>📋 Active Tasks:</strong> ${data.active_tasks}</p>
                        <p><strong>✅ Completed Tasks:</strong> ${data.total_tasks_completed}</p>
                        <p><strong>🎯 Features:</strong> ${data.features.join(', ')}</p>
                    `;
                } catch (error) {
                    document.getElementById('system-info').innerHTML = '<p style="color: red;">Error loading system info</p>';
                }
            }
            
            // Initialize
            loadSystemInfo();
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

if __name__ == "__main__":
    print("🚀 Starting Enhanced CodeAgent Integration Demo Server...")
    print("📱 Access the demo at: http://localhost:12000")
    print("📚 API docs at: http://localhost:12000/docs")
    print("❤️  Health check at: http://localhost:12000/health")
    
    uvicorn.run(
        "demo_server:app",
        host="0.0.0.0",
        port=12000,
        reload=False,
        log_level="info"
    )