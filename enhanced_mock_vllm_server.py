#!/usr/bin/env python3
"""
Enhanced Mock vLLM Server for Testing
Simulates DeepSeek R1 responses without requiring actual model
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Request Models
class CompletionRequest(BaseModel):
    model: str = "deepseek-ai/DeepSeek-R1-0528"
    prompt: str
    max_tokens: int = 1024
    temperature: float = 0.1
    stream: bool = False

# FastAPI App
app = FastAPI(
    title="Mock vLLM Server",
    description="Enhanced mock server simulating vLLM API for testing",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Enhanced mock responses for different types of prompts
MOCK_RESPONSES = {
    "python_code": """def fibonacci(n):
    \"\"\"Generate Fibonacci sequence up to n terms\"\"\"
    if n <= 0:
        return []
    elif n == 1:
        return [0]
    elif n == 2:
        return [0, 1]
    
    fib = [0, 1]
    for i in range(2, n):
        fib.append(fib[i-1] + fib[i-2])
    return fib

# Example usage
if __name__ == "__main__":
    result = fibonacci(10)
    print(f"First 10 Fibonacci numbers: {result}")""",
    
    "javascript_code": """function fibonacci(n) {
    /**
     * Generate Fibonacci sequence up to n terms
     * @param {number} n - Number of terms to generate
     * @returns {number[]} Array of Fibonacci numbers
     */
    if (n <= 0) return [];
    if (n === 1) return [0];
    if (n === 2) return [0, 1];
    
    const fib = [0, 1];
    for (let i = 2; i < n; i++) {
        fib.push(fib[i-1] + fib[i-2]);
    }
    return fib;
}

// Example usage
console.log('First 10 Fibonacci numbers:', fibonacci(10));""",
    
    "explanation": """This code implements the Fibonacci sequence generator. Here's how it works:

1. **Input validation**: Checks if n is valid (handles edge cases)
2. **Base cases**: Handles n=0, n=1, and n=2 specially
3. **Iterative approach**: Uses a loop to build the sequence efficiently
4. **Time complexity**: O(n) - linear time, optimal for this approach
5. **Space complexity**: O(n) - stores all numbers in the sequence

The Fibonacci sequence starts with 0, 1 and each subsequent number is the sum of the two preceding ones: 0, 1, 1, 2, 3, 5, 8, 13, 21, 34, ...""",
    
    "analysis": """**Code Analysis Report:**

**Strengths:**
✅ Clear function documentation with docstring
✅ Proper input validation for edge cases
✅ Efficient iterative approach (better than recursive)
✅ Good variable naming conventions
✅ Readable and maintainable code structure

**Potential Improvements:**
🔧 Add type hints for better code clarity:
   `def fibonacci(n: int) -> List[int]:`
🔧 Consider using generators for memory efficiency with large sequences
🔧 Add comprehensive error handling for invalid inputs
🔧 Include unit tests for better reliability

**Performance Analysis:**
⚡ Time Complexity: O(n) - optimal for this approach
⚡ Space Complexity: O(n) - could be optimized to O(1) if only the nth value is needed
⚡ Memory usage scales linearly with input size

**Security Considerations:**
🔒 Input validation prevents negative numbers
🔒 No external dependencies or security risks
🔒 Safe for production use with proper input sanitization""",
    
    "chat_response": """Hello! I'm your AI coding assistant powered by DeepSeek R1. I can help you with:

🔧 **Code Generation**: Write functions, classes, and complete applications
📊 **Code Analysis**: Review code quality, performance, and best practices  
🐛 **Debugging**: Identify and fix issues in your code
📚 **Explanations**: Explain algorithms, concepts, and code functionality
🧪 **Testing**: Generate unit tests and testing strategies
📖 **Documentation**: Create clear documentation and comments

What would you like me to help you with today? Please provide specific details about your coding task or question.""",
    
    "error_help": """I can help you debug that error! Here's a systematic approach:

1. **Error Analysis**: Let me examine the error message and stack trace
2. **Root Cause**: Identify what's causing the issue
3. **Solution**: Provide a fix with explanation
4. **Prevention**: Suggest how to avoid similar issues

Please share:
- The complete error message
- The relevant code snippet
- What you were trying to accomplish
- Your environment details (Python version, OS, etc.)

