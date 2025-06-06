#!/usr/bin/env python3
"""
Production vLLM Server for DeepSeek R1 0528
Real-time data processing with optimized configuration
"""

import asyncio
import logging
import os
import sys
import time
from typing import Dict, Any, Optional
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import psutil

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
class VLLMConfig:
    def __init__(self):
        self.model_name = "deepseek-ai/DeepSeek-R1-0528"
        self.host = "0.0.0.0"
        self.port = 8000
        self.max_model_len = 32768
        self.trust_remote_code = True
        self.device = self.detect_device()
        self.tensor_parallel_size = self.get_optimal_tp_size()
        self.gpu_memory_utilization = 0.85
        self.max_num_seqs = 256
        self.max_num_batched_tokens = 8192
        
    def detect_device(self) -> str:
        """Detect optimal device configuration"""
        try:
            import torch
            if torch.cuda.is_available():
                gpu_count = torch.cuda.device_count()
                total_memory = sum(torch.cuda.get_device_properties(i).total_memory 
                                 for i in range(gpu_count)) / (1024**3)  # GB
                
                logger.info(f"Detected {gpu_count} GPU(s) with {total_memory:.1f}GB total memory")
                
                if total_memory >= 24:  # Sufficient for DeepSeek R1
                    return "cuda"
                else:
                    logger.warning(f"GPU memory ({total_memory:.1f}GB) may be insufficient for DeepSeek R1")
                    return "cuda"
            else:
                logger.info("No CUDA available, using CPU")
                return "cpu"
        except ImportError:
            logger.info("PyTorch not available, using CPU")
            return "cpu"
    
    def get_optimal_tp_size(self) -> int:
        """Get optimal tensor parallel size"""
        try:
            import torch
            if torch.cuda.is_available():
                gpu_count = torch.cuda.device_count()
                # Use all available GPUs for tensor parallelism
                return min(gpu_count, 8)  # Max 8 for most efficient parallelism
            return 1
        except ImportError:
            return 1

# Request/Response Models
class GenerationRequest(BaseModel):
    prompt: str
    max_tokens: int = 2048
    temperature: float = 0.1
    top_p: float = 0.9
    stream: bool = False

class GenerationResponse(BaseModel):
    text: str
    usage: Dict[str, int]
    model: str
    created: int

class HealthResponse(BaseModel):
    status: str
    model: str
    device: str
    memory_usage: Dict[str, Any]
    uptime: float

# Global state
config = VLLMConfig()
server_start_time = time.time()
vllm_engine = None

# FastAPI app
app = FastAPI(
    title="DeepSeek R1 vLLM Server",
    description="Production vLLM server for DeepSeek R1 0528",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def initialize_vllm_engine():
    """Initialize vLLM engine with optimal configuration"""
    global vllm_engine
    
    try:
        from vllm import AsyncLLMEngine
        from vllm.engine.arg_utils import AsyncEngineArgs
        
        logger.info(f"Initializing vLLM engine for {config.model_name}")
        logger.info(f"Device: {config.device}, TP Size: {config.tensor_parallel_size}")
        
        # Configure engine arguments
        engine_args = AsyncEngineArgs(
            model=config.model_name,
            device=config.device,
            tensor_parallel_size=config.tensor_parallel_size,
            max_model_len=config.max_model_len,
            trust_remote_code=config.trust_remote_code,
            gpu_memory_utilization=config.gpu_memory_utilization,
            max_num_seqs=config.max_num_seqs,
            max_num_batched_tokens=config.max_num_batched_tokens,
            enforce_eager=True,  # For better compatibility
            disable_log_stats=False,
        )
        
        # Add CPU-specific optimizations
        if config.device == "cpu":
            # For CPU mode, don't set device parameter, let vLLM handle it
            engine_args.gpu_memory_utilization = 0.0
            engine_args.max_num_seqs = 64  # Reduce for CPU
            engine_args.max_num_batched_tokens = 2048
            # Remove tensor_parallel_size for CPU
            engine_args.tensor_parallel_size = 1
            logger.info("Applied CPU optimizations")
        
        # Initialize engine
        vllm_engine = AsyncLLMEngine.from_engine_args(engine_args)
        logger.info("vLLM engine initialized successfully")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize vLLM engine: {e}")
        return False

def get_memory_usage() -> Dict[str, Any]:
    """Get current memory usage statistics"""
    memory_info = {
        "system": {
            "total": psutil.virtual_memory().total / (1024**3),
            "available": psutil.virtual_memory().available / (1024**3),
            "percent": psutil.virtual_memory().percent
        }
    }
    
    try:
        import torch
        if torch.cuda.is_available():
            gpu_memory = {}
            for i in range(torch.cuda.device_count()):
                allocated = torch.cuda.memory_allocated(i) / (1024**3)
                reserved = torch.cuda.memory_reserved(i) / (1024**3)
                total = torch.cuda.get_device_properties(i).total_memory / (1024**3)
                
                gpu_memory[f"gpu_{i}"] = {
                    "allocated": allocated,
                    "reserved": reserved,
                    "total": total,
                    "utilization": (allocated / total) * 100
                }
            memory_info["gpu"] = gpu_memory
    except ImportError:
        pass
    
    return memory_info

@app.on_event("startup")
async def startup_event():
    """Initialize vLLM engine on startup"""
    logger.info("Starting DeepSeek R1 vLLM server...")
    success = await initialize_vllm_engine()
    if not success:
        logger.error("Failed to initialize vLLM engine")
        sys.exit(1)

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy" if vllm_engine else "initializing",
        model=config.model_name,
        device=config.device,
        memory_usage=get_memory_usage(),
        uptime=time.time() - server_start_time
    )

