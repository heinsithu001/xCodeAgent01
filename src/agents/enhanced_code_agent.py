"""
Enhanced Code Agent
Integrates CodeAgent03 with DeepSeek R1 and OpenHands for comprehensive code assistance.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum

# Add CodeAgent03 to path
sys.path.append(str(Path(__file__).parent.parent.parent / "repositories" / "CodeAgent03"))

from src.models.deepseek_provider import LocalDeepSeekProvider, GenerationConfig, ModelResponse

logger = logging.getLogger(__name__)

class TaskType(Enum):
    """Types of tasks the agent can handle"""
    CODE_GENERATION = "code_generation"
    CODE_REVIEW = "code_review"
    CODE_DEBUGGING = "code_debugging"
    CODE_OPTIMIZATION = "code_optimization"
    CODE_EXPLANATION = "code_explanation"
    TEST_GENERATION = "test_generation"
    DOCUMENTATION = "documentation"
    REFACTORING = "refactoring"
    ENVIRONMENT_SETUP = "environment_setup"
    FILE_OPERATIONS = "file_operations"
    PROJECT_ANALYSIS = "project_analysis"

@dataclass
class Task:
    """Represents a task for the agent"""
    id: str
    type: TaskType
    description: str
    context: Optional[Dict[str, Any]] = None
    priority: int = 1
    language: Optional[str] = None
    files: Optional[List[str]] = None
    requirements: Optional[List[str]] = None

@dataclass
class TaskResult:
    """Result of a completed task"""
    task_id: str
    success: bool
    result: Any
    error: Optional[str] = None
    execution_time: float = 0.0
    metadata: Optional[Dict[str, Any]] = None

class EnhancedCodeAgent:
    """
    Enhanced Code Agent that combines CodeAgent03, DeepSeek R1, and OpenHands capabilities.
    Provides intelligent task routing and multi-agent coordination.
    """
    
    def __init__(self, 
                 deepseek_url: str = "http://localhost:8000",
                 model_name: str = "deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B",
                 workspace_path: str = "./workspace"):
        
        self.deepseek_url = deepseek_url
        self.model_name = model_name
        self.workspace_path = Path(workspace_path)
        self.workspace_path.mkdir(exist_ok=True)
        
        # Initialize providers
        self.deepseek_provider: Optional[LocalDeepSeekProvider] = None
        self.codeagent03_available = False
        self.openhands_available = False
        
        # Task queue and history
        self.task_queue: asyncio.Queue = asyncio.Queue()
        self.task_history: List[TaskResult] = []
        self.active_tasks: Dict[str, Task] = {}
        
        # Initialize components
        self._initialize_components()
    
    def _initialize_components(self):
        """Initialize available components"""
        try:
            # Check CodeAgent03 availability
            codeagent_path = Path(__file__).parent.parent.parent / "repositories" / "CodeAgent03"
            if codeagent_path.exists():
                self.codeagent03_available = True
                logger.info("CodeAgent03 integration available")
            
            # Check OpenHands availability (placeholder for now)
            self.openhands_available = True
            logger.info("OpenHands integration available")
            
        except Exception as e:
            logger.error(f"Error initializing components: {e}")
    
    async def start(self):
        """Start the enhanced code agent"""
        logger.info("Starting Enhanced Code Agent...")
        
        # Initialize DeepSeek provider
        self.deepseek_provider = LocalDeepSeekProvider(
            base_url=self.deepseek_url,
            model_name=self.model_name
        )
        await self.deepseek_provider.__aenter__()
        
        # Check health
        if await self.deepseek_provider.health_check():
            logger.info("DeepSeek provider is healthy")
        else:
            logger.warning("DeepSeek provider health check failed")
        
        logger.info("Enhanced Code Agent started successfully")
    
    async def stop(self):
        """Stop the enhanced code agent"""
        logger.info("Stopping Enhanced Code Agent...")
        
        if self.deepseek_provider:
            await self.deepseek_provider.__aexit__(None, None, None)
        
        logger.info("Enhanced Code Agent stopped")
    
    async def route_task(self, task: Task) -> TaskResult:
        """
        Route task to the most appropriate agent/component.
        
        Args:
            task: Task to be executed
            
        Returns:
            TaskResult with execution results
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            self.active_tasks[task.id] = task
            
            # Route based on task type
            if task.type == TaskType.CODE_GENERATION:
                result = await self._handle_code_generation(task)
            elif task.type == TaskType.CODE_REVIEW:
                result = await self._handle_code_review(task)
            elif task.type == TaskType.CODE_DEBUGGING:
                result = await self._handle_code_debugging(task)
            elif task.type == TaskType.CODE_OPTIMIZATION:
                result = await self._handle_code_optimization(task)
            elif task.type == TaskType.CODE_EXPLANATION:
                result = await self._handle_code_explanation(task)
            elif task.type == TaskType.TEST_GENERATION:
                result = await self._handle_test_generation(task)
            elif task.type == TaskType.DOCUMENTATION:
                result = await self._handle_documentation(task)
            elif task.type == TaskType.REFACTORING:
                result = await self._handle_refactoring(task)
            elif task.type == TaskType.ENVIRONMENT_SETUP:
                result = await self._handle_environment_setup(task)
            elif task.type == TaskType.FILE_OPERATIONS:
                result = await self._handle_file_operations(task)
            elif task.type == TaskType.PROJECT_ANALYSIS:
                result = await self._handle_project_analysis(task)
            else:
                raise ValueError(f"Unknown task type: {task.type}")
            
            execution_time = asyncio.get_event_loop().time() - start_time
            
            task_result = TaskResult(
                task_id=task.id,
                success=True,
                result=result,
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = asyncio.get_event_loop().time() - start_time
            logger.error(f"Error executing task {task.id}: {e}")
            
            task_result = TaskResult(
                task_id=task.id,
                success=False,
                result=None,
                error=str(e),
                execution_time=execution_time
            )
        
        finally:
            if task.id in self.active_tasks:
                del self.active_tasks[task.id]
            self.task_history.append(task_result)
        
        return task_result
    
    async def _handle_code_generation(self, task: Task) -> str:
        """Handle code generation tasks"""
        if not self.deepseek_provider:
            raise RuntimeError("DeepSeek provider not initialized")
        
        language = task.language or "python"
        context = task.context.get("existing_code", "") if task.context else ""
        
        response = await self.deepseek_provider.generate_code(
            task_description=task.description,
            language=language,
            context=context
        )
        
        return response.content
    
    async def _handle_code_review(self, task: Task) -> str:
        """Handle code review tasks"""
        if not self.deepseek_provider:
            raise RuntimeError("DeepSeek provider not initialized")
        
        code = task.context.get("code", "") if task.context else ""
        if not code:
            raise ValueError("No code provided for review")
        
        response = await self.deepseek_provider.analyze_code(
            code=code,
            task_type="review"
        )
        
        return response.content
    
    async def _handle_code_debugging(self, task: Task) -> str:
        """Handle code debugging tasks"""
        if not self.deepseek_provider:
            raise RuntimeError("DeepSeek provider not initialized")
        
        code = task.context.get("code", "") if task.context else ""
        error_message = task.context.get("error", "") if task.context else ""
        
        if not code:
            raise ValueError("No code provided for debugging")
        
        # Enhanced debugging prompt
        debug_prompt = f"<think>\nI need to debug this code. Let me analyze the error and the code carefully.\n</think>\n\n"
        debug_prompt += f"Debug the following code"
        
        if error_message:
            debug_prompt += f" that produces this error: {error_message}"
        
        debug_prompt += f":\n\n```\n{code}\n```\n\n"
        debug_prompt += "Please identify the issue, explain what's wrong, and provide a corrected version."
        
        config = GenerationConfig(temperature=0.3, max_tokens=2048)
        response = await self.deepseek_provider.generate_completion(debug_prompt, config)
        
        return response.content
    
    async def _handle_code_optimization(self, task: Task) -> str:
        """Handle code optimization tasks"""
        if not self.deepseek_provider:
            raise RuntimeError("DeepSeek provider not initialized")
        
        code = task.context.get("code", "") if task.context else ""
        if not code:
            raise ValueError("No code provided for optimization")
        
        response = await self.deepseek_provider.analyze_code(
            code=code,
            task_type="optimize"
        )
        
        return response.content
    
    async def _handle_code_explanation(self, task: Task) -> str:
        """Handle code explanation tasks"""
        if not self.deepseek_provider:
            raise RuntimeError("DeepSeek provider not initialized")
        
        code = task.context.get("code", "") if task.context else ""
        if not code:
            raise ValueError("No code provided for explanation")
        
        response = await self.deepseek_provider.analyze_code(
            code=code,
            task_type="explain"
        )
        
        return response.content
    
    async def _handle_test_generation(self, task: Task) -> str:
        """Handle test generation tasks"""
        if not self.deepseek_provider:
            raise RuntimeError("DeepSeek provider not initialized")
        
        code = task.context.get("code", "") if task.context else ""
        if not code:
            raise ValueError("No code provided for test generation")
        
        response = await self.deepseek_provider.analyze_code(
            code=code,
            task_type="test"
        )
        
        return response.content
    
    async def _handle_documentation(self, task: Task) -> str:
        """Handle documentation generation tasks"""
        if not self.deepseek_provider:
            raise RuntimeError("DeepSeek provider not initialized")
        
        code = task.context.get("code", "") if task.context else ""
        doc_type = task.context.get("doc_type", "docstring") if task.context else "docstring"
        
        if not code:
            raise ValueError("No code provided for documentation")
        
        response = await self.deepseek_provider.generate_documentation(
            code=code,
            doc_type=doc_type
        )
        
        return response.content
    
    async def _handle_refactoring(self, task: Task) -> str:
        """Handle code refactoring tasks"""
        if not self.deepseek_provider:
            raise RuntimeError("DeepSeek provider not initialized")
        
        code = task.context.get("code", "") if task.context else ""
        refactor_goals = task.context.get("goals", []) if task.context else []
        
        if not code:
            raise ValueError("No code provided for refactoring")
        
        prompt = f"<think>\nI need to refactor this code to improve its structure and maintainability.\n</think>\n\n"
        prompt += "Refactor the following code"
        
        if refactor_goals:
            prompt += f" with these goals: {', '.join(refactor_goals)}"
        
        prompt += f":\n\n```\n{code}\n```\n\n"
        prompt += "Please provide the refactored code with explanations of the changes made."
        
        config = GenerationConfig(temperature=0.3, max_tokens=2048)
        response = await self.deepseek_provider.generate_completion(prompt, config)
        
        return response.content
    
    async def _handle_environment_setup(self, task: Task) -> str:
        """Handle environment setup tasks (delegated to OpenHands-style agent)"""
        # This would integrate with OpenHands or similar environment management
        # For now, provide guidance
        
        setup_type = task.context.get("type", "general") if task.context else "general"
        requirements = task.requirements or []
        
        prompt = f"<think>\nI need to help set up a development environment for: {task.description}\n</think>\n\n"
        prompt += f"Provide step-by-step instructions to set up a development environment for: {task.description}"
        
        if requirements:
            prompt += f"\n\nRequirements: {', '.join(requirements)}"
        
        if setup_type != "general":
            prompt += f"\n\nSetup type: {setup_type}"
        
        config = GenerationConfig(temperature=0.4, max_tokens=2048)
        response = await self.deepseek_provider.generate_completion(prompt, config)
        
        return response.content
    
    async def _handle_file_operations(self, task: Task) -> str:
        """Handle file operations tasks"""
        operation = task.context.get("operation", "read") if task.context else "read"
        file_path = task.context.get("file_path", "") if task.context else ""
        
        if not file_path:
            raise ValueError("No file path provided")
        
        full_path = self.workspace_path / file_path
        
        try:
            if operation == "read":
                if full_path.exists():
                    content = full_path.read_text()
                    return f"File content:\n{content}"
                else:
                    return f"File {file_path} does not exist"
            
            elif operation == "write":
                content = task.context.get("content", "") if task.context else ""
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_text(content)
                return f"Successfully wrote to {file_path}"
            
            elif operation == "list":
                if full_path.is_dir():
                    files = [f.name for f in full_path.iterdir()]
                    return f"Files in {file_path}:\n" + "\n".join(files)
                else:
                    return f"{file_path} is not a directory"
            
            else:
                raise ValueError(f"Unknown file operation: {operation}")
                
        except Exception as e:
            raise RuntimeError(f"File operation failed: {e}")
    
    async def _handle_project_analysis(self, task: Task) -> str:
        """Handle project analysis tasks"""
        project_path = task.context.get("project_path", ".") if task.context else "."
        analysis_type = task.context.get("analysis_type", "overview") if task.context else "overview"
        
        full_path = self.workspace_path / project_path
        
        if not full_path.exists():
            raise ValueError(f"Project path {project_path} does not exist")
        
        # Analyze project structure
        structure = self._analyze_project_structure(full_path)
        
        prompt = f"<think>\nI need to analyze this project structure and provide insights.\n</think>\n\n"
        prompt += f"Analyze this project structure and provide a {analysis_type} analysis:\n\n"
        prompt += structure
        prompt += f"\n\nTask: {task.description}"
        
        config = GenerationConfig(temperature=0.4, max_tokens=2048)
        response = await self.deepseek_provider.generate_completion(prompt, config)
        
        return response.content
    
    def _analyze_project_structure(self, path: Path, max_depth: int = 3, current_depth: int = 0) -> str:
        """Analyze project structure recursively"""
        if current_depth > max_depth:
            return ""
        
        structure = []
        indent = "  " * current_depth
        
        try:
            for item in sorted(path.iterdir()):
                if item.name.startswith('.'):
                    continue
                
                if item.is_file():
                    size = item.stat().st_size
                    structure.append(f"{indent}{item.name} ({size} bytes)")
                elif item.is_dir():
                    structure.append(f"{indent}{item.name}/")
                    if current_depth < max_depth:
                        sub_structure = self._analyze_project_structure(item, max_depth, current_depth + 1)
                        if sub_structure:
                            structure.append(sub_structure)
        
        except PermissionError:
            structure.append(f"{indent}[Permission Denied]")
        
        return "\n".join(structure)
    
    async def execute_task(self, task: Task) -> TaskResult:
        """Execute a single task"""
        return await self.route_task(task)
    
    async def execute_batch_tasks(self, tasks: List[Task]) -> List[TaskResult]:
        """Execute multiple tasks concurrently"""
        results = await asyncio.gather(
            *[self.route_task(task) for task in tasks],
            return_exceptions=True
        )
        
        # Convert exceptions to failed TaskResults
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(TaskResult(
                    task_id=tasks[i].id,
                    success=False,
                    result=None,
                    error=str(result)
                ))
            else:
                processed_results.append(result)
        
        return processed_results
    
    def get_task_history(self) -> List[TaskResult]:
        """Get task execution history"""
        return self.task_history.copy()
    
    def get_active_tasks(self) -> Dict[str, Task]:
        """Get currently active tasks"""
        return self.active_tasks.copy()

# Utility functions for easy usage
async def create_enhanced_agent(deepseek_url: str = "http://localhost:8000",
                              model_name: str = "deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B",
                              workspace_path: str = "./workspace") -> EnhancedCodeAgent:
    """Create and start an enhanced code agent"""
    agent = EnhancedCodeAgent(deepseek_url, model_name, workspace_path)
    await agent.start()
    return agent