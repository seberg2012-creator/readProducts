"""Unit tests for the product master data MCP tool integration."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def add_app_to_path(add_agent_to_path):
    """Ensure app/ is on sys.path via the shared fixture."""
    yield


def _get_mock_tools():
    """Load mock tools from mcp-mock.json and return as LangChain StructuredTools."""
    from langchain_core.tools import StructuredTool
    mock_file = Path(__file__).parent.parent / "mcp-mock.json"
    mock_data = json.loads(mock_file.read_text())
    tools = []
    for server_slug, server in mock_data["servers"].items():
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


class TestProductMasterToolIntegration:
    """Tests for product master data MCP tool calls."""

    def test_mock_tools_loaded(self):
        """Mock tools should be loadable from mcp-mock.json."""
        tools = _get_mock_tools()
        assert len(tools) > 0
        tool_names = [t.name for t in tools]
        assert "list_a_product_for_api_product_srv" in tool_names
        assert "get_a_product_for_api_product_srv" in tool_names

    def test_list_products_tool_returns_results(self):
        """list_a_product_for_api_product_srv tool should return product list."""
        tools = _get_mock_tools()
        list_tool = next(t for t in tools if t.name == "list_a_product_for_api_product_srv")
        result = list_tool.invoke({"top": 10})
        assert "results" in result
        assert len(result["results"]) >= 1
        assert "Product" in result["results"][0]
        assert "ProductType" in result["results"][0]

    def test_get_product_by_id_tool_returns_single_product(self):
        """get_a_product_for_api_product_srv tool should return a single product."""
        tools = _get_mock_tools()
        get_tool = next(t for t in tools if t.name == "get_a_product_for_api_product_srv")
        result = get_tool.invoke({"Product": "PROD-001"})
        assert "Product" in result
        assert result["Product"] == "PROD-001"
        assert "ProductType" in result
        assert "BaseUnit" in result

    def test_list_product_descriptions_returns_results(self):
        """list_a_productdescription_for_api_product_srv should return descriptions."""
        tools = _get_mock_tools()
        desc_tool = next(t for t in tools if t.name == "list_a_productdescription_for_api_product_srv")
        result = desc_tool.invoke({"filter": "Product eq 'PROD-001'"})
        assert "results" in result
        assert len(result["results"]) >= 1
        first = result["results"][0]
        assert "Product" in first
        assert "Language" in first
        assert "ProductName" in first

    def test_get_product_description_by_key(self):
        """get_a_productdescription_for_api_product_srv should return single description."""
        tools = _get_mock_tools()
        desc_tool = next(t for t in tools if t.name == "get_a_productdescription_for_api_product_srv")
        result = desc_tool.invoke({"Product": "PROD-001", "Language": "EN"})
        assert result["Product"] == "PROD-001"
        assert result["Language"] == "EN"
        assert "ProductName" in result

    def test_get_metadata_tool_returns_metadata(self):
        """get_metadata_api_product_srv should return metadata."""
        tools = _get_mock_tools()
        meta_tool = next(t for t in tools if t.name == "get_metadata_api_product_srv")
        result = meta_tool.invoke({})
        assert "metadata" in result

    def test_list_product_basic_text_returns_long_description(self):
        """list_a_productbasictext_for_api_product_srv should return long text."""
        tools = _get_mock_tools()
        text_tool = next(t for t in tools if t.name == "list_a_productbasictext_for_api_product_srv")
        result = text_tool.invoke({})
        assert "results" in result
        first = result["results"][0]
        assert "LongText" in first

    def test_product_tool_names_have_no_invalid_chars(self):
        """All product master tool names should not contain spaces."""
        tools = _get_mock_tools()
        product_tools = [t for t in tools if "product" in t.name.lower()]
        for tool in product_tools:
            assert " " not in tool.name, f"Tool name contains space: {tool.name}"