@app.post("/v1/completions", response_model=GenerationResponse)
async def generate_completion(request: GenerationRequest):
    """Generate text completion using DeepSeek R1"""
    if not vllm_engine:
        raise HTTPException(status_code=503, detail="vLLM engine not initialized")
    
    try:
        from vllm import SamplingParams
        
        # Configure sampling parameters
        sampling_params = SamplingParams(
            temperature=request.temperature,
            top_p=request.top_p,
            max_tokens=request.max_tokens,
            stop=None
        )
        
        # Generate response
        start_time = time.time()
        results = await vllm_engine.generate(
            request.prompt,
            sampling_params,
            request_id=f"req_{int(time.time() * 1000)}"
        )
        
        if not results:
            raise HTTPException(status_code=500, detail="No results generated")
        
        result = results[0]
        generated_text = result.outputs[0].text
        
        # Calculate usage statistics
        prompt_tokens = len(result.prompt_token_ids)
        completion_tokens = len(result.outputs[0].token_ids)
        total_tokens = prompt_tokens + completion_tokens
        
        generation_time = time.time() - start_time
        logger.info(f"Generated {completion_tokens} tokens in {generation_time:.2f}s "
                   f"({completion_tokens/generation_time:.1f} tokens/s)")
        
        return GenerationResponse(
            text=generated_text,
            usage={
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens
            },
            model=config.model_name,
            created=int(time.time())
        )
        
    except Exception as e:
        logger.error(f"Generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")

@app.post("/v1/chat/completions")
async def chat_completion(request: dict):
    """OpenAI-compatible chat completion endpoint"""
    if not vllm_engine:
        raise HTTPException(status_code=503, detail="vLLM engine not initialized")
    
    try:
        # Extract messages and convert to prompt
        messages = request.get("messages", [])
        if not messages:
            raise HTTPException(status_code=400, detail="No messages provided")
        
        # Convert chat messages to prompt format
        prompt = ""
        for message in messages:
            role = message.get("role", "user")
            content = message.get("content", "")
            
            if role == "system":
                prompt += f"System: {content}\n"
            elif role == "user":
                prompt += f"User: {content}\n"
            elif role == "assistant":
                prompt += f"Assistant: {content}\n"
        
        prompt += "Assistant: "
        
        # Create generation request
        gen_request = GenerationRequest(
            prompt=prompt,
            max_tokens=request.get("max_tokens", 2048),
            temperature=request.get("temperature", 0.1),
            top_p=request.get("top_p", 0.9),
            stream=request.get("stream", False)
        )
        
        # Generate response
        response = await generate_completion(gen_request)
        
        # Format as OpenAI-compatible response
        return {
            "id": f"chatcmpl-{int(time.time() * 1000)}",
            "object": "chat.completion",
            "created": response.created,
            "model": response.model,
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response.text
                },
                "finish_reason": "stop"
            }],
            "usage": response.usage
        }
        
    except Exception as e:
        logger.error(f"Chat completion failed: {e}")
        raise HTTPException(status_code=500, detail=f"Chat completion failed: {str(e)}")

@app.get("/v1/models")
async def list_models():
    """List available models"""
    return {
        "object": "list",
        "data": [{
            "id": config.model_name,
            "object": "model",
            "created": int(server_start_time),
            "owned_by": "deepseek"
        }]
    }

@app.get("/metrics")
async def get_metrics():
    """Get server metrics"""
    return {
        "model": config.model_name,
        "device": config.device,
        "tensor_parallel_size": config.tensor_parallel_size,
        "memory_usage": get_memory_usage(),
        "uptime": time.time() - server_start_time,
        "status": "healthy" if vllm_engine else "initializing"
    }

if __name__ == "__main__":
    logger.info(f"Starting DeepSeek R1 vLLM server on {config.host}:{config.port}")
    logger.info(f"Model: {config.model_name}")
    logger.info(f"Device: {config.device}")
    logger.info(f"Max model length: {config.max_model_len}")
    
    uvicorn.run(
        app,
        host=config.host,
        port=config.port,
        log_level="info",
        access_log=True
    )