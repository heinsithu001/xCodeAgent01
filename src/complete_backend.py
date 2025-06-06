#!/usr/bin/env python3
"""
Complete Backend Server for ZeroCostxCode Professional
Integrates all core features: Database, Auth, Execution, WebSocket, AI
"""

import asyncio
import json
import logging
import os
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List
import uvicorn

# Add src to path
sys.path.append(str(Path(__file__).parent))

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer
from pydantic import BaseModel

# Import our modules
try:
    from database.sqlite_db import db
    from auth.simple_auth import init_auth
    from execution.secure_executor import executor
    from websocket.realtime_manager import connection_manager
    from models.deepseek_provider import LocalDeepSeekProvider
except ImportError as e:
    print(f"Import error: {e}")
    print("Please ensure all modules are in the correct path")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="ZeroCostxCode Professional Backend",
    description="Complete AI-powered coding platform",
    version="3.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response Models
class UserRegister(BaseModel):
    username: str
    email: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class ProjectCreate(BaseModel):
    name: str
    description: str = ""

class FileCreate(BaseModel):
    filename: str
    content: str
    file_type: str
    project_id: int

class CodeExecute(BaseModel):
    code: str
    language: str = "python"
    filename: str = None

class AIRequest(BaseModel):
    prompt: str
    language: str = "python"
    task_type: str = "generate"  # generate, analyze, debug, optimize

# Global instances
auth = None
ai_provider = None

@app.on_event("startup")
async def startup_event():
    """Initialize all services on startup"""
    global auth, ai_provider
    
    # Initialize database
    await db.initialize()
    logger.info("Database initialized")
    
    # Initialize authentication
    auth = init_auth(db)
    logger.info("Authentication initialized")
    
    # Initialize AI provider
    ai_provider = LocalDeepSeekProvider()
    await ai_provider.__aenter__()
    logger.info("AI provider initialized")
    
    # Create default user if none exists
    try:
        await db.create_user("demo", "demo@zerocostxcode.com", "demo123")
        logger.info("Demo user created")
    except:
        pass  # User already exists

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    if ai_provider:
        await ai_provider.__aexit__(None, None, None)

# Serve static files
frontend_path = Path(__file__).parent.parent / "frontend-professional"
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")

@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    """Serve the frontend"""
    if frontend_path.exists() and (frontend_path / "index.html").exists():
        with open(frontend_path / "index.html", "r") as f:
            return HTMLResponse(content=f.read())
    else:
        return HTMLResponse(content="""
        <html>
            <head><title>ZeroCostxCode Professional</title></head>
            <body>
                <h1>ZeroCostxCode Professional Backend</h1>
                <p>Backend is running! Frontend not found.</p>
                <ul>
                    <li><a href="/docs">API Documentation</a></li>
                    <li><a href="/health">Health Check</a></li>
                </ul>
            </body>
        </html>
        """)

# Health and Status Endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    ai_healthy = await ai_provider.health_check() if ai_provider else False
    
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "database": True,
            "ai_provider": ai_healthy,
            "executor": True,
            "websocket": True
        },
        "stats": connection_manager.get_stats()
    }

@app.get("/api/v3/status")
async def api_status():
    """API status endpoint"""
    return {
        "api_version": "v3.0",
        "status": "running",
        "features": [
            "authentication",
            "file_management", 
            "code_execution",
            "ai_integration",
            "real_time_collaboration"
        ],
        "supported_languages": executor.get_supported_languages()
    }

# Authentication Endpoints
@app.post("/api/v3/auth/register")
async def register(user_data: UserRegister):
    """Register new user"""
    return await auth.register_user(user_data.username, user_data.email, user_data.password)

@app.post("/api/v3/auth/login")
async def login(user_data: UserLogin):
    """Login user"""
    return await auth.login_user(user_data.username, user_data.password)

@app.get("/api/v3/auth/me")
async def get_current_user_info(current_user: dict = Depends(auth.get_current_user)):
    """Get current user information"""
    return current_user

# Project Management Endpoints
@app.post("/api/v3/projects")
async def create_project(project_data: ProjectCreate, current_user: dict = Depends(auth.get_current_user)):
    """Create new project"""
    return await db.create_project(project_data.name, project_data.description, current_user["id"])

