"""
Unit tests for BindingDB tool.
"""

import pytest
import json
from unittest.mock import patch, MagicMock


class TestBindingDBToolDirect:
    """Test BindingDB tool directly (Level 1)."""

    @pytest.fixture
    def tool_config(self):
        with open("src/tooluniverse/data/bindingdb_tools.json") as f:
            tools = json.load(f)
            return next(t for t in tools if t["name"] == "BindingDB_get_ligands_by_uniprot")

    @pytest.fixture
    def tool(self, tool_config):
        from tooluniverse.bindingdb_tool import BindingDBTool
        return BindingDBTool(tool_config)

    def test_missing_uniprot_id(self, tool):
        result = tool.run({"operation": "get_ligands_by_uniprot"})
        assert result["status"] == "error"
        assert "uniprot" in result["error"].lower()

    def test_unknown_operation(self, tool):
        result = tool.run({"operation": "unknown"})
        assert result["status"] == "error"

    @patch("tooluniverse.bindingdb_tool.requests.get")
    def test_get_by_uniprot_success(self, mock_get, tool):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "getLindsByUniprotResponse": {
                "bdb.affinities": [
                    {"query": "P00533", "monomerid": "12345", "smile": "CCO", "affinity_type": "IC50", "affinity": "100", "pmid": None, "doi": None}
                ]
            }
        }
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = tool.run({"operation": "get_ligands_by_uniprot", "uniprot": "P00533"})
        assert result["status"] == "success"
        assert "data" in result
        assert len(result["data"]) > 0


class TestBindingDBToolInterface:
    """Test BindingDB tool via ToolUniverse interface (Level 2)."""

    @pytest.fixture
    def tu(self):
        from tooluniverse import ToolUniverse
        tu = ToolUniverse()
        tu.load_tools()
        return tu

    def test_tools_registered(self, tu):
        assert hasattr(tu.tools, "BindingDB_get_ligands_by_uniprot")
        assert hasattr(tu.tools, "BindingDB_get_ligands_by_uniprots")
        assert hasattr(tu.tools, "BindingDB_get_ligands_by_pdb")
        assert hasattr(tu.tools, "BindingDB_get_targets_by_compound")
