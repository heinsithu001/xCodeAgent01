#!/usr/bin/env python3
"""
Production Unified Backend for xCodeAgent
Real DeepSeek-R1-0528 integration with comprehensive monitoring
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
from fastapi.responses import JSONResponse, HTMLResponse, Response
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
PRODUCTION_MODE = os.getenv("PRODUCTION_MODE", "true").lower() == "true"

# Pydantic Models
class ChatRequest(BaseModel):
    message: str
    execution_mode: str = "production"  # production, demo, hybrid
    context: Optional[Dict[str, Any]] = None
    temperature: float = 0.1
    max_tokens: int = 2048

class SystemStatus(BaseModel):
    status: str
    vllm_server: Dict[str, Any]
    backend_info: Dict[str, Any]
    timestamp: str
    production_mode: bool

class CodeGenerationRequest(BaseModel):
    prompt: str
    language: str = "python"
    complexity: str = "standard"
    include_tests: bool = False
    temperature: float = 0.1
    max_tokens: int = 2048

class AnalysisRequest(BaseModel):
    code: str
    analysis_type: str = "general"
    include_suggestions: bool = True

# FastAPI App
app = FastAPI(
    title="xCodeAgent Production Backend",
    description="Production backend with real DeepSeek-R1-0528 integration",
    version="2.0.0",
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

# Enhanced vLLM Client for Production
class ProductionVLLMClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.session: Optional[aiohttp.ClientSession] = None
        self.model_name = "deepseek-ai/DeepSeek-R1-0528"
        self.connection_retries = 3
        self.timeout = 60  # Increased timeout for large model
        
    async def get_session(self):
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self.session
        
    async def check_health(self) -> Dict[str, Any]:
        """Check vLLM server health with retries"""
        for attempt in range(self.connection_retries):
            try:
                session = await self.get_session()
                async with session.get(f"{self.base_url}/health") as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            "status": "healthy",
                            "url": self.base_url,
                            "model": self.model_name,
                            "response_time": response.headers.get("X-Response-Time", "unknown"),
                            "attempt": attempt + 1
                        }
                    else:
                        error_text = await response.text()
                        return {
                            "status": "unhealthy",
                            "url": self.base_url,
                            "error": f"HTTP {response.status}: {error_text}",
                            "attempt": attempt + 1
                        }
            except Exception as e:
                logger.error(f"Health check failed: {e}")
                if attempt == self.connection_retries - 1:  # Last attempt
                    return {
                        "status": "unreachable",
                        "url": self.base_url,
                        "error": "An internal error occurred while checking health.",
                        "attempts": self.connection_retries
                    }
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
        
    async def get_models(self) -> Dict[str, Any]:
        """Get available models"""
        try:
            session = await self.get_session()
            async with session.get(f"{self.base_url}/v1/models") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {"error": f"HTTP {response.status}"}
        except Exception as e:
            return {"error": str(e)}
    
    async def generate_completion(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate completion with production settings"""
        try:
            session = await self.get_session()
            
            # Production payload with optimized settings
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "max_tokens": kwargs.get("max_tokens", 2048),
                "temperature": kwargs.get("temperature", 0.1),
                "top_p": kwargs.get("top_p", 0.9),
                "frequency_penalty": kwargs.get("frequency_penalty", 0.0),
                "presence_penalty": kwargs.get("presence_penalty", 0.0),
                "stream": False,
                "stop": kwargs.get("stop", None)
            }
            
            start_time = time.time()
            
            async with session.post(
                f"{self.base_url}/v1/completions",
                json=payload
            ) as response:
                
                response_time = time.time() - start_time
                
                if response.status == 200:
                    data = await response.json()
                    
                    # Extract response text
                    response_text = ""
                    if "choices" in data and len(data["choices"]) > 0:
                        response_text = data["choices"][0].get("text", "")
                    
                    return {
                        "success": True,
                        "response": response_text,
                        "model": data.get("model", self.model_name),
                        "usage": data.get("usage", {}),
                        "response_time": response_time,
                        "finish_reason": data.get("choices", [{}])[0].get("finish_reason", "unknown")
                    }
                else:
                    error_text = await response.text()
                    return {
                        "success": False,
                        "error": f"vLLM server error: {response.status} - {error_text}",
                        "response_time": response_time
                    }
                    
        except asyncio.TimeoutError:
            return {
                "success": False,
                "error": "Request timeout - model may be loading or overloaded"
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
vllm_client = ProductionVLLMClient(VLLM_SERVER_URL)

# Session management with persistence
sessions = {}
performance_metrics = {
    "requests_total": 0,
    "requests_successful": 0,
    "requests_failed": 0,
    "average_response_time": 0,
    "model_status": "unknown"
}

# Startup/Shutdown events
@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Starting xCodeAgent Production Backend")
    logger.info(f"📡 vLLM Server URL: {VLLM_SERVER_URL}")
    logger.info(f"🌐 Backend running on {BACKEND_HOST}:{BACKEND_PORT}")
    logger.info(f"🏭 Production Mode: {PRODUCTION_MODE}")
    
    # Initial health check
    health = await vllm_client.check_health()
    logger.info(f"🔍 vLLM Server Status: {health.get('status', 'unknown')}")

@app.on_event("shutdown")
async def shutdown_event():
    await vllm_client.close()
    logger.info("🛑 Backend shutdown complete")

# Serve frontend files
app.mount("/static", StaticFiles(directory="frontend-v2"), name="static")

@app.get("/config.js")
async def serve_config():
    """Serve the frontend configuration file"""
    try:
        with open("frontend-v2/config.js", "r") as f:
            content = f.read()
            return Response(
                content=content,
                media_type="application/javascript"
            )
    except FileNotFoundError:
        return Response(
            content="console.error('Config file not found');",
            media_type="application/javascript",
            status_code=404
        )

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
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "production_mode": PRODUCTION_MODE,
        "version": "2.0.0"
    }

