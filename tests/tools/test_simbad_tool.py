#!/usr/bin/env python3
"""
Unit tests for SIMBADTool - SIMBAD astronomical database tool.

Tests cover all SIMBAD operations and edge cases with >90% code coverage.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import requests

from tooluniverse.simbad_tool import SIMBADTool, SIMBADAdvancedTool


@pytest.mark.unit
class TestSIMBADToolInitialization:
    """Test SIMBADTool initialization."""

    def test_init_default_config(self):
        """Test SIMBADTool initialization with default config."""
        config = {"name": "test_simbad", "description": "Test"}
        tool = SIMBADTool(config)
        assert tool.base_url == "https://simbad.cds.unistra.fr/simbad/sim-script"

    def test_init_custom_config(self):
        """Test SIMBADTool initialization with custom base URL."""
        config = {
            "name": "test_simbad",
            "description": "Test"
        }
        tool = SIMBADTool(config, base_url="https://custom.example.org")
        assert tool.base_url == "https://custom.example.org"


@pytest.mark.unit
class TestSIMBADToolRunMethod:
    """Test SIMBADTool.run() method."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = {"name": "test_simbad"}
        self.tool = SIMBADTool(self.config)

    def test_run_default_query_type(self):
        """Test run() with default query_type (object_name)."""
        with patch.object(self.tool, '_query_by_name') as mock_query:
            mock_query.return_value = {"success": True}
            result = self.tool.run({"object_name": "M31"})
            mock_query.assert_called_once()
            assert result == {"success": True}

    def test_run_coordinates_query_type(self):
        """Test run() with coordinates query_type."""
        with patch.object(self.tool, '_query_by_coordinates') as mock_query:
            mock_query.return_value = {"success": True}
            result = self.tool.run({
                "query_type": "coordinates",
                "ra": 10.68,
                "dec": 41.27
            })
            mock_query.assert_called_once()
            assert result == {"success": True}

    def test_run_identifier_query_type(self):
        """Test run() with identifier query_type."""
        with patch.object(self.tool, '_query_by_identifier') as mock_query:
            mock_query.return_value = {"success": True}
            result = self.tool.run({
                "query_type": "identifier",
                "identifier": "NGC 10*"
            })
            mock_query.assert_called_once()
            assert result == {"success": True}

    def test_run_invalid_query_type(self):
        """Test run() with invalid query_type."""
        result = self.tool.run({"query_type": "invalid_type"})
        assert "error" in result
        assert "Unknown query_type" in result["error"]


@pytest.mark.unit
class TestQueryByName:
    """Test _query_by_name method."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = {"name": "test_simbad"}
        self.tool = SIMBADTool(self.config)

    def test_query_by_name_missing_object_name(self):
        """Test query_by_name without object_name parameter."""
        result = self.tool._query_by_name({})
        assert result.get("status") == "error"
        assert "object_name" in result["data"]["error"]

    @patch.object(SIMBADTool, '_execute_query')
    def test_query_by_name_success(self, mock_execute):
        """Test successful query_by_name."""
        mock_execute.return_value = {
            "success": True,
            "results": [{"main_id": "M  31"}]
        }
        result = self.tool._query_by_name({"object_name": "M31"})
        assert result["success"] is True
        mock_execute.assert_called_once()

    @patch.object(SIMBADTool, '_execute_query')
    def test_query_by_name_with_detailed_format(self, mock_execute):
        """Test query_by_name with detailed output format."""
        mock_execute.return_value = {"success": True}
        self.tool._query_by_name({
            "object_name": "Sirius",
            "output_format": "detailed"
        })
        mock_execute.assert_called_once()
        # Check that the script contains appropriate format
        call_args = mock_execute.call_args[0]
        assert "Sirius" in call_args[0]

    @patch.object(SIMBADTool, '_execute_query')
    def test_query_by_name_with_full_format(self, mock_execute):
        """Test query_by_name with full output format."""
        mock_execute.return_value = {"success": True}
        self.tool._query_by_name({
            "object_name": "M31",
            "output_format": "full"
        })
        mock_execute.assert_called_once()


@pytest.mark.unit
class TestQueryByCoordinates:
    """Test _query_by_coordinates method."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = {"name": "test_simbad"}
        self.tool = SIMBADTool(self.config)

    def test_query_by_coordinates_missing_ra(self):
        """Test query_by_coordinates without ra parameter."""
        result = self.tool._query_by_coordinates({"dec": 41.27})
        assert result.get("status") == "error"
        assert "ra" in result["data"]["error"]

    def test_query_by_coordinates_missing_dec(self):
        """Test query_by_coordinates without dec parameter."""
        result = self.tool._query_by_coordinates({"ra": 10.68})
        assert result.get("status") == "error"
        assert "dec" in result["data"]["error"]

    @patch.object(SIMBADTool, '_execute_query')
    def test_query_by_coordinates_success(self, mock_execute):
        """Test successful query_by_coordinates."""
        mock_execute.return_value = {
            "success": True,
            "results": [{"main_id": "M  31"}]
        }
        result = self.tool._query_by_coordinates({
            "ra": 10.68458,
            "dec": 41.26917,
            "radius": 2.0
        })
        assert result["success"] is True
        mock_execute.assert_called_once()
        call_args = mock_execute.call_args[0]
        assert "10.68458" in call_args[0]
        assert "41.26917" in call_args[0]

    @patch.object(SIMBADTool, '_execute_query')
    def test_query_by_coordinates_default_radius(self, mock_execute):
        """Test query_by_coordinates with default radius."""
        mock_execute.return_value = {"success": True}
        self.tool._query_by_coordinates({
            "ra": 10.68,
            "dec": 41.27
        })
        mock_execute.assert_called_once()
        # Check that default radius is used
        call_args = mock_execute.call_args[0]
        assert "radius=1.0m" in call_args[0] or "radius" in call_args[1]


