#!/usr/bin/env python3
"""
Unified Backend for xCodeAgent
Combines all functionality with correct API endpoints for frontend integration
"""

import asyncio
import json
import logging
import os
import time
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
import aiohttp
import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import psutil

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
VLLM_SERVER_URL = os.getenv("VLLM_SERVER_URL", "http://localhost:8000")
BACKEND_HOST = os.getenv("BACKEND_HOST", "0.0.0.0")
BACKEND_PORT = int(os.getenv("BACKEND_PORT", "12000"))

# Pydantic Models
class ChatRequest(BaseModel):
    message: str
    execution_mode: str = "hybrid"
    context: Optional[Dict[str, Any]] = None

class SystemStatus(BaseModel):
    status: str
    vllm_server: Dict[str, Any]
    backend_info: Dict[str, Any]
    timestamp: str

class CodeGenerationRequest(BaseModel):
    prompt: str
    language: str = "python"
    complexity: str = "standard"
    include_tests: bool = False

# FastAPI App
app = FastAPI(
    title="xCodeAgent Unified Backend",
    description="Unified backend with correct API endpoints for frontend integration",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# vLLM Client
class VLLMClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def get_session(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
        
    async def check_health(self) -> Dict[str, Any]:
        try:
            session = await self.get_session()
            async with session.get(f"{self.base_url}/health", timeout=5) as response:
                if response.status == 200:
                    return {"status": "healthy", "url": self.base_url}
                else:
                    return {"status": "unhealthy", "url": self.base_url, "error": f"HTTP {response.status}"}
        except Exception as e:
            return {"status": "unreachable", "url": self.base_url, "error": str(e)}
    
    async def generate_completion(self, prompt: str, **kwargs) -> Dict[str, Any]:
        try:
            session = await self.get_session()
            payload = {
                "model": "deepseek-ai/DeepSeek-R1-0528",
                "prompt": prompt,
                "max_tokens": kwargs.get("max_tokens", 1024),
                "temperature": kwargs.get("temperature", 0.1),
                "stream": False
            }
            
            async with session.post(
                f"{self.base_url}/v1/completions",
                json=payload,
                timeout=30
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "success": True,
                        "response": data.get("choices", [{}])[0].get("text", ""),
                        "model": data.get("model", "unknown")
                    }
                else:
                    error_text = await response.text()
                    return {
                        "success": False,
                        "error": f"vLLM server error: {response.status} - {error_text}"
                    }
        except Exception as e:
            logger.error(f"vLLM generation failed: {e}")
            return {
                "success": False,
                "error": f"Connection failed: {str(e)}"
            }
    
    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()

# Global vLLM client
vllm_client = VLLMClient(VLLM_SERVER_URL)

# Session management
sessions = {}

# Startup/Shutdown events
@app.on_event("startup")
async def startup_event():
    logger.info("Starting xCodeAgent Unified Backend")
    logger.info(f"vLLM Server URL: {VLLM_SERVER_URL}")
    logger.info(f"Backend running on {BACKEND_HOST}:{BACKEND_PORT}")

@app.on_event("shutdown")
async def shutdown_event():
    await vllm_client.close()
    logger.info("Backend shutdown complete")

# Serve frontend files
app.mount("/static", StaticFiles(directory="frontend-v2"), name="static")

@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    """Serve the main frontend page"""
    try:
        with open("frontend-v2/index.html", "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(
            content="<h1>Frontend not found</h1><p>Please ensure frontend-v2/index.html exists</p>",
            status_code=404
        )

# Health check
@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# API v3 Endpoints (matching frontend expectations)
@app.get("/api/v3/status")
async def get_system_status():
    """Get system status including vLLM server health"""
    try:
        # Check vLLM server
        vllm_status = await vllm_client.check_health()
        
        # Get system info
        system_info = {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent,
            "uptime": time.time() - psutil.boot_time()
        }
        
        return {
            "success": True,
            "status": "operational",
            "vllm_server": vllm_status,
            "backend_info": {
                "version": "1.0.0",
                "host": BACKEND_HOST,
                "port": BACKEND_PORT,
                "system": system_info
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.post("/api/v3/chat")
async def chat_endpoint(request: ChatRequest):
    """Main chat endpoint for AI interactions"""
    try:
        session_id = str(uuid.uuid4())
        
        # Store session
        sessions[session_id] = {
            "created_at": datetime.now().isoformat(),
            "messages": []
        }
        
        # Add user message to session
        sessions[session_id]["messages"].append({
            "role": "user",
            "content": request.message,
            "timestamp": datetime.now().isoformat()
        })
        
        # Generate AI response
        if request.execution_mode == "demo":
            # Demo mode - return mock response
            ai_response = f"Demo response to: {request.message}\n\nThis is a demonstration of the xCodeAgent system. In production mode, this would connect to the DeepSeek R1 model via vLLM server."
        else:
            # Try to get real AI response
            vllm_result = await vllm_client.generate_completion(
                prompt=request.message,
                max_tokens=1024,
                temperature=0.1
            )
            
            if vllm_result["success"]:
                ai_response = vllm_result["response"]
            else:
                # Fallback to demo mode if vLLM fails
                ai_response = f"AI Response (Fallback Mode): {request.message}\n\nNote: vLLM server connection failed. Error: {vllm_result.get('error', 'Unknown error')}"
        
        # Add AI response to session
        sessions[session_id]["messages"].append({
            "role": "assistant",
            "content": ai_response,
            "timestamp": datetime.now().isoformat()
        })
        
        return {
            "success": True,
            "session_id": session_id,
            "execution_mode": request.execution_mode,
            "data": {
                "response": ai_response,
                "message_count": len(sessions[session_id]["messages"])
            },
            "metadata": {
                "context": request.context,
                "timestamp": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Chat endpoint failed: {e}")
        return {
            "success": False,
            "error": "An internal error has occurred.",
            "timestamp": datetime.now().isoformat()
        }

@app.post("/api/v3/generate-code")
async def generate_code(request: CodeGenerationRequest):
    """Generate code based on prompt"""
    try:
        # Create a code generation prompt
        code_prompt = f"""Generate {request.language} code for the following request:
{request.prompt}

Requirements:
- Language: {request.language}
- Complexity: {request.complexity}
- Include tests: {request.include_tests}

Please provide clean, well-commented code."""

        # Generate code using vLLM
        result = await vllm_client.generate_completion(
            prompt=code_prompt,
            max_tokens=2048,
            temperature=0.1
        )
        
        if result["success"]:
            return {
                "success": True,
                "data": {
                    "code": result["response"],
                    "language": request.language,
                    "complexity": request.complexity
                }
            }
        else:
            return {
                "success": False,
                "error": result["error"]
            }
            
    except Exception as e:
        logger.error(f"Code generation failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@app.get("/api/v3/sessions/{session_id}")
async def get_session(session_id: str):
    """Get session history"""
    if session_id in sessions:
        return {
            "success": True,
            "session": sessions[session_id]
        }
    else:
        raise HTTPException(status_code=404, detail="Session not found")

@app.websocket("/ws/{connection_id}")
async def websocket_endpoint(websocket: WebSocket, connection_id: str):
    """WebSocket endpoint for real-time communication"""
    await websocket.accept()
    logger.info(f"WebSocket connection established: {connection_id}")
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Echo back with timestamp
            response = {
                "type": "response",
                "data": message,
                "timestamp": datetime.now().isoformat(),
                "connection_id": connection_id
            }
            
            await websocket.send_text(json.dumps(response))
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {connection_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")

if __name__ == "__main__":
    logger.info("Starting xCodeAgent Unified Backend")
    uvicorn.run(
        app,
        host=BACKEND_HOST,
        port=BACKEND_PORT,
        log_level="info",
        access_log=True
    )