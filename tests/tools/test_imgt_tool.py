"""Unit tests for IMGT tool."""
import pytest
import json
from unittest.mock import patch, MagicMock

class TestIMGTToolDirect:
    @pytest.fixture
    def tool_config(self):
        with open("src/tooluniverse/data/imgt_tools.json") as f:
            return json.load(f)[0]

    @pytest.fixture
    def tool(self, tool_config):
        from tooluniverse.imgt_tool import IMGTTool
        return IMGTTool(tool_config)

    def test_missing_accession(self, tool):
        result = tool.run({"operation": "get_sequence"})
        assert result["status"] == "error"

    def test_get_gene_info(self, tool):
        result = tool.run({"operation": "get_gene_info"})
        assert result["status"] == "success"

class TestIMGTToolInterface:
    @pytest.fixture
    def tu(self):
        from tooluniverse import ToolUniverse
        tu = ToolUniverse()
        tu.load_tools()
        return tu

    def test_tools_registered(self, tu):
        assert hasattr(tu.tools, "IMGT_get_sequence")
        assert hasattr(tu.tools, "IMGT_get_gene_info")