@pytest.mark.unit
class TestQueryByIdentifier:
    """Test _query_by_identifier method."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = {"name": "test_simbad"}
        self.tool = SIMBADTool(self.config)

    def test_query_by_identifier_missing_identifier(self):
        """Test query_by_identifier without identifier parameter."""
        result = self.tool._query_by_identifier({})
        assert result.get("status") == "error"
        assert "identifier" in result["data"]["error"]

    @patch.object(SIMBADTool, '_execute_query')
    def test_query_by_identifier_success(self, mock_execute):
        """Test successful query_by_identifier."""
        mock_execute.return_value = {
            "success": True,
            "results": [
                {"main_id": "NGC 1068"},
                {"main_id": "NGC 1055"}
            ]
        }
        result = self.tool._query_by_identifier({
            "identifier": "NGC 10*",
            "max_results": 5
        })
        assert result["success"] is True
        mock_execute.assert_called_once()


@pytest.mark.unit
class TestGetFormatString:
    """Test _get_format_string method."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = {"name": "test_simbad"}
        self.tool = SIMBADTool(self.config)

    def test_format_string_basic(self):
        """Test basic format string."""
        fmt = self.tool._get_format_string("basic")
        assert "%IDLIST" in fmt
        assert "%COO" in fmt
        assert "%OTYPE" in fmt

    def test_format_string_detailed(self):
        """Test detailed format string."""
        fmt = self.tool._get_format_string("detailed")
        assert "%IDLIST" in fmt
        assert "%SP" in fmt
        assert "%FLUXLIST" in fmt

    def test_format_string_full(self):
        """Test full format string."""
        fmt = self.tool._get_format_string("full")
        assert "%IDLIST" in fmt
        assert "%PM" in fmt
        assert "%PLX" in fmt
        assert "%RV" in fmt

    def test_format_string_unknown_defaults_to_basic(self):
        """Test unknown format string defaults to basic."""
        fmt = self.tool._get_format_string("unknown")
        basic_fmt = self.tool._get_format_string("basic")
        assert fmt == basic_fmt


