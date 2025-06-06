#!/usr/bin/env python3
"""
Simple CodeAgent03 + DeepSeek R1 Integration Server
A lightweight implementation that gets the core functionality running quickly.
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional

import aiohttp
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

# Add the repositories to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "repositories" / "CodeAgent03"))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SimpleDeepSeekProvider:
    """Simple DeepSeek R1 provider using Hugging Face Transformers"""
    
    def __init__(self):
        self.model_name = "deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B"
        self.model = None
        self.tokenizer = None
        self.device = "cpu"  # Force CPU for this environment
        
    async def initialize(self):
        """Initialize the model"""
        try:
            from transformers import AutoTokenizer, AutoModelForCausalLM
            
            logger.info(f"Loading model: {self.model_name}")
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                torch_dtype="auto",
                device_map="cpu",
                trust_remote_code=True
            )
            logger.info("Model loaded successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return False
    
    async def generate_response(self, prompt: str, max_length: int = 1024) -> str:
        """Generate response using the model"""
        if not self.model or not self.tokenizer:
            return "Model not initialized. Please wait for initialization to complete."
        
        try:
            # Add thinking prompt to encourage reasoning
            enhanced_prompt = f"<think>\nLet me think about this step by step.\n</think>\n\n{prompt}"
            
            inputs = self.tokenizer.encode(enhanced_prompt, return_tensors="pt")
            
            with torch.no_grad():
                outputs = self.model.generate(
                    inputs,
                    max_length=min(max_length, 2048),  # Limit for CPU
                    temperature=0.6,
                    top_p=0.95,
                    do_sample=True,
                    pad_token_id=self.tokenizer.eos_token_id
                )
            
            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            # Remove the original prompt from response
            response = response[len(enhanced_prompt):].strip()
            
            return response
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            return f"Error generating response: {str(e)}"

class CodeAgentIntegration:
    """Integration with CodeAgent03 functionality"""
    
    def __init__(self, deepseek_provider: SimpleDeepSeekProvider):
        self.deepseek = deepseek_provider
        self.codeagent_path = Path(__file__).parent.parent / "repositories" / "CodeAgent03"
        
    async def analyze_code(self, code: str, task_type: str = "general") -> Dict[str, Any]:
        """Analyze code using DeepSeek R1"""
        prompt = f"""
Please analyze the following code and provide insights:

Code:
```
{code}
```

Task: {task_type}

Please provide:
1. Code quality assessment
2. Potential improvements
3. Security considerations
4. Performance suggestions
5. Best practices recommendations
"""
        
        response = await self.deepseek.generate_response(prompt)
        
        return {
            "analysis": response,
            "task_type": task_type,
            "code_length": len(code),
            "timestamp": asyncio.get_event_loop().time()
        }
    
    async def generate_code(self, description: str, language: str = "python") -> Dict[str, Any]:
        """Generate code based on description"""
        prompt = f"""
Generate {language} code for the following requirement:

Requirement: {description}

Please provide:
1. Clean, well-commented code
2. Error handling where appropriate
3. Best practices implementation
4. Brief explanation of the approach

Code:
"""
        
        response = await self.deepseek.generate_response(prompt)
        
        return {
            "generated_code": response,
            "language": language,
            "description": description,
            "timestamp": asyncio.get_event_loop().time()
        }
    
    async def review_code(self, code: str) -> Dict[str, Any]:
        """Perform code review"""
        prompt = f"""
Please perform a comprehensive code review for the following code:

```
{code}
```

Provide feedback on:
1. Code structure and organization
2. Naming conventions
3. Error handling
4. Performance considerations
5. Security issues
6. Maintainability
7. Testing suggestions

