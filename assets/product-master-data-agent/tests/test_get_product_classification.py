"""Unit tests for the product classification MCP tool integration."""
from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def add_app_to_path(add_agent_to_path):
    yield


def _get_classification_tools():
    """Load classification mock tools from mcp-mock.json."""
    from langchain_core.tools import StructuredTool
    mock_file = Path(__file__).parent.parent / "mcp-mock.json"
    mock_data = json.loads(mock_file.read_text())
    server = mock_data["servers"]["product-classification"]
    tools = []
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


class TestProductClassificationToolIntegration:
    """Tests for product classification MCP tools."""

    def test_classification_tools_loaded(self):
        """Classification tools should be loadable from mcp-mock.json."""
        tools = _get_classification_tools()
        assert len(tools) > 0
        tool_names = [t.name for t in tools]
        assert "GET_AClfnProduct" in tool_names
        assert "GET_AProductClass" in tool_names

    def test_get_classified_products_returns_list(self):
        """GET_AClfnProduct should return a list of classified products."""
        tools = _get_classification_tools()
        tool = next(t for t in tools if t.name == "GET_AClfnProduct")
        result = tool.invoke({"$top": 10})
        assert "value" in result
        assert len(result["value"]) >= 1
        assert "Product" in result["value"][0]

    def test_get_product_classification_by_id(self):
        """GET_AClfnProduct__Product__ should return classification for a product."""
        tools = _get_classification_tools()
        tool = next(t for t in tools if t.name == "GET_AClfnProduct__Product__")
        result = tool.invoke({"Product": "PROD-001"})
        assert "Product" in result
        assert result["Product"] == "PROD-001"
        assert "ClassInternalID" in result

    def test_get_product_class_assignments_returns_list(self):
        """GET_AProductClass should return class assignments."""
        tools = _get_classification_tools()
        tool = next(t for t in tools if t.name == "GET_AProductClass")
        result = tool.invoke({"$filter": "Product eq 'PROD-001'"})
        assert "value" in result
        first = result["value"][0]
        assert "Product" in first
        assert "ClassInternalID" in first
        assert "ClassName" in first

    def test_get_product_class_by_key(self):
        """Class_Product__Product__ClassInternalID__ClassInternalID__ should return single class."""
        tools = _get_classification_tools()
        tool = next(
            t for t in tools
            if t.name == "Class_Product__Product__ClassInternalID__ClassInternalID__"
        )
        result = tool.invoke({"Product": "PROD-001", "ClassInternalID": "CL-001"})
        assert result["Product"] == "PROD-001"
        assert result["ClassInternalID"] == "CL-001"
        assert "ClassName" in result

    def test_get_product_characteristics(self):
        """GET_AProductCharc should return product characteristics."""
        tools = _get_classification_tools()
        tool = next(t for t in tools if t.name == "GET_AProductCharc")
        result = tool.invoke({"$filter": "Product eq 'PROD-001'"})
        assert "value" in result
        first = result["value"][0]
        assert "CharcInternalID" in first
        assert "CharcName" in first

    def test_get_product_charc_values(self):
        """GET_AProductCharcValue should return characteristic values."""
        tools = _get_classification_tools()
        tool = next(t for t in tools if t.name == "GET_AProductCharcValue")
        result = tool.invoke({})
        assert "value" in result
        first = result["value"][0]
        assert "CharcValue" in first

    def test_get_class_for_key_date(self):
        """GET_AClfnClassForKeyDate should return classification classes."""
        tools = _get_classification_tools()
        tool = next(t for t in tools if t.name == "GET_AClfnClassForKeyDate")
        result = tool.invoke({})
        assert "value" in result
        first = result["value"][0]
        assert "ClassInternalID" in first
        assert "ClassName" in first

    def test_product_toProductClass_navigation(self):
        """GET_AClfnProduct__Product___toProductClass should return class list for product."""
        tools = _get_classification_tools()
        tool = next(t for t in tools if t.name == "GET_AClfnProduct__Product___toProductClass")
        result = tool.invoke({"Product": "PROD-001"})
        assert "value" in result
        first = result["value"][0]
        assert "ClassName" in first
