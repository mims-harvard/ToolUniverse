"""Unit tests for MetaboliteTool (replaces the retired direct-HMDB-API tool)."""

import pytest
from tooluniverse import ToolUniverse
from tooluniverse.metabolite_tool import MetaboliteTool


class TestMetaboliteToolValidation:
    """Fast, network-free validation tests."""

    @pytest.fixture
    def tool(self):
        return MetaboliteTool({"timeout": 10})

    def test_missing_identifier_for_get_info(self, tool):
        result = tool.run({"operation": "get_info"})
        assert result["status"] == "error"
        assert "hmdb_id" in result["error"] or "compound_name" in result["error"]

    def test_missing_query_for_search(self, tool):
        result = tool.run({"operation": "search"})
        assert result["status"] == "error"
        assert "query" in result["error"]

    def test_missing_identifier_for_get_diseases(self, tool):
        result = tool.run({"operation": "get_diseases"})
        assert result["status"] == "error"

    def test_unknown_operation(self, tool):
        result = tool.run({"operation": "invalid_op"})
        assert result["status"] == "error"
        assert "Unknown operation" in result["error"]


class TestMetaboliteToolsRegistered:
    """Test the current metabolite tool family (and HMDB_* aliases) load correctly."""

    @pytest.fixture
    def tu(self):
        tu = ToolUniverse()
        tu.load_tools()
        return tu

    def test_tools_load(self, tu):
        tool_names = [tool.get("name") for tool in tu.all_tools if isinstance(tool, dict)]

        expected_tools = [
            "Metabolite_get_info",
            "Metabolite_search",
            "Metabolite_get_diseases",
            "HMDB_search",
            "HMDB_get_metabolite",
            "HMDB_get_diseases",
        ]

        for tool_name in expected_tools:
            assert tool_name in tool_names, f"Tool {tool_name} not found"

    def test_get_info_by_compound_name(self, tu):
        result = tu.tools.Metabolite_get_info(**{"compound_name": "glucose"})

        assert result.get("status") == "success" or "error" in result
        if result.get("status") == "success":
            data = result["data"]
            assert data["pubchem_cid"]
            assert data["formula"]

    def test_search_by_name(self, tu):
        result = tu.tools.Metabolite_search(**{"query": "caffeine"})

        assert result.get("status") == "success" or "error" in result
        if result.get("status") == "success":
            data = result["data"]
            assert "results" in data
            assert "count" in data
            assert isinstance(data["results"], list)

    def test_get_diseases_by_compound_name(self, tu):
        result = tu.tools.Metabolite_get_diseases(**{"compound_name": "glucose"})

        assert result.get("status") == "success" or "error" in result
        if result.get("status") == "success":
            assert "data" in result

    def test_hmdb_alias_search(self, tu):
        """HMDB_search is a documented alias for Metabolite_search."""
        result = tu.tools.HMDB_search(**{"query": "glucose"})

        assert result.get("status") == "success" or "error" in result
