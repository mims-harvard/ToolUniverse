"""
Unit tests for GPCRdb tool.
"""

import pytest
import json
from unittest.mock import patch, MagicMock


class TestGPCRdbToolDirect:
    @pytest.fixture
    def tool_config(self):
        with open("src/tooluniverse/data/gpcrdb_tools.json") as f:
            tools = json.load(f)
            return next(t for t in tools if t["name"] == "GPCRdb_get_protein")

    @pytest.fixture
    def tool(self, tool_config):
        from tooluniverse.gpcrdb_tool import GPCRdbTool
        return GPCRdbTool(tool_config)

    def test_missing_protein(self, tool):
        result = tool.run({"operation": "get_protein"})
        assert result["status"] == "error"

    @patch("tooluniverse.gpcrdb_tool.requests.get")
    def test_get_protein_success(self, mock_get, tool):
        mock_response = MagicMock()
        mock_response.json.return_value = {"entry_name": "adrb2_human", "name": "Beta-2 adrenergic receptor"}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = tool.run({"operation": "get_protein", "protein": "adrb2_human"})
        assert result["status"] == "success"


class TestGPCRdbToolInterface:
    @pytest.fixture
    def tu(self):
        from tooluniverse import ToolUniverse
        tu = ToolUniverse()
        tu.load_tools()
        return tu

    def test_tools_registered(self, tu):
        assert hasattr(tu.tools, "GPCRdb_get_protein")
        assert hasattr(tu.tools, "GPCRdb_list_proteins")
        assert hasattr(tu.tools, "GPCRdb_get_structures")
        assert hasattr(tu.tools, "GPCRdb_get_ligands")