@app.get("/api/v3/projects")
async def get_user_projects(current_user: dict = Depends(auth.get_current_user)):
    """Get user's projects"""
    return await db.get_user_projects(current_user["id"])

@app.get("/api/v3/projects/{project_id}/files")
async def get_project_files(project_id: int, current_user: dict = Depends(auth.get_current_user)):
    """Get files in a project"""
    return await db.get_project_files(project_id)

# File Management Endpoints
@app.post("/api/v3/files")
async def create_file(file_data: FileCreate, current_user: dict = Depends(auth.get_current_user)):
    """Create or update file"""
    return await db.save_file(
        file_data.filename, 
        file_data.content, 
        file_data.file_type, 
        file_data.project_id
    )

@app.get("/api/v3/files/{file_id}")
async def get_file(file_id: int, current_user: dict = Depends(auth.get_current_user)):
    """Get file by ID"""
    file_data = await db.get_file(file_id)
    if not file_data:
        raise HTTPException(status_code=404, detail="File not found")
    return file_data

@app.put("/api/v3/files/{file_id}")
async def update_file(file_id: int, content: str = Form(...), current_user: dict = Depends(auth.get_current_user)):
    """Update file content"""
    file_data = await db.get_file(file_id)
    if not file_data:
        raise HTTPException(status_code=404, detail="File not found")
    
    return await db.save_file(
        file_data["filename"],
        content,
        file_data["file_type"],
        file_data["project_id"]
    )

@app.delete("/api/v3/files/{file_id}")
async def delete_file(file_id: int, current_user: dict = Depends(auth.get_current_user)):
    """Delete file"""
    success = await db.delete_file(file_id)
    if not success:
        raise HTTPException(status_code=404, detail="File not found")
    return {"success": True, "message": "File deleted"}

@app.post("/api/v3/files/upload")
async def upload_file(
    file: UploadFile = File(...),
    project_id: int = Form(...),
    current_user: dict = Depends(auth.get_current_user)
):
    """Upload file"""
    content = await file.read()
    
    # Determine file type
    file_type = Path(file.filename).suffix
    
    # For text files, decode content
    if file_type in ['.py', '.js', '.html', '.css', '.md', '.txt', '.json']:
        content = content.decode('utf-8')
    else:
        # For binary files, store as base64
        import base64
        content = base64.b64encode(content).decode('utf-8')
    
    return await db.save_file(file.filename, content, file_type, project_id)

# Code Execution Endpoints
@app.post("/api/v3/execute")
async def execute_code(exec_data: CodeExecute, current_user: dict = Depends(auth.get_current_user)):
    """Execute code"""
    return await executor.execute_code(
        exec_data.code,
        exec_data.language,
        current_user["id"],
        exec_data.filename
    )

@app.get("/api/v3/languages")
async def get_supported_languages():
    """Get supported programming languages"""
    return executor.get_supported_languages()