Format your response as a structured review with specific recommendations.
"""
        
        response = await self.deepseek.generate_response(prompt)
        
        return {
            "review": response,
            "code_length": len(code),
            "timestamp": asyncio.get_event_loop().time()
        }

# Initialize providers
deepseek_provider = SimpleDeepSeekProvider()
code_agent = CodeAgentIntegration(deepseek_provider)

# FastAPI app
app = FastAPI(
    title="Enhanced CodeAgent03 + DeepSeek R1 Integration",
    description="Local AI coding assistant with DeepSeek R1 reasoning capabilities",
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

# WebSocket connections
active_connections = []

@app.on_event("startup")
async def startup_event():
    """Initialize the application"""
    logger.info("Starting Enhanced CodeAgent Integration...")
    
    # Try to install torch if not available
    try:
        import torch
    except ImportError:
        logger.info("Installing PyTorch...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "torch", "--index-url", "https://download.pytorch.org/whl/cpu"])
        import torch
    
    # Try to install transformers if not available
    try:
        import transformers
    except ImportError:
        logger.info("Installing transformers...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "transformers"])
    
    # Initialize DeepSeek provider
    success = await deepseek_provider.initialize()
    if success:
        logger.info("DeepSeek provider initialized successfully")
    else:
        logger.warning("DeepSeek provider initialization failed - using fallback mode")

@app.get("/")
async def root():
    """Serve the main interface"""
    return HTMLResponse(content="""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Enhanced CodeAgent03 + DeepSeek R1</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
            color: white;
            padding: 20px;
            text-align: center;
        }
        .header h1 {
            margin: 0;
            font-size: 2.5em;
        }
        .header p {
            margin: 10px 0 0 0;
            opacity: 0.9;
        }
        .main-content {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            padding: 20px;
        }
        .panel {
            background: #f8f9fa;
            border-radius: 8px;
            padding: 20px;
            border: 1px solid #e9ecef;
        }
        .panel h3 {
            margin-top: 0;
            color: #2c3e50;
            border-bottom: 2px solid #3498db;
            padding-bottom: 10px;
        }
        textarea {
            width: 100%;
            height: 200px;
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 10px;
            font-family: 'Courier New', monospace;
            resize: vertical;
        }
        button {
            background: linear-gradient(135deg, #3498db 0%, #2980b9 100%);
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 16px;
            margin: 10px 5px 0 0;
            transition: all 0.3s ease;
        }
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(52, 152, 219, 0.4);
        }
        button:disabled {
            background: #bdc3c7;
            cursor: not-allowed;
            transform: none;
            box-shadow: none;
        }
        .output {
            background: #2c3e50;
            color: #ecf0f1;
            padding: 15px;
            border-radius: 6px;
            font-family: 'Courier New', monospace;
            white-space: pre-wrap;
            max-height: 400px;
            overflow-y: auto;
            margin-top: 15px;
        }
        .status {
            background: #27ae60;
            color: white;
            padding: 10px;
            border-radius: 4px;
            margin-bottom: 20px;
            text-align: center;
        }
        .loading {
            display: none;
            text-align: center;
            padding: 20px;
        }
        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #3498db;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .full-width {
            grid-column: 1 / -1;
        }
        select {
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
            margin-bottom: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 Enhanced CodeAgent03 + DeepSeek R1</h1>
            <p>Local AI Coding Assistant with Advanced Reasoning Capabilities</p>
        </div>
        
        <div class="status" id="status">
            🟢 System Ready - DeepSeek R1 Model Loaded
        </div>
        
        <div class="main-content">
            <div class="panel">
                <h3>📝 Code Generation</h3>
                <textarea id="codeDescription" placeholder="Describe what code you want to generate...
Example: Create a Python function that calculates fibonacci numbers with memoization"></textarea>
                <select id="language">
                    <option value="python">Python</option>
                    <option value="javascript">JavaScript</option>
                    <option value="java">Java</option>
                    <option value="cpp">C++</option>
                    <option value="rust">Rust</option>
                    <option value="go">Go</option>
                </select>
                <button onclick="generateCode()">🚀 Generate Code</button>
                <div class="output" id="generatedCode"></div>
            </div>
            
            <div class="panel">
                <h3>🔍 Code Analysis</h3>
                <textarea id="codeToAnalyze" placeholder="Paste your code here for analysis..."></textarea>
                <select id="analysisType">
                    <option value="general">General Analysis</option>
                    <option value="performance">Performance Review</option>
                    <option value="security">Security Audit</option>
                    <option value="refactoring">Refactoring Suggestions</option>
                </select>
                <button onclick="analyzeCode()">🔬 Analyze Code</button>
                <div class="output" id="analysisResult"></div>
            </div>
            
            <div class="panel">
                <h3>📋 Code Review</h3>
                <textarea id="codeToReview" placeholder="Paste code for comprehensive review..."></textarea>
                <button onclick="reviewCode()">👀 Review Code</button>
                <div class="output" id="reviewResult"></div>
            </div>
            
            <div class="panel">
                <h3>💬 Chat with DeepSeek R1</h3>
                <textarea id="chatInput" placeholder="Ask any coding question or request help...
Example: How do I implement a binary search tree in Python?"></textarea>
                <button onclick="chatWithAI()">💭 Ask DeepSeek R1</button>
                <div class="output" id="chatOutput"></div>
            </div>
        </div>
        
        <div class="loading" id="loading">
            <div class="spinner"></div>
            <p>Processing with DeepSeek R1...</p>
        </div>
    </div>

    <script>
        function showLoading() {
            document.getElementById('loading').style.display = 'block';
        }
        
        function hideLoading() {
            document.getElementById('loading').style.display = 'none';
        }
        
        async function generateCode() {
            const description = document.getElementById('codeDescription').value;
            const language = document.getElementById('language').value;
            
            if (!description.trim()) {
                alert('Please enter a code description');
                return;
            }
            
            showLoading();
            try {
                const response = await fetch('/generate-code', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({description, language})
                });
                
                const result = await response.json();
                document.getElementById('generatedCode').textContent = result.generated_code;
            } catch (error) {
                document.getElementById('generatedCode').textContent = 'Error: ' + error.message;
            }
            hideLoading();
        }
        
        async function analyzeCode() {
            const code = document.getElementById('codeToAnalyze').value;
            const taskType = document.getElementById('analysisType').value;
            
            if (!code.trim()) {
                alert('Please enter code to analyze');
                return;
            }
            
            showLoading();
            try {
                const response = await fetch('/analyze-code', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({code, task_type: taskType})
                });
                
                const result = await response.json();
                document.getElementById('analysisResult').textContent = result.analysis;
            } catch (error) {
                document.getElementById('analysisResult').textContent = 'Error: ' + error.message;
            }
            hideLoading();
        }
        
        async function reviewCode() {
            const code = document.getElementById('codeToReview').value;
            
            if (!code.trim()) {
                alert('Please enter code to review');
                return;
            }
            
            showLoading();
            try {
                const response = await fetch('/review-code', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({code})
                });
                
                const result = await response.json();
                document.getElementById('reviewResult').textContent = result.review;
            } catch (error) {
                document.getElementById('reviewResult').textContent = 'Error: ' + error.message;
            }
            hideLoading();
        }
        
        async function chatWithAI() {
            const input = document.getElementById('chatInput').value;
            
            if (!input.trim()) {
                alert('Please enter a question');
                return;
            }
            
            showLoading();
            try {
                const response = await fetch('/chat', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({message: input})
                });
                
                const result = await response.json();
                document.getElementById('chatOutput').textContent = result.response;
            } catch (error) {
                document.getElementById('chatOutput').textContent = 'Error: ' + error.message;
            }
            hideLoading();
        }
        
        // Check system status
        async function checkStatus() {
            try {
                const response = await fetch('/health');
                const result = await response.json();
                const statusEl = document.getElementById('status');
                
                if (result.status === 'healthy') {
                    statusEl.innerHTML = '🟢 System Ready - DeepSeek R1 Model Loaded';
                    statusEl.style.background = '#27ae60';
                } else {
                    statusEl.innerHTML = '🟡 System Starting - Please wait...';
                    statusEl.style.background = '#f39c12';
                }
            } catch (error) {
                const statusEl = document.getElementById('status');
                statusEl.innerHTML = '🔴 System Error - Check console';
                statusEl.style.background = '#e74c3c';
            }
        }
        
        // Check status on load and periodically
        checkStatus();
        setInterval(checkStatus, 30000);
    </script>
