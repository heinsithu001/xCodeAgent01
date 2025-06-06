"""
Local DeepSeek R1 Provider
Handles communication with local vLLM server running DeepSeek R1 models.
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Optional, AsyncGenerator, Any
import aiohttp
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class GenerationConfig:
    """Configuration for text generation"""
    temperature: float = 0.6
    top_p: float = 0.95
    max_tokens: int = 4096
    stream: bool = False
    stop: Optional[List[str]] = None
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0

@dataclass
class ModelResponse:
    """Response from the model"""
    content: str
    usage: Dict[str, int]
    model: str
    finish_reason: str
    response_time: float

class LocalDeepSeekProvider:
    """
    Provider for local DeepSeek R1 model via vLLM server.
    Handles both streaming and non-streaming responses.
    """
    
    def __init__(self, 
                 base_url: str = "http://localhost:8000",
                 model_name: str = "deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B",
                 timeout: int = 300):
        self.base_url = base_url.rstrip('/')
        self.model_name = model_name
        self.timeout = timeout
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def health_check(self) -> bool:
        """Check if the vLLM server is healthy"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=10)
                )
            
            async with self.session.get(f"{self.base_url}/health") as response:
                return response.status == 200
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    async def get_model_info(self) -> Dict[str, Any]:
        """Get information about the loaded model"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            async with self.session.get(f"{self.base_url}/v1/models") as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    logger.error(f"Failed to get model info: {response.status}")
                    return {}
        except Exception as e:
            logger.error(f"Error getting model info: {e}")
            return {}
    
    async def generate_completion(self, 
                                prompt: str, 
                                config: Optional[GenerationConfig] = None) -> ModelResponse:
        """
        Generate a completion for the given prompt.
        
        Args:
            prompt: Input prompt
            config: Generation configuration
            
        Returns:
            ModelResponse with generated content
        """
        if config is None:
            config = GenerationConfig()
        
        start_time = time.time()
        
        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": config.temperature,
            "top_p": config.top_p,
            "max_tokens": config.max_tokens,
            "stream": config.stream,
            "frequency_penalty": config.frequency_penalty,
            "presence_penalty": config.presence_penalty
        }
        
        if config.stop:
            payload["stop"] = config.stop
        
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            async with self.session.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"API request failed with status {response.status}: {error_text}")
                
                data = await response.json()
                response_time = time.time() - start_time
                
                # Extract response data
                choice = data["choices"][0]
                content = choice["message"]["content"]
                finish_reason = choice["finish_reason"]
                usage = data.get("usage", {})
                
                return ModelResponse(
                    content=content,
                    usage=usage,
                    model=data["model"],
                    finish_reason=finish_reason,
                    response_time=response_time
                )
                
        except Exception as e:
            logger.error(f"Error generating completion: {e}")
            raise
    
    async def generate_streaming_completion(self, 
                                          prompt: str, 
                                          config: Optional[GenerationConfig] = None) -> AsyncGenerator[str, None]:
        """
        Generate a streaming completion for the given prompt.
        
        Args:
            prompt: Input prompt
            config: Generation configuration
            
        Yields:
            Chunks of generated text
        """
        if config is None:
            config = GenerationConfig(stream=True)
        else:
            config.stream = True
        
        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": config.temperature,
            "top_p": config.top_p,
            "max_tokens": config.max_tokens,
            "stream": True,
            "frequency_penalty": config.frequency_penalty,
            "presence_penalty": config.presence_penalty
        }
        
        if config.stop:
            payload["stop"] = config.stop
        
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            async with self.session.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"API request failed with status {response.status}: {error_text}")
                
                async for line in response.content:
                    line = line.decode('utf-8').strip()
                    if line.startswith('data: '):
                        data_str = line[6:]  # Remove 'data: ' prefix
                        
                        if data_str == '[DONE]':
                            break
                        
                        try:
                            data = json.loads(data_str)
                            choice = data["choices"][0]
                            
                            if "delta" in choice and "content" in choice["delta"]:
                                content = choice["delta"]["content"]
                                if content:
                                    yield content
                                    
                        except json.JSONDecodeError:
                            continue
                            
        except Exception as e:
            logger.error(f"Error generating streaming completion: {e}")
            raise
    
    async def generate_code(self, 
                          task_description: str, 
                          language: str = "python",
                          context: Optional[str] = None) -> ModelResponse:
        """
        Generate code based on task description.
        
        Args:
            task_description: Description of the coding task
            language: Programming language
            context: Additional context or existing code
            
        Returns:
            ModelResponse with generated code
        """
        # Construct a code-specific prompt
        prompt = f"<think>\nI need to generate {language} code for the following task: {task_description}\n"
        
        if context:
            prompt += f"\nExisting context:\n{context}\n"
        
        prompt += f"\nLet me think about this step by step and generate clean, efficient {language} code.\n</think>\n\n"
        prompt += f"Generate {language} code for: {task_description}"
        
        if language.lower() == "python":
            prompt += "\n\nPlease provide clean, well-documented Python code with appropriate error handling."
        elif language.lower() in ["javascript", "js"]:
            prompt += "\n\nPlease provide clean, modern JavaScript code with proper error handling."
        elif language.lower() in ["java"]:
            prompt += "\n\nPlease provide clean, well-structured Java code with proper exception handling."
        
        config = GenerationConfig(
            temperature=0.3,  # Lower temperature for more deterministic code
            max_tokens=2048
        )
        
        return await self.generate_completion(prompt, config)
    
    async def analyze_code(self, 
                         code: str, 
                         task_type: str = "review") -> ModelResponse:
        """
        Analyze code for various purposes.
        
        Args:
            code: Code to analyze
            task_type: Type of analysis (review, debug, optimize, explain)
            
        Returns:
            ModelResponse with analysis results
        """
        task_prompts = {
            "review": "Please review this code and provide feedback on code quality, best practices, and potential improvements:",
            "debug": "Please analyze this code for potential bugs, errors, or issues:",
            "optimize": "Please analyze this code and suggest optimizations for performance and efficiency:",
            "explain": "Please explain what this code does, how it works, and its key components:",
            "test": "Please generate comprehensive unit tests for this code:"
        }
        
        prompt = f"<think>\nI need to {task_type} the following code. Let me analyze it carefully.\n</think>\n\n"
        prompt += task_prompts.get(task_type, task_prompts["review"])
        prompt += f"\n\n```\n{code}\n```"
        
        config = GenerationConfig(
            temperature=0.4,
            max_tokens=2048
        )
        
        return await self.generate_completion(prompt, config)
    
    async def generate_documentation(self, 
                                   code: str, 
                                   doc_type: str = "docstring") -> ModelResponse:
        """
        Generate documentation for code.
        
        Args:
            code: Code to document
            doc_type: Type of documentation (docstring, readme, api)
            
        Returns:
            ModelResponse with generated documentation
        """
        doc_prompts = {
            "docstring": "Generate comprehensive docstrings for this code:",
            "readme": "Generate a README.md file for this code:",
            "api": "Generate API documentation for this code:",
            "comments": "Add inline comments to explain this code:"
        }
        
        prompt = f"<think>\nI need to generate {doc_type} documentation for the provided code.\n</think>\n\n"
        prompt += doc_prompts.get(doc_type, doc_prompts["docstring"])
        prompt += f"\n\n```\n{code}\n```"
        
        config = GenerationConfig(
            temperature=0.3,
            max_tokens=2048
        )
        
        return await self.generate_completion(prompt, config)

# Utility functions for easy usage
async def create_provider(base_url: str = "http://localhost:8000", 
                         model_name: str = "deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B") -> LocalDeepSeekProvider:
    """Create and initialize a DeepSeek provider"""
    provider = LocalDeepSeekProvider(base_url, model_name)
    await provider.__aenter__()
    return provider

async def quick_generate(prompt: str, 
                        base_url: str = "http://localhost:8000") -> str:
    """Quick generation function for simple use cases"""
    async with LocalDeepSeekProvider(base_url) as provider:
        response = await provider.generate_completion(prompt)
        return response.content