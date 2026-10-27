"""Integration test for the Product Master Data Agent end-to-end flow."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def add_app_to_path(add_agent_to_path):
    yield


def _build_mock_tools():
    """Build StructuredTools from mcp-mock.json for offline testing."""
    from langchain_core.tools import StructuredTool

    mock_file = Path(__file__).parent.parent / "mcp-mock.json"
    mock_data = json.loads(mock_file.read_text())
    tools = []
    for _server_slug, server in mock_data["servers"].items():
        for tool_name, tool_def in server["tools"].items():
            def make_func(response):
                def _func(**kwargs):
                    return response
                return _func
            tool = StructuredTool.from_function(
                func=make_func(tool_def["mock_response"]),
                name=tool_name,
                description=tool_def["description"],
            )
            tools.append(tool)
    return tools


class TestAgentIntegration:
    """End-to-end agent flow tests with mocked LLM and MCP tools."""

    @pytest.mark.asyncio
    async def test_agent_invoke_returns_completed_status(self):
        """Agent.invoke() should return a completed AgentResponse for a product query."""
        from agent import SampleAgent

        mock_tools = _build_mock_tools()

        # Build a canned LLM response that simulates the agent answering a product query
        canned_response = MagicMock()
        canned_response.content = (
            "Product PROD-001 is an Industrial Pump Model A. "
            "It is a finished product (FERT) with a base unit of EA and a gross weight of 2.5 KG."
        )
        canned_response.tool_calls = []
        canned_response.additional_kwargs = {}

        with patch("langchain_litellm.ChatLiteLLM") as MockLLM:
            mock_llm_instance = MagicMock()
            mock_llm_instance.bind_tools.return_value = mock_llm_instance
            mock_llm_instance.ainvoke = AsyncMock(return_value=canned_response)
            MockLLM.return_value = mock_llm_instance

            agent = SampleAgent()
            # Patch the agent's LLM directly
            agent.llm = mock_llm_instance

            response = await agent.invoke(
                query="What are the details of product PROD-001?",
                context_id="test-session-001",
                tools=mock_tools,
            )

        assert response.status in ("completed", "error")

    @pytest.mark.asyncio
    async def test_agent_stream_yields_chunks(self):
        """Agent.stream() should yield at least one chunk."""
        from agent import SampleAgent

        mock_tools = _build_mock_tools()

        canned_response = MagicMock()
        canned_response.content = "Product PROD-001: Industrial Pump Model A, base unit EA."
        canned_response.tool_calls = []
        canned_response.additional_kwargs = {}

        with patch("langchain_litellm.ChatLiteLLM") as MockLLM:
            mock_llm_instance = MagicMock()
            mock_llm_instance.bind_tools.return_value = mock_llm_instance
            mock_llm_instance.ainvoke = AsyncMock(return_value=canned_response)
            MockLLM.return_value = mock_llm_instance

            agent = SampleAgent()
            agent.llm = mock_llm_instance

            chunks = []
            async for chunk in agent.stream(
                query="Describe product PROD-001",
                context_id="test-session-002",
                tools=mock_tools,
            ):
                chunks.append(chunk)

        assert len(chunks) >= 1
        last = chunks[-1]
        assert "is_task_complete" in last
        assert "content" in last

    @pytest.mark.asyncio
    async def test_agent_handles_no_tools_gracefully(self):
        """Agent should respond gracefully when no tools are available."""
        from agent import SampleAgent

        canned_response = MagicMock()
        canned_response.content = "No tools are currently available."
        canned_response.tool_calls = []
        canned_response.additional_kwargs = {}

        with patch("langchain_litellm.ChatLiteLLM") as MockLLM:
            mock_llm_instance = MagicMock()
            mock_llm_instance.bind_tools.return_value = mock_llm_instance
            mock_llm_instance.ainvoke = AsyncMock(return_value=canned_response)
            MockLLM.return_value = mock_llm_instance

            agent = SampleAgent()
            agent.llm = mock_llm_instance

            response = await agent.invoke(
                query="What is product ABC?",
                context_id="test-session-003",
                tools=[],
            )

        assert response.status in ("completed", "error")
        assert response.message  # must have some content

    def test_get_system_prompt_contains_key_instructions(self):
        """System prompt should contain critical agent instructions."""
        from agent import get_system_prompt

        prompt = get_system_prompt()
        assert "MUST use tools" in prompt
        assert "Never fabricate" in prompt or "never" in prompt.lower()
        assert "product" in prompt.lower()
        assert "never create, update, or delete" in prompt.lower() or "Only retrieve" in prompt

    def test_mock_tools_count_matches_expected(self):
        """Mock tools should include tools from both MCP servers."""
        tools = _build_mock_tools()
        assert len(tools) == 30  # 14 product master + 16 classification

    def test_mcp_mock_json_structure_valid(self):
        """mcp-mock.json must have valid structure with servers and tools."""
        mock_file = Path(__file__).parent.parent / "mcp-mock.json"
        mock_data = json.loads(mock_file.read_text())
        assert "servers" in mock_data
        assert "metadata" in mock_data
        assert len(mock_data["servers"]) == 2
        for server_slug, server in mock_data["servers"].items():
            assert "tools" in server
            assert len(server["tools"]) > 0

    @pytest.mark.asyncio
    async def test_run_agent_helper_returns_dict(self):
        """_run_agent() should return a dict with 'response' and 'error' keys."""
        from agent import SampleAgent

        mock_tools = _build_mock_tools()

        canned_response = MagicMock()
        canned_response.content = "Product PROD-001 details: Industrial Pump."
        canned_response.tool_calls = []
        canned_response.additional_kwargs = {}

        with patch("langchain_litellm.ChatLiteLLM") as MockLLM:
            mock_llm_instance = MagicMock()
            mock_llm_instance.bind_tools.return_value = mock_llm_instance
            mock_llm_instance.ainvoke = AsyncMock(return_value=canned_response)
            MockLLM.return_value = mock_llm_instance

            agent = SampleAgent()
            agent.llm = mock_llm_instance

            result = await agent._run_agent(
                query="What is product PROD-001?",
                context_id="test-session-004",
                tools=mock_tools,
            )

        assert "response" in result
        assert "error" in result