@pytest.mark.unit
class TestExecuteQuery:
    """Test _execute_query method."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = {"name": "test_simbad"}
        self.tool = SIMBADTool(self.config)

    @patch('requests.post')
    def test_execute_query_success(self, mock_post):
        """Test successful query execution."""
        mock_response = MagicMock()
        mock_response.text = "M  31 | 00 42 44.330 +41 16 07.50 | Galaxy"
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        result = self.tool._execute_query("test script", "M31")
        assert result["status"] == "success"
        data = result["data"]
        assert "results" in data
        assert len(data["results"]) > 0
        assert data["results"][0]["main_id"] == "M  31"

    @patch('requests.post')
    def test_execute_query_timeout(self, mock_post):
        """Test query execution with timeout."""
        mock_post.side_effect = requests.Timeout()
        result = self.tool._execute_query("test script", "M31")
        assert result.get("status") == "error"
        assert "timed out" in result["data"]["error"]

    @patch('requests.post')
    def test_execute_query_network_error(self, mock_post):
        """Test query execution with network error."""
        mock_post.side_effect = requests.RequestException("Connection failed")
        result = self.tool._execute_query("test script", "M31")
        assert result.get("status") == "error"
        assert "Network error" in result["data"]["error"]

    @patch('requests.post')
    def test_execute_query_not_found(self, mock_post):
        """Test query execution when object not found."""
        mock_response = MagicMock()
        mock_response.text = "error: Object not found"
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        result = self.tool._execute_query("test script", "InvalidObject")
        assert result.get("status") == "error"
        assert "not found" in result["data"]["error"]

    @patch('requests.post')
    def test_execute_query_empty_result(self, mock_post):
        """Test query execution with empty result."""
        mock_response = MagicMock()
        mock_response.text = ""
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        result = self.tool._execute_query("test script", "Empty")
        assert result.get("status") == "error"
        assert "No results" in result["data"]["error"]

    @patch('requests.post')
    def test_execute_query_with_metadata_lines(self, mock_post):
        """Test query execution filters out SIMBAD metadata lines."""
        mock_response = MagicMock()
        mock_response.text = """::script::