</body>
</html>
    """)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    model_status = "loaded" if deepseek_provider.model else "loading"
    return {
        "status": "healthy" if model_status == "loaded" else "starting",
        "model_status": model_status,
        "model_name": deepseek_provider.model_name,
        "timestamp": asyncio.get_event_loop().time()
    }

@app.post("/generate-code")
async def generate_code_endpoint(request: Dict[str, Any]):
    """Generate code based on description"""
    try:
        description = request.get("description", "")
        language = request.get("language", "python")
        
        if not description:
            raise HTTPException(status_code=400, detail="Description is required")
        
        result = await code_agent.generate_code(description, language)
        return result
    except Exception as e:
        logger.error(f"Code generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze-code")
async def analyze_code_endpoint(request: Dict[str, Any]):
    """Analyze code"""
    try:
        code = request.get("code", "")
        task_type = request.get("task_type", "general")
        
        if not code:
            raise HTTPException(status_code=400, detail="Code is required")
        
        result = await code_agent.analyze_code(code, task_type)
        return result
    except Exception as e:
        logger.error(f"Code analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/review-code")
async def review_code_endpoint(request: Dict[str, Any]):
    """Review code"""
    try:
        code = request.get("code", "")
        
        if not code:
            raise HTTPException(status_code=400, detail="Code is required")
        
        result = await code_agent.review_code(code)
        return result
    except Exception as e:
        logger.error(f"Code review error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat")
async def chat_endpoint(request: Dict[str, Any]):
    """Chat with DeepSeek R1"""
    try:
        message = request.get("message", "")
        
        if not message:
            raise HTTPException(status_code=400, detail="Message is required")
        
        response = await deepseek_provider.generate_response(message)
        return {"response": response, "timestamp": asyncio.get_event_loop().time()}
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time communication"""
    await websocket.accept()
    active_connections.append(websocket)
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Process message based on type
            if message.get("type") == "chat":
                response = await deepseek_provider.generate_response(message.get("content", ""))
                await websocket.send_text(json.dumps({
                    "type": "response",
                    "content": response
                }))
    except WebSocketDisconnect:
        active_connections.remove(websocket)

if __name__ == "__main__":
    # Run the server
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=12000,
        log_level="info",
        access_log=True
    )