# AI Integration Endpoints
@app.post("/api/v3/ai/generate")
async def ai_generate(ai_request: AIRequest, current_user: dict = Depends(auth.get_current_user)):
    """Generate code using AI"""
    try:
        if ai_request.task_type == "generate":
            response = await ai_provider.generate_code(ai_request.prompt, ai_request.language)
        elif ai_request.task_type == "analyze":
            response = await ai_provider.analyze_code(ai_request.prompt, "review")
        else:
            response = await ai_provider.generate_completion(ai_request.prompt)
        
        return {
            "success": True,
            "content": response.content,
            "model": response.model,
            "usage": response.usage,
            "response_time": response.response_time
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v3/ai/analyze")
async def ai_analyze_code(code: str = Form(...), analysis_type: str = Form("review"), current_user: dict = Depends(auth.get_current_user)):
    """Analyze code using AI"""
    try:
        response = await ai_provider.analyze_code(code, analysis_type)
        return {
            "success": True,
            "analysis": response.content,
            "type": analysis_type,
            "model": response.model,
            "usage": response.usage
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# WebSocket Endpoints
@app.websocket("/ws/{connection_id}")
async def websocket_endpoint(websocket: WebSocket, connection_id: str):
    """Main WebSocket endpoint for real-time features"""
    user_id = None
    
    try:
        await connection_manager.connect(websocket, connection_id)
        
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            message_type = message.get("type")
            
            if message_type == "auth":
                # Authenticate user
                token = message.get("token")
                if token and auth:
                    token_data = auth.verify_token(token)
                    if token_data:
                        user_id = token_data["user_id"]
                        await connection_manager.send_to_connection({
                            "type": "auth_success",
                            "user_id": user_id
                        }, connection_id)
                    else:
                        await connection_manager.send_to_connection({
                            "type": "auth_error",
                            "message": "Invalid token"
                        }, connection_id)
            
            elif message_type == "join_project":
                # Join project collaboration room
                project_id = message.get("project_id")
                if project_id:
                    connection_manager.join_project_room(connection_id, project_id)
                    await connection_manager.broadcast_to_project({
                        "type": "user_joined_project",
                        "user_id": user_id,
                        "project_id": project_id
                    }, project_id, exclude_connection=connection_id)
            
            elif message_type == "terminal_command":
                # Execute terminal command
                if user_id:
                    session_id = message.get("session_id")
                    if not session_id:
                        session_id = await connection_manager.create_terminal_session(user_id, connection_id)
                    
                    command = message.get("command", "")
                    await connection_manager.handle_terminal_command(session_id, command, executor)
            
            elif message_type == "ai_stream":
                # Stream AI response
                if user_id:
                    prompt = message.get("prompt", "")
                    await connection_manager.stream_ai_response(connection_id, ai_provider, prompt)
            
            elif message_type == "file_change":
                # Handle real-time file changes
                file_id = message.get("file_id")
                changes = message.get("changes", {})
                if file_id:
                    await connection_manager.handle_file_change(file_id, connection_id, changes)
    
    except WebSocketDisconnect:
        connection_manager.disconnect(connection_id, user_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        connection_manager.disconnect(connection_id, user_id)

# Demo/Testing Endpoints
@app.get("/api/v3/demo/create-sample-project")
async def create_sample_project(current_user: dict = Depends(auth.get_current_user)):
    """Create a sample project for testing"""
    # Create project
    project = await db.create_project("Sample Project", "A sample project for testing", current_user["id"])
    
    # Create sample files
    sample_files = [
        {
            "filename": "main.py",
            "content": '''#!/usr/bin/env python3
"""
Sample Python application
"""

def hello_world():
    """Print hello world message"""
    print("Hello, World from ZeroCostxCode!")
    return "Hello, World!"

def fibonacci(n):
    """Calculate fibonacci sequence"""
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

if __name__ == "__main__":
    hello_world()
    
    # Calculate first 10 fibonacci numbers
    print("Fibonacci sequence:")
    for i in range(10):
        print(f"F({i}) = {fibonacci(i)}")
''',
            "file_type": ".py"
        },
        {
            "filename": "README.md",
            "content": '''# Sample Project

This is a sample project created by ZeroCostxCode Professional.

## Features

- Python code execution
- AI-powered code generation
- Real-time collaboration
- File management

## Usage

1. Edit the code in `main.py`
2. Click "Run Code" to execute
3. Use AI assistant for help

## AI Commands

Try these prompts with the AI:
- "Add error handling to the fibonacci function"
- "Create a unit test for hello_world function"
- "Optimize the fibonacci function using memoization"
''',
            "file_type": ".md"
        },
        {
            "filename": "requirements.txt",
            "content": '''# Python dependencies
# Add your project dependencies here

# Example:
# requests>=2.25.0
# numpy>=1.20.0
# pandas>=1.3.0
''',
            "file_type": ".txt"
        }
    ]
    
    # Save files
    for file_data in sample_files:
        await db.save_file(
            file_data["filename"],
            file_data["content"],
            file_data["file_type"],
            project["id"]
        )
    
    return {
        "success": True,
        "project": project,
        "files_created": len(sample_files)
    }

if __name__ == "__main__":
    # Install required packages
    import subprocess
    import sys
    
    required_packages = [
        "aiosqlite",
        "PyJWT",
        "python-multipart"
    ]
    
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
        except ImportError:
            print(f"Installing {package}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
    
    # Run server
    uvicorn.run(
        "complete_backend:app",
        host="0.0.0.0",
        port=12000,
        reload=False,
        log_level="info"
    )