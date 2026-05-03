"""Unit tests for SAbDab tool."""
import pytest
import json
from unittest.mock import patch, MagicMock

class TestSAbDabToolDirect:
    @pytest.fixture
    def tool_config(self):
        with open("src/tooluniverse/data/sabdab_tools.json") as f:
            return json.load(f)[0]

    @pytest.fixture
    def tool(self, tool_config):
        from tooluniverse.sabdab_tool import SAbDabTool
        return SAbDabTool(tool_config)

    def test_missing_pdb_id(self, tool):
        result = tool.run({"operation": "get_structure"})
        assert result["status"] == "error"

class TestSAbDabToolInterface:
    @pytest.fixture
    def tu(self):
        from tooluniverse import ToolUniverse
        tu = ToolUniverse()
        tu.load_tools()
        return tu

    def test_tools_registered(self, tu):
        assert hasattr(tu.tools, "SAbDab_search_structures")
        assert hasattr(tu.tools, "SAbDab_get_structure")