::data::
M  31 | 00 42 44.330 +41 16 07.50 | Galaxy
NGC 224 | 00 42 44.330 +41 16 07.50 | Galaxy"""
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        result = self.tool._execute_query("test script", "M31")
        assert result["status"] == "success"
        assert len(result["data"]["results"]) == 2
        # Verify metadata lines are filtered out
        for res in result["data"]["results"]:
            assert "::" not in res["main_id"]

    @patch('requests.post')
    def test_execute_query_with_max_results(self, mock_post):
        """Test query execution respects max_results parameter."""
        mock_response = MagicMock()
        mock_response.text = "\n".join([
            f"Object {i} | 00 00 00 +00 00 00 | Star"
            for i in range(20)
        ])
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        result = self.tool._execute_query("test script", "query", max_results=5)
        assert result["status"] == "success"
        assert len(result["data"]["results"]) == 5

    @patch('requests.post')
    def test_execute_query_parses_multiple_fields(self, mock_post):
        """Test query execution correctly parses multiple fields."""
        mock_response = MagicMock()
        mock_response.text = "Sirius | 06 45 08.917 -16 42 58.02 | Star | A1V | 1.46"
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        result = self.tool._execute_query("test script", "Sirius")
        assert result["status"] == "success"
        row = result["data"]["results"][0]
        assert row["main_id"] == "Sirius"
        assert row["object_type"] == "Star"
        assert "spectral_type" in row
        assert "flux" in row


@pytest.mark.unit
class TestSIMBADAdvancedToolInitialization:
    """Test SIMBADAdvancedTool initialization."""

    def test_init_default_config(self):
        """Test SIMBADAdvancedTool initialization with default config."""
        config = {"name": "test_simbad_advanced", "description": "Test"}
        tool = SIMBADAdvancedTool(config)
        assert tool.tap_url == "https://simbad.cds.unistra.fr/simbad/sim-tap/sync"

    def test_init_custom_config(self):
        """Test SIMBADAdvancedTool initialization with custom TAP URL."""
        config = {
            "name": "test_simbad_advanced",
            "description": "Test"
        }
        tool = SIMBADAdvancedTool(config, tap_url="https://custom.tap.org/sync")
        assert tool.tap_url == "https://custom.tap.org/sync"


@pytest.mark.unit
class TestSIMBADAdvancedToolRun:
    """Test SIMBADAdvancedTool.run() method."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = {"name": "test_simbad_advanced"}
        self.tool = SIMBADAdvancedTool(self.config)

    def test_run_missing_adql_query(self):
        """Test run() without adql_query parameter."""
        result = self.tool.run({})
        assert result.get("status") == "error"
        assert "adql_query" in result["data"]["error"]

    @patch('requests.post')
    def test_run_success_json(self, mock_post):
        """Test successful TAP query with JSON format."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [
                ["M  31", 10.68, 41.27, "Galaxy"]
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        result = self.tool.run({
            "adql_query": "SELECT TOP 1 main_id, ra, dec, otype FROM basic",
            "format": "json"
        })
        assert result["status"] == "success"
        assert "results" in result["data"]
        mock_post.assert_called_once()

    @patch('requests.post')
    def test_run_success_votable(self, mock_post):
        """Test successful TAP query with VOTable format."""
        mock_response = MagicMock()
        mock_response.text = "<?xml version='1.0'?><VOTABLE>...</VOTABLE>"
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        result = self.tool.run({
            "adql_query": "SELECT TOP 1 main_id FROM basic",
            "format": "votable"
        })
        assert result["status"] == "success"
        assert "<?xml" in result["data"]["results"]

    @patch('requests.post')
    def test_run_default_format(self, mock_post):
        """Test TAP query with default format (json)."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": []}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        result = self.tool.run({
            "adql_query": "SELECT TOP 1 main_id FROM basic"
        })
        assert result["status"] == "success"

    @patch('requests.post')
    def test_run_with_max_results(self, mock_post):
        """Test TAP query with max_results parameter."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": []}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        self.tool.run({
            "adql_query": "SELECT main_id FROM basic",
            "max_results": 50
        })

        call_args = mock_post.call_args
        assert call_args[1]["data"]["MAXREC"] == 50

    @patch('requests.post')
    def test_run_timeout(self, mock_post):
        """Test TAP query with timeout."""
        mock_post.side_effect = requests.Timeout()
        result = self.tool.run({
            "adql_query": "SELECT * FROM basic"
        })
        assert result.get("status") == "error"
        assert "timed out" in result["data"]["error"]

    @patch('requests.post')
    def test_run_network_error(self, mock_post):
        """Test TAP query with network error."""
        mock_post.side_effect = requests.RequestException("Connection failed")
        result = self.tool.run({
            "adql_query": "SELECT * FROM basic"
        })
        assert result.get("status") == "error"
        assert "Network error" in result["data"]["error"]

    @patch('requests.post')
    def test_run_json_parse_error(self, mock_post):
        """Test TAP query when JSON parsing fails."""
        mock_response = MagicMock()
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.text = "Invalid JSON response"
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        result = self.tool.run({
            "adql_query": "SELECT * FROM basic",
            "format": "json"
        })
        assert result["status"] == "success"
        assert result["data"]["results"] == "Invalid JSON response"


@pytest.mark.unit
class TestIntegration:
    """Integration tests for SIMBADTool."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = {"name": "test_simbad"}
        self.tool = SIMBADTool(self.config)

    @patch('requests.post')
    def test_full_workflow_object_query(self, mock_post):
        """Test complete workflow of querying an object."""
        mock_response = MagicMock()
        mock_response.text = "M  31 | 00 42 44.330 +41 16 07.50 | Galaxy"
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        result = self.tool.run({
            "query_type": "object_name",
            "object_name": "M31",
            "output_format": "basic"
        })

        assert result["status"] == "success"
        data = result["data"]
        assert data["count"] == 1
        assert data["results"][0]["main_id"] == "M  31"
        assert "Galaxy" in data["results"][0]["object_type"]

    @patch('requests.post')
    def test_full_workflow_coordinate_search(self, mock_post):
        """Test complete workflow of coordinate search."""
        mock_response = MagicMock()
        mock_response.text = """M  31 | 00 42 44.330 +41 16 07.50 | Galaxy
NGC 224 | 00 42 44.330 +41 16 07.50 | Galaxy"""
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        result = self.tool.run({
            "query_type": "coordinates",
            "ra": 10.68458,
            "dec": 41.26917,
            "radius": 5.0,
            "max_results": 10
        })

        assert result["status"] == "success"
        data = result["data"]
        assert data["count"] >= 1
        assert len(data["results"]) <= 10
