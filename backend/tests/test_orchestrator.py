"""
Tests for the AI agent orchestrator
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import json

from app.tests.orchestrator import (
    BrowserToolExecutor,
    VLLMClient,
    AgentOrchestrator,
    BROWSER_TOOLS,
    SYSTEM_PROMPT,
)
from app.projects.schemas import VLLMConfig


class TestBrowserToolExecutor:
    """Tests for BrowserToolExecutor"""
    
    @pytest.fixture
    def executor(self):
        return BrowserToolExecutor()
    
    @pytest.mark.asyncio
    async def test_execute_unknown_tool(self, executor):
        """Test executing an unknown tool returns error"""
        result = await executor.execute("unknown_tool", {})
        
        assert result["success"] is False
        assert "Unknown tool" in result["error"]
    
    @pytest.mark.asyncio
    async def test_execute_navigate_command_mapping(self, executor):
        """Test that navigate command is properly mapped"""
        with patch('asyncio.create_subprocess_exec') as mock_exec:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(return_value=(b'{"status": "ok"}', b''))
            mock_exec.return_value = mock_process
            
            result = await executor.execute("browser_navigate", {"url": "https://example.com"})
            
            # Verify the command was called with correct arguments
            call_args = mock_exec.call_args[0]
            assert "agent-browser" in call_args
            assert "open" in call_args
            assert "https://example.com" in call_args
    
    @pytest.mark.asyncio
    async def test_execute_click_command_mapping(self, executor):
        """Test that click command is properly mapped"""
        with patch('asyncio.create_subprocess_exec') as mock_exec:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(return_value=(b'{"clicked": true}', b''))
            mock_exec.return_value = mock_process
            
            result = await executor.execute("browser_click", {"selector": "#button"})
            
            call_args = mock_exec.call_args[0]
            assert "click" in call_args
            assert "#button" in call_args
    
    @pytest.mark.asyncio
    async def test_execute_handles_json_output(self, executor):
        """Test that JSON output is properly parsed"""
        with patch('asyncio.create_subprocess_exec') as mock_exec:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(return_value=(b'{"data": "test"}', b''))
            mock_exec.return_value = mock_process
            
            result = await executor.execute("browser_snapshot", {})
            
            assert result["success"] is True
            assert result["data"] == {"data": "test"}
    
    @pytest.mark.asyncio
    async def test_execute_handles_non_json_output(self, executor):
        """Test that non-JSON output is returned as string"""
        with patch('asyncio.create_subprocess_exec') as mock_exec:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(return_value=(b'plain text output', b''))
            mock_exec.return_value = mock_process
            
            result = await executor.execute("browser_get_url", {})
            
            assert result["success"] is True
            assert result["data"] == "plain text output"
    
    @pytest.mark.asyncio
    async def test_execute_handles_failure(self, executor):
        """Test that command failure is handled"""
        with patch('asyncio.create_subprocess_exec') as mock_exec:
            mock_process = AsyncMock()
            mock_process.returncode = 1
            mock_process.communicate = AsyncMock(return_value=(b'', b'Error message'))
            mock_exec.return_value = mock_process
            
            result = await executor.execute("browser_navigate", {"url": "https://example.com"})
            
            assert result["success"] is False
            assert "Error message" in result["error"]


class TestVLLMClient:
    """Tests for VLLMClient"""
    
    @pytest.fixture
    def config(self):
        return VLLMConfig(
            api_url="http://localhost:8000",
            model_name="test-model",
            temperature=0.7,
            max_tokens=2048,
        )
    
    @pytest.fixture
    def client(self, config):
        return VLLMClient(config)
    
    def test_client_initialization(self, client, config):
        """Test client is initialized with correct values"""
        assert client.api_url == config.api_url
        assert client.model_name == config.model_name
        assert client.temperature == config.temperature
        assert client.max_tokens == config.max_tokens
    
    def test_client_with_api_key(self):
        """Test client sets authorization header when API key provided"""
        config = VLLMConfig(
            api_url="http://localhost:8000",
            model_name="test-model",
            api_key="test-key",
        )
        client = VLLMClient(config)
        
        assert "Authorization" in client.headers
        assert client.headers["Authorization"] == "Bearer test-key"
    
    @pytest.mark.asyncio
    async def test_generate_sends_correct_payload(self, client):
        """Test that generate sends correct payload to API"""
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={
                "choices": [{"message": {"content": "test response"}}]
            })
            mock_response.raise_for_status = MagicMock()
            
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value = mock_response
            
            mock_session_instance = AsyncMock()
            mock_session_instance.post.return_value = mock_context
            mock_session.return_value.__aenter__.return_value = mock_session_instance
            
            messages = [{"role": "user", "content": "test"}]
            result = await client.generate(messages)
            
            assert result == {"content": "test response"}


class TestAgentOrchestrator:
    """Tests for AgentOrchestrator"""
    
    @pytest.fixture
    def config(self):
        return VLLMConfig(
            api_url="http://localhost:8000",
            model_name="test-model",
        )
    
    @pytest.fixture
    def orchestrator(self, config):
        return AgentOrchestrator(config)
    
    def test_orchestrator_initialization(self, orchestrator):
        """Test orchestrator is initialized correctly"""
        assert orchestrator.llm_client is not None
        assert orchestrator.tool_executor is not None
        assert orchestrator.conversation_history == []
        assert orchestrator.max_iterations == 20
    
    def test_is_task_complete_detection(self, orchestrator):
        """Test task completion detection"""
        complete_messages = [
            "The task is complete.",
            "I have successfully completed the task.",
            "Task has been completed.",
            "Finished the task as requested.",
        ]
        
        incomplete_messages = [
            "I'm working on it.",
            "Let me try another approach.",
            "Here are the results so far.",
        ]
        
        for msg in complete_messages:
            assert orchestrator._is_task_complete(msg) is True, f"Should detect: {msg}"
        
        for msg in incomplete_messages:
            assert orchestrator._is_task_complete(msg) is False, f"Should not detect: {msg}"


class TestBrowserTools:
    """Tests for browser tool definitions"""
    
    def test_all_tools_have_required_fields(self):
        """Test that all tools have required fields"""
        for tool in BROWSER_TOOLS:
            assert "type" in tool
            assert tool["type"] == "function"
            assert "function" in tool
            assert "name" in tool["function"]
            assert "description" in tool["function"]
            assert "parameters" in tool["function"]
    
    def test_navigate_tool_definition(self):
        """Test browser_navigate tool definition"""
        navigate_tool = next(
            (t for t in BROWSER_TOOLS if t["function"]["name"] == "browser_navigate"),
            None
        )
        
        assert navigate_tool is not None
        assert "url" in navigate_tool["function"]["parameters"]["properties"]
        assert "url" in navigate_tool["function"]["parameters"]["required"]
    
    def test_click_tool_definition(self):
        """Test browser_click tool definition"""
        click_tool = next(
            (t for t in BROWSER_TOOLS if t["function"]["name"] == "browser_click"),
            None
        )
        
        assert click_tool is not None
        assert "selector" in click_tool["function"]["parameters"]["properties"]
        assert "selector" in click_tool["function"]["parameters"]["required"]
    
    def test_fill_tool_definition(self):
        """Test browser_fill tool definition"""
        fill_tool = next(
            (t for t in BROWSER_TOOLS if t["function"]["name"] == "browser_fill"),
            None
        )
        
        assert fill_tool is not None
        assert "selector" in fill_tool["function"]["parameters"]["properties"]
        assert "text" in fill_tool["function"]["parameters"]["properties"]
        assert "selector" in fill_tool["function"]["parameters"]["required"]
        assert "text" in fill_tool["function"]["parameters"]["required"]


class TestSystemPrompt:
    """Tests for system prompt"""
    
    def test_system_prompt_contains_key_instructions(self):
        """Test that system prompt contains key instructions"""
        assert "browser" in SYSTEM_PROMPT.lower()
        assert "tool" in SYSTEM_PROMPT.lower()
        assert "navigate" in SYSTEM_PROMPT.lower() or "url" in SYSTEM_PROMPT.lower()
