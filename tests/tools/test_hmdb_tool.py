"""Unit tests for HMDBTool."""

import pytest
from unittest.mock import patch, MagicMock

from tooluniverse.hmdb_tool import HMDBTool


class TestHMDBTool:
    """Test suite for HMDBTool."""

    @pytest.fixture
    def tool(self):
        """Create a tool instance with default config."""
        return HMDBTool({"timeout": 10})

    def test_missing_hmdb_id(self, tool):
        """Test error when hmdb_id is missing for get_metabolite."""
        result = tool.run({"operation": "get_metabolite"})
        assert result["status"] == "error"
        assert "hmdb_id" in result["error"]

    def test_missing_query(self, tool):
        """Test error when query is missing for search."""
        result = tool.run({"operation": "search"})
        assert result["status"] == "error"
        assert "query" in result["error"]

    def test_unknown_operation(self, tool):
        """Test error for unknown operation."""
        result = tool.run({"operation": "invalid_op"})
        assert result["status"] == "error"
        assert "Unknown operation" in result["error"]

    @patch("tooluniverse.hmdb_tool.requests.get")
    def test_get_metabolite_success(self, mock_get, tool):
        """Test successful metabolite retrieval via PubChem cross-reference."""
        # First call returns PubChem compound lookup
        mock_pubchem_response = MagicMock()
        mock_pubchem_response.status_code = 200
        mock_pubchem_response.json.return_value = {
            "PC_Compounds": [{"id": {"id": {"cid": 92105}}}]
        }

        # Second call returns compound properties
        mock_props_response = MagicMock()
        mock_props_response.status_code = 200
        mock_props_response.json.return_value = {
            "PropertyTable": {
                "Properties": [{
                    "CID": 92105,
                    "IUPACName": "1-methylhistidine",
                    "MolecularFormula": "C7H11N3O2",
                    "MolecularWeight": 169.18,
                    "CanonicalSMILES": "CN1C=NC(CC(C(=O)O)N)=C1",
                    "InChIKey": "BRMWTNUJHUMWMS-UHFFFAOYSA-N",
                }]
            }
        }

        mock_get.side_effect = [mock_pubchem_response, mock_props_response]

        result = tool.run({"operation": "get_metabolite", "hmdb_id": "HMDB0000001"})

        assert result["status"] == "success"
        assert result["data"]["pubchem_cid"] == 92105
        assert "metadata" in result

    @patch("tooluniverse.hmdb_tool.requests.get")
    def test_get_metabolite_fallback(self, mock_get, tool):
        """Test metabolite returns HMDB URL when PubChem doesn't have cross-reference."""
        mock_response = MagicMock()
        mock_response.status_code = 404  # PubChem doesn't have this HMDB ID
        mock_get.return_value = mock_response

        result = tool.run({"operation": "get_metabolite", "hmdb_id": "HMDB9999999"})
        # Should still succeed with HMDB URL reference
        assert result["status"] == "success"
        assert "hmdb_url" in result["metadata"]


class TestHMDBToolInterface:
    """Test HMDBTool through ToolUniverse interface."""

    def test_tool_registered(self):
        """Test that HMDBTool is properly registered."""
        from tooluniverse import ToolUniverse

        tu = ToolUniverse()
        tu.load_tools()

        assert hasattr(tu.tools, "HMDB_get_metabolite")
        assert hasattr(tu.tools, "HMDB_search")
        assert hasattr(tu.tools, "HMDB_get_diseases")