# Enhanced API v3 Endpoints
@app.get("/api/v3/status")
async def get_system_status():
    """Get comprehensive system status"""
    try:
        # Check vLLM server
        vllm_status = await vllm_client.check_health()
        
        # Get models info
        models_info = await vllm_client.get_models()
        
        # Get system info
        system_info = {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent,
            "uptime": time.time() - psutil.boot_time(),
            "load_average": os.getloadavg() if hasattr(os, 'getloadavg') else [0, 0, 0]
        }
        
        # Update performance metrics
        performance_metrics["model_status"] = vllm_status.get("status", "unknown")
        
        return {
            "success": True,
            "status": "operational" if vllm_status.get("status") == "healthy" else "degraded",
            "vllm_server": vllm_status,
            "models": models_info,
            "backend_info": {
                "version": "2.0.0",
                "host": BACKEND_HOST,
                "port": BACKEND_PORT,
                "production_mode": PRODUCTION_MODE,
                "system": system_info
            },
            "performance": performance_metrics,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        return {
            "success": False,
            "error": "An internal error occurred while retrieving system status.",
            "timestamp": datetime.now().isoformat()
        }

@app.post("/api/v3/chat")
async def chat_endpoint(request: ChatRequest):
    """Enhanced chat endpoint with production DeepSeek-R1-0528"""
    start_time = time.time()
    performance_metrics["requests_total"] += 1
    
    try:
        session_id = str(uuid.uuid4())
        
        # Store session
        sessions[session_id] = {
            "created_at": datetime.now().isoformat(),
            "messages": [],
            "execution_mode": request.execution_mode
        }
        
        # Add user message to session
        user_message = {
            "role": "user",
            "content": request.message,
            "timestamp": datetime.now().isoformat()
        }
        sessions[session_id]["messages"].append(user_message)
        
        # Generate AI response based on execution mode
        if request.execution_mode == "demo":
            # Demo mode - return mock response
            ai_response = f"""Demo Response to: "{request.message}"

This is a demonstration of the xCodeAgent system. In production mode, this connects to the real DeepSeek-R1-0528 model via vLLM server.

**Available Modes:**
- `production`: Real DeepSeek-R1-0528 model
- `demo`: Mock responses (current)
- `hybrid`: Fallback to demo if production fails

To use production mode, ensure the vLLM server is running with DeepSeek-R1-0528."""
            
        elif request.execution_mode == "production" or request.execution_mode == "hybrid":
            # Production mode - use real DeepSeek-R1-0528
            logger.info(f"Generating response with DeepSeek-R1-0528 for: {request.message[:100]}...")
            
            # Create enhanced prompt for better responses
            enhanced_prompt = f"""You are an expert AI coding assistant powered by DeepSeek-R1-0528. Please provide a helpful, accurate, and detailed response to the following request:

{request.message}

Please ensure your response is:
- Technically accurate and up-to-date
- Well-structured and easy to understand
- Includes code examples when relevant
- Provides explanations for complex concepts
- Follows best practices and conventions

Response:"""

            vllm_result = await vllm_client.generate_completion(
                prompt=enhanced_prompt,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                top_p=0.9
            )
            
            if vllm_result["success"]:
                ai_response = vllm_result["response"].strip()
                performance_metrics["requests_successful"] += 1
                
                # Add metadata about the generation
                ai_response += f"\n\n---\n*Generated by DeepSeek-R1-0528 via vLLM (Response time: {vllm_result.get('response_time', 0):.2f}s)*"
                
            else:
                # Fallback handling
                if request.execution_mode == "hybrid":
                    ai_response = f"""**Hybrid Mode Fallback Response**

I apologize, but the DeepSeek-R1-0528 model is currently unavailable. Here's a fallback response to your query: "{request.message}"

**Error Details:** {vllm_result.get('error', 'Unknown error')}

**Suggested Actions:**
1. Check if the vLLM server is running
2. Verify the model is loaded correctly
3. Try again in a few moments
4. Use demo mode for testing

For immediate assistance, please try rephrasing your question or use demo mode."""
                else:
                    # Pure production mode - return error
                    performance_metrics["requests_failed"] += 1
                    return {
                        "success": False,
                        "error": f"Production model unavailable: {vllm_result.get('error', 'Unknown error')}",
                        "session_id": session_id,
                        "execution_mode": request.execution_mode,
                        "timestamp": datetime.now().isoformat()
                    }
        else:
            # Unknown execution mode
            ai_response = f"Unknown execution mode: {request.execution_mode}. Available modes: production, demo, hybrid"
        
        # Add AI response to session
        ai_message = {
            "role": "assistant",
            "content": ai_response,
            "timestamp": datetime.now().isoformat(),
            "execution_mode": request.execution_mode
        }
        sessions[session_id]["messages"].append(ai_message)
        
        # Update performance metrics
        response_time = time.time() - start_time
        performance_metrics["average_response_time"] = (
            (performance_metrics["average_response_time"] * (performance_metrics["requests_total"] - 1) + response_time) /
            performance_metrics["requests_total"]
        )
        
        return {
            "success": True,
            "session_id": session_id,
            "execution_mode": request.execution_mode,
            "data": {
                "response": ai_response,
                "message_count": len(sessions[session_id]["messages"]),
                "response_time": response_time
            },
            "metadata": {
                "context": request.context,
                "timestamp": datetime.now().isoformat(),
                "model": "deepseek-ai/DeepSeek-R1-0528" if request.execution_mode == "production" else "demo"
            }
        }
        
    except Exception as e:
        performance_metrics["requests_failed"] += 1
        logger.error(f"Chat endpoint failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.post("/api/v3/generate-code")
async def generate_code(request: CodeGenerationRequest):
    """Generate code using DeepSeek-R1-0528"""
    try:
        # Create specialized code generation prompt
        code_prompt = f"""You are an expert software engineer. Generate high-quality {request.language} code for the following request:

**Request:** {request.prompt}

**Requirements:**
- Language: {request.language}
- Complexity: {request.complexity}
- Include tests: {request.include_tests}
- Follow best practices and conventions
- Include proper documentation/comments
- Ensure code is production-ready

**Response Format:**
Please provide:
1. The main code implementation
2. Usage examples
3. {"Unit tests" if request.include_tests else "Brief explanation"}

Code:"""

        # Generate code using vLLM
        result = await vllm_client.generate_completion(
            prompt=code_prompt,
            max_tokens=request.max_tokens,
            temperature=request.temperature
        )
        
        if result["success"]:
            return {
                "success": True,
                "data": {
                    "code": result["response"],
                    "language": request.language,
                    "complexity": request.complexity,
                    "include_tests": request.include_tests,
                    "usage": result.get("usage", {}),
                    "response_time": result.get("response_time", 0)
                },
                "metadata": {
                    "model": "deepseek-ai/DeepSeek-R1-0528",
                    "timestamp": datetime.now().isoformat()
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

@app.post("/api/v3/analyze-code")
async def analyze_code(request: AnalysisRequest):
    """Analyze code using DeepSeek-R1-0528"""
    try:
        analysis_prompt = f"""You are an expert code reviewer. Please analyze the following code:

```
{request.code}
```

**Analysis Type:** {request.analysis_type}
**Include Suggestions:** {request.include_suggestions}

Please provide a comprehensive analysis including:
1. Code quality assessment
2. Performance considerations
3. Security review
4. Best practices compliance
5. {"Improvement suggestions" if request.include_suggestions else "Summary"}

Analysis:"""

        result = await vllm_client.generate_completion(
            prompt=analysis_prompt,
            max_tokens=2048,
            temperature=0.1
        )
        
        if result["success"]:
            return {
                "success": True,
                "data": {
                    "analysis": result["response"],
                    "analysis_type": request.analysis_type,
                    "include_suggestions": request.include_suggestions,
                    "usage": result.get("usage", {}),
                    "response_time": result.get("response_time", 0)
                },
                "metadata": {
                    "model": "deepseek-ai/DeepSeek-R1-0528",
                    "timestamp": datetime.now().isoformat()
                }
            }
        else:
            return {
                "success": False,
                "error": result["error"]
            }
            
    except Exception as e:
        logger.error(f"Code analysis failed: {e}")
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

@app.get("/api/v3/performance")
async def get_performance_metrics():
    """Get performance metrics"""
    return {
        "success": True,
        "metrics": performance_metrics,
        "timestamp": datetime.now().isoformat()
    }

@app.websocket("/ws/{connection_id}")
async def websocket_endpoint(websocket: WebSocket, connection_id: str):
    """WebSocket endpoint for real-time communication"""
    await websocket.accept()
    logger.info(f"WebSocket connection established: {connection_id}")
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Echo back with timestamp and status
            response = {
                "type": "response",
                "data": message,
                "timestamp": datetime.now().isoformat(),
                "connection_id": connection_id,
                "server_status": "production" if PRODUCTION_MODE else "development"
            }
            
            await websocket.send_text(json.dumps(response))
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {connection_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")

if __name__ == "__main__":
    logger.info("🚀 Starting xCodeAgent Production Backend")
    uvicorn.run(
        app,
        host=BACKEND_HOST,
        port=BACKEND_PORT,
        log_level="info",
        access_log=True
    )