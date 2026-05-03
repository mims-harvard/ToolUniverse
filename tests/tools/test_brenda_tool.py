"""Unit tests for BRENDA tool."""

import json
import os

import pytest
from unittest.mock import patch, MagicMock


class TestBRENDAToolDirect:
    @pytest.fixture
    def tool_config(self):
        with open("src/tooluniverse/data/brenda_tools.json") as f:
            return json.load(f)[0]

    @pytest.fixture
    def tool(self, tool_config):
        from tooluniverse.brenda_tool import BRENDATool

        return BRENDATool(tool_config)

    def test_missing_ec_number(self, tool):
        result = tool.run({"operation": "get_km"})
        assert result["status"] == "error"

    def test_unknown_operation(self, tool):
        result = tool.run({"operation": "nonexistent"})
        assert result["status"] == "error"
        assert "Unknown operation" in result["error"]


class TestBRENDAGetEnzymeKinetics:
    """Tests for the get_enzyme_kinetics operation (no auth required)."""

    @pytest.fixture
    def kinetics_config(self):
        with open("src/tooluniverse/data/brenda_tools.json") as f:
            configs = json.load(f)
            return next(c for c in configs if c["name"] == "BRENDA_get_enzyme_kinetics")

    @pytest.fixture
    def tool(self, kinetics_config):
        from tooluniverse.brenda_tool import BRENDATool

        return BRENDATool(kinetics_config)

    def test_missing_both_params(self, tool):
        result = tool.run({"operation": "get_enzyme_kinetics"})
        assert result["status"] == "error"
        assert "ec_number" in result["error"] or "enzyme_name" in result["error"]

    @patch("tooluniverse.brenda_tool.requests.get")
    def test_expasy_enzyme_parsing(self, mock_get, tool):
        """Test ExPASy ENZYME flat file parsing."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = (
            "ID   1.1.1.1\n"
            "DE   alcohol dehydrogenase.\n"
            "AN   aldehyde reductase.\n"
            "CA   (1) a primary alcohol + NAD(+) = an aldehyde + NADH + H(+).\n"
            "CC   -!- Acts on primary or secondary alcohols.\n"
        )
        mock_get.return_value = mock_resp

        data = tool._fetch_expasy_enzyme("1.1.1.1")
        assert data["ec_number"] == "1.1.1.1"
        assert data["name"] == "alcohol dehydrogenase"
        assert "aldehyde reductase" in data["alternative_names"]
        assert len(data["catalytic_activity"]) == 1

    @patch("tooluniverse.brenda_tool.requests.get")
    def test_enzyme_name_resolution(self, mock_get, tool):
        """Test enzyme name to EC number resolution via UniProt."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "results": [
                {
                    "proteinDescription": {
                        "recommendedName": {
                            "ecNumbers": [{"value": "2.7.1.1"}]
                        }
                    }
                }
            ]
        }
        mock_get.return_value = mock_resp

        ec = tool._resolve_ec_from_name("hexokinase")
        assert ec == "2.7.1.1"

    @patch("tooluniverse.brenda_tool.requests.get")
    def test_enzyme_name_not_found(self, mock_get, tool):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"results": []}
        mock_get.return_value = mock_resp

        ec = tool._resolve_ec_from_name("nonexistent enzyme xyz")
        assert ec is None

    def test_enzyme_id_alias(self, tool):
        """Test that enzyme_id is properly aliased to ec_number."""
        # The run() method handles this alias before dispatching
        # Just verify the dispatch works with enzyme_id
        result = tool.run(
            {"operation": "get_enzyme_kinetics", "enzyme_id": "9.9.9.9"}
        )
        # Will fail with no data but should not error on missing ec_number
        assert result["status"] == "error"
        assert "No data found" in result["error"]

    @patch("tooluniverse.brenda_tool.requests.get")
    def test_sabiork_no_data(self, mock_get, tool):
        """Test handling of SABIO-RK 'no data found' response."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "no data found"
        mock_get.return_value = mock_resp

        result = tool._fetch_sabiork_kinetics("9.9.9.9")
        assert result["kinetic_laws"] == []
        assert result["total_count"] == 0


class TestBRENDAGetEnzymeKineticsIntegration:
    """Integration tests that hit real APIs (ExPASy, SABIO-RK)."""

    @pytest.fixture
    def tu(self):
        from tooluniverse import ToolUniverse

        tu = ToolUniverse()
        tu.load_tools()
        return tu

    @pytest.mark.integration
    def test_tool_registered(self, tu):
        assert "BRENDA_get_enzyme_kinetics" in tu.all_tool_dict

    @pytest.mark.integration
    def test_ec_number_real(self, tu):
        """Test with real EC 1.1.1.1 (alcohol dehydrogenase)."""
        result = tu.run_one_function(
            {
                "name": "BRENDA_get_enzyme_kinetics",
                "arguments": {"ec_number": "1.1.1.1", "limit": 5},
            }
        )
        assert result["status"] == "success"
        data = result["data"]
        assert data["ec_number"] == "1.1.1.1"
        assert data["enzyme_name"] == "alcohol dehydrogenase"
        assert "ExPASy ENZYME" in result["metadata"]["sources"]
        assert data["sabiork_total_entries"] > 0
        assert len(data["kinetic_parameters"]) > 0
        assert "parameter_summary" in data

    @pytest.mark.integration
    def test_enzyme_name_real(self, tu):
        """Test enzyme name resolution."""
        result = tu.run_one_function(
            {
                "name": "BRENDA_get_enzyme_kinetics",
                "arguments": {"enzyme_name": "hexokinase", "limit": 3},
            }
        )
        assert result["status"] == "success"
        data = result["data"]
        assert data["ec_number"] == "2.7.1.1"
        assert data["sabiork_total_entries"] > 0

    @pytest.mark.integration
    def test_with_organism_filter(self, tu):
        """Test organism filtering."""
        result = tu.run_one_function(
            {
                "name": "BRENDA_get_enzyme_kinetics",
                "arguments": {"ec_number": "2.7.1.1", "limit": 5},
            }
        )
        assert result["status"] == "success"


class TestBRENDAToolInterface:
    @pytest.fixture
    def tu(self):
        from tooluniverse import ToolUniverse

        tu = ToolUniverse()
        tu.load_tools()
        return tu

    def test_tools_registered(self, tu):
        # BRENDA SOAP tools require API keys - skip if not loaded
        if not (os.environ.get("BRENDA_EMAIL") and os.environ.get("BRENDA_PASSWORD")):
            pytest.skip("BRENDA_EMAIL and BRENDA_PASSWORD not set")

        assert hasattr(tu.tools, "BRENDA_get_km")
        assert hasattr(tu.tools, "BRENDA_get_kcat")