I'll provide a detailed solution with code examples!""",
    
    "default": """I understand your request. As an AI coding assistant, I'm here to help you with various programming tasks.

**How I can assist you:**
- Generate code in multiple programming languages
- Analyze and optimize existing code
- Debug errors and provide solutions
- Explain programming concepts and algorithms
- Suggest best practices and design patterns
- Create documentation and tests

Please provide more specific details about what you'd like me to help you with, and I'll give you a comprehensive response tailored to your needs."""
}

def generate_mock_response(prompt: str) -> str:
    """Generate appropriate mock response based on prompt content"""
    prompt_lower = prompt.lower()
    
    # Check for specific programming languages
    if "python" in prompt_lower and any(word in prompt_lower for word in ["code", "function", "class", "implement"]):
        return MOCK_RESPONSES["python_code"]
    elif "javascript" in prompt_lower and any(word in prompt_lower for word in ["code", "function", "class", "implement"]):
        return MOCK_RESPONSES["javascript_code"]
    
    # Check for general code requests
    elif any(word in prompt_lower for word in ["code", "function", "class", "implement", "write", "create"]):
        return MOCK_RESPONSES["python_code"]  # Default to Python
    
    # Check for explanations
    elif any(word in prompt_lower for word in ["explain", "how", "what", "why", "describe"]):
        return MOCK_RESPONSES["explanation"]
    
    # Check for analysis requests
    elif any(word in prompt_lower for word in ["analyze", "review", "check", "improve", "optimize"]):
        return MOCK_RESPONSES["analysis"]
    
    # Check for error/debugging help
    elif any(word in prompt_lower for word in ["error", "bug", "debug", "fix", "problem", "issue"]):
        return MOCK_RESPONSES["error_help"]
    
    # Check for greetings or general chat
    elif any(word in prompt_lower for word in ["hello", "hi", "help", "assist", "can you"]):
        return MOCK_RESPONSES["chat_response"]
    
    else:
        return MOCK_RESPONSES["default"]

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "model": "deepseek-ai/DeepSeek-R1-0528",
        "server": "mock-vllm",
        "timestamp": datetime.now().isoformat(),
        "uptime": time.time()
    }

@app.post("/v1/completions")
async def create_completion(request: CompletionRequest):
    """Mock completion endpoint with enhanced responses"""
    try:
        # Simulate realistic processing time
        processing_time = min(0.5 + len(request.prompt) / 1000, 3.0)
        await asyncio.sleep(processing_time)
        
        # Generate contextual mock response
        response_text = generate_mock_response(request.prompt)
        
        # Add some variation based on temperature
        if request.temperature > 0.5:
            response_text += "\n\n*Note: This response includes some creative variations due to higher temperature setting.*"
        
        completion_id = f"cmpl-{int(time.time())}-{hash(request.prompt) % 10000}"
        
        return {
            "id": completion_id,
            "object": "text_completion",
            "created": int(time.time()),
            "model": request.model,
            "choices": [
                {
                    "text": response_text,
                    "index": 0,
                    "logprobs": None,
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": len(request.prompt.split()),
                "completion_tokens": len(response_text.split()),
                "total_tokens": len(request.prompt.split()) + len(response_text.split())
            }
        }
        
    except Exception as e:
        logger.error(f"Completion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/v1/models")
async def list_models():
    """List available models"""
    return {
        "object": "list",
        "data": [
            {
                "id": "deepseek-ai/DeepSeek-R1-0528",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "deepseek-ai",
                "permission": [],
                "root": "deepseek-ai/DeepSeek-R1-0528",
                "parent": None
            }
        ]
    }

@app.get("/")
async def root():
    """Root endpoint with server info"""
    return {
        "message": "Mock vLLM Server is running",
        "version": "1.0.0",
        "model": "deepseek-ai/DeepSeek-R1-0528",
        "endpoints": {
            "health": "/health",
            "completions": "/v1/completions",
            "models": "/v1/models"
        },
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    logger.info("Starting Enhanced Mock vLLM Server on port 8000")
    logger.info("Available endpoints:")
    logger.info("  - Health: http://localhost:8000/health")
    logger.info("  - Completions: http://localhost:8000/v1/completions")
    logger.info("  - Models: http://localhost:8000/v1/models")
    uvicorn.run(app, host="0.0.0.0", port=8000)