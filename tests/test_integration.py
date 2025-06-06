"""
Integration Tests for Enhanced CodeAgent
Tests the complete integration between components.
"""

import asyncio
import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from agents.enhanced_code_agent import EnhancedCodeAgent, Task, TaskType
from models.deepseek_provider import LocalDeepSeekProvider, GenerationConfig

@pytest.fixture
async def mock_deepseek_provider():
    """Mock DeepSeek provider for testing"""
    class MockProvider:
        async def __aenter__(self):
            return self
        
        async def __aexit__(self, *args):
            pass
        
        async def health_check(self):
            return True
        
        async def generate_completion(self, prompt, config=None):
            from models.deepseek_provider import ModelResponse
            return ModelResponse(
                content=f"Mock response for: {prompt[:50]}...",
                usage={"prompt_tokens": 10, "completion_tokens": 20},
                model="mock-model",
                finish_reason="stop",
                response_time=0.1
            )
        
        async def generate_code(self, task_description, language="python", context=None):
            return await self.generate_completion(f"Generate {language} code: {task_description}")
        
        async def analyze_code(self, code, task_type="review"):
            return await self.generate_completion(f"Analyze code for {task_type}: {code[:50]}...")
    
    return MockProvider()

@pytest.fixture
async def enhanced_agent(mock_deepseek_provider):
    """Create enhanced agent with mock provider"""
    agent = EnhancedCodeAgent(
        deepseek_url="http://mock:8000",
        model_name="mock-model",
        workspace_path="./test_workspace"
    )
    
    # Replace the provider with mock
    agent.deepseek_provider = mock_deepseek_provider
    await agent.deepseek_provider.__aenter__()
    
    yield agent
    
    await agent.stop()

class TestEnhancedCodeAgent:
    """Test the Enhanced Code Agent"""
    
    @pytest.mark.asyncio
    async def test_code_generation_task(self, enhanced_agent):
        """Test code generation task"""
        task = Task(
            id="test-1",
            type=TaskType.CODE_GENERATION,
            description="Create a function to calculate fibonacci numbers",
            language="python"
        )
        
        result = await enhanced_agent.execute_task(task)
        
        assert result.success
        assert result.task_id == "test-1"
        assert "Mock response" in result.result
        assert result.execution_time > 0
    
    @pytest.mark.asyncio
    async def test_code_review_task(self, enhanced_agent):
        """Test code review task"""
        task = Task(
            id="test-2",
            type=TaskType.CODE_REVIEW,
            description="Review this Python function",
            context={"code": "def add(a, b): return a + b"}
        )
        
        result = await enhanced_agent.execute_task(task)
        
        assert result.success
        assert result.task_id == "test-2"
        assert "Mock response" in result.result
    
    @pytest.mark.asyncio
    async def test_batch_tasks(self, enhanced_agent):
        """Test batch task execution"""
        tasks = [
            Task(
                id="batch-1",
                type=TaskType.CODE_GENERATION,
                description="Create a class",
                language="python"
            ),
            Task(
                id="batch-2",
                type=TaskType.CODE_EXPLANATION,
                description="Explain this code",
                context={"code": "print('hello')"}
            )
        ]
        
        results = await enhanced_agent.execute_batch_tasks(tasks)
        
        assert len(results) == 2
        assert all(result.success for result in results)
        assert results[0].task_id == "batch-1"
        assert results[1].task_id == "batch-2"
    
    @pytest.mark.asyncio
    async def test_file_operations(self, enhanced_agent):
        """Test file operations"""
        # Test write operation
        write_task = Task(
            id="file-write",
            type=TaskType.FILE_OPERATIONS,
            description="Write to file",
            context={
                "operation": "write",
                "file_path": "test.py",
                "content": "print('Hello, World!')"
            }
        )
        
        result = await enhanced_agent.execute_task(write_task)
        assert result.success
        
        # Test read operation
        read_task = Task(
            id="file-read",
            type=TaskType.FILE_OPERATIONS,
            description="Read from file",
            context={
                "operation": "read",
                "file_path": "test.py"
            }
        )
        
        result = await enhanced_agent.execute_task(read_task)
        assert result.success
        assert "Hello, World!" in result.result
    
    @pytest.mark.asyncio
    async def test_task_history(self, enhanced_agent):
        """Test task history tracking"""
        task = Task(
            id="history-test",
            type=TaskType.CODE_GENERATION,
            description="Test task for history",
            language="python"
        )
        
        await enhanced_agent.execute_task(task)
        
        history = enhanced_agent.get_task_history()
        assert len(history) > 0
        assert any(result.task_id == "history-test" for result in history)

class TestDeepSeekProvider:
    """Test the DeepSeek provider (with mocking)"""
    
    @pytest.mark.asyncio
    async def test_generation_config(self):
        """Test generation configuration"""
        config = GenerationConfig(
            temperature=0.7,
            max_tokens=1000,
            top_p=0.9
        )
        
        assert config.temperature == 0.7
        assert config.max_tokens == 1000
        assert config.top_p == 0.9
        assert config.stream == False
    
    @pytest.mark.asyncio
    async def test_mock_provider_health(self, mock_deepseek_provider):
        """Test provider health check"""
        async with mock_deepseek_provider as provider:
            health = await provider.health_check()
            assert health == True

class TestTaskTypes:
    """Test different task types"""
    
    def test_task_type_enum(self):
        """Test TaskType enum"""
        assert TaskType.CODE_GENERATION.value == "code_generation"
        assert TaskType.CODE_REVIEW.value == "code_review"
        assert TaskType.DOCUMENTATION.value == "documentation"
    
    def test_task_creation(self):
        """Test Task creation"""
        task = Task(
            id="test-task",
            type=TaskType.CODE_GENERATION,
            description="Test description",
            language="python",
            priority=2
        )
        
        assert task.id == "test-task"
        assert task.type == TaskType.CODE_GENERATION
        assert task.description == "Test description"
        assert task.language == "python"
        assert task.priority == 2

if __name__ == "__main__":
    pytest.main([__file__, "-v"])