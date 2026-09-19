"""
Unit tests for the EPA CompTox / CCTE API tool.

Every CompTox endpoint requires an API key via the "x-api-key" header, so
these tests mock the HTTP layer rather than hitting the live API,
following the same pattern used for other key-gated tools in this repo
(see test_protocolsio_tool.py).
"""

import json
from unittest.mock import MagicMock, patch

import pytest


def _load_tool(name):
    with open("src/tooluniverse/data/comptox_tools.json") as f:
        tools = json.load(f)
    return next(t for t in tools if t["name"] == name)


@pytest.fixture
def search_config():
    return _load_tool("CompTox_search_chemical")


@pytest.fixture
def detail_config():
    return _load_tool("CompTox_get_chemical_detail")


@pytest.fixture
def hazard_config():
    return _load_tool("CompTox_get_hazard_data")


@pytest.fixture
def bio_summary_config():
    return _load_tool("CompTox_get_bioactivity_summary")


@pytest.fixture
def bio_assays_config():
    return _load_tool("CompTox_get_bioactivity_assays")


def _ok_response(body):
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = body
    resp.raise_for_status.return_value = None
    return resp


def _status_response(status_code, body=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = body or {}
    resp.raise_for_status.return_value = None
    return resp


class TestMissingApiKey:
    def test_run_without_key_returns_clean_error(self, search_config):
        from tooluniverse.comptox_tool import CompToxTool

        tool = CompToxTool(search_config, api_key=None)
        result = tool.run({"operation": "search_chemical", "word": "aspirin"})
        assert result["status"] == "error"
        assert "EPA_COMPTOX_API_KEY" in result["error"]

    def test_key_resolved_from_environment_at_construction(self, search_config):
        from tooluniverse.comptox_tool import CompToxTool

        with patch.dict("os.environ", {"EPA_COMPTOX_API_KEY": "env-key"}, clear=False):
            tool = CompToxTool(search_config)
        assert tool.api_key == "env-key"


class TestMissingOperation:
    def test_missing_operation_is_an_error_not_a_crash(self, search_config):
        from tooluniverse.comptox_tool import CompToxTool

        tool = CompToxTool(search_config, api_key="test-key")
        result = tool.run({})
        assert result["status"] == "error"
        assert "operation" in result["error"]

    def test_unknown_operation_is_an_error(self, search_config):
        from tooluniverse.comptox_tool import CompToxTool

        tool = CompToxTool(search_config, api_key="test-key")
        result = tool.run({"operation": "not_a_real_operation"})
        assert result["status"] == "error"
        assert "Unknown operation" in result["error"]


class TestSearchChemical:
    def test_missing_word_is_an_error(self, search_config):
        from tooluniverse.comptox_tool import CompToxTool

        tool = CompToxTool(search_config, api_key="test-key")
        result = tool.run({"operation": "search_chemical"})
        assert result["status"] == "error"
        assert "word" in result["error"]

    def test_invalid_match_type_is_an_error(self, search_config):
        from tooluniverse.comptox_tool import CompToxTool

        tool = CompToxTool(search_config, api_key="test-key")
        result = tool.run(
            {"operation": "search_chemical", "word": "aspirin", "match_type": "fuzzy"}
        )
        assert result["status"] == "error"
        assert "match_type" in result["error"]

    def test_successful_search_returns_results(self, search_config):
        from tooluniverse.comptox_tool import CompToxTool

        tool = CompToxTool(search_config, api_key="test-key")
        body = [
            {
                "searchName": "aspirin",
                "preferredName": "Aspirin",
                "dtxsid": "DTXSID5020108",
                "casrn": "50-78-2",
            }
        ]
        with patch("requests.get", return_value=_ok_response(body)) as mock_get:
            result = tool.run({"operation": "search_chemical", "word": "aspirin"})
        assert result["status"] == "success"
        assert result["data"]["results"][0]["dtxsid"] == "DTXSID5020108"
        assert result["data"]["result_count"] == 1
        called_url = mock_get.call_args[0][0]
        assert "/chemical/search/equal/aspirin" in called_url
        assert mock_get.call_args[1]["headers"]["x-api-key"] == "test-key"

    def test_auth_failure_returns_actionable_hint(self, search_config):
        from tooluniverse.comptox_tool import CompToxTool

        tool = CompToxTool(search_config, api_key="stale-key")
        with patch("requests.get", return_value=_status_response(401)):
            result = tool.run({"operation": "search_chemical", "word": "aspirin"})
        assert result["status"] == "error"
        assert "EPA_COMPTOX_API_KEY" in result["error"]


class TestGetChemicalDetail:
    def test_missing_dtxsid_is_an_error(self, detail_config):
        from tooluniverse.comptox_tool import CompToxTool

        tool = CompToxTool(detail_config, api_key="test-key")
        result = tool.run({"operation": "get_chemical_detail"})
        assert result["status"] == "error"
        assert "dtxsid" in result["error"]

    def test_not_found_returns_clean_error(self, detail_config):
        from tooluniverse.comptox_tool import CompToxTool

        tool = CompToxTool(detail_config, api_key="test-key")
        with patch("requests.get", return_value=_status_response(404)):
            result = tool.run(
                {"operation": "get_chemical_detail", "dtxsid": "DTXSID_NOT_REAL"}
            )
        assert result["status"] == "error"
        assert "no comptox record" in result["error"].lower()

    def test_successful_detail_lookup(self, detail_config):
        from tooluniverse.comptox_tool import CompToxTool

        tool = CompToxTool(detail_config, api_key="test-key")
        body = {
            "preferredName": "Aspirin",
            "dtxsid": "DTXSID5020108",
            "molFormula": "C9H8O4",
            "totalAssays": 821,
            "activeAssays": 63,
        }
        with patch("requests.get", return_value=_ok_response(body)):
            result = tool.run(
                {"operation": "get_chemical_detail", "dtxsid": "DTXSID5020108"}
            )
        assert result["status"] == "success"
        assert result["data"]["molFormula"] == "C9H8O4"


class TestGetHazardData:
    def test_missing_dtxsid_is_an_error(self, hazard_config):
        from tooluniverse.comptox_tool import CompToxTool

        tool = CompToxTool(hazard_config, api_key="test-key")
        result = tool.run({"operation": "get_hazard_data"})
        assert result["status"] == "error"
        assert "dtxsid" in result["error"]

    def test_successful_hazard_lookup(self, hazard_config):
        from tooluniverse.comptox_tool import CompToxTool

        tool = CompToxTool(hazard_config, api_key="test-key")
        body = [
            {
                "dtxsid": "DTXSID5020108",
                "toxvalType": "LD50",
                "toxvalNumeric": 200.0,
                "toxvalUnits": "mg/kg",
            }
        ]
        with patch("requests.get", return_value=_ok_response(body)):
            result = tool.run(
                {"operation": "get_hazard_data", "dtxsid": "DTXSID5020108"}
            )
        assert result["status"] == "success"
        assert result["data"]["record_count"] == 1
        assert result["data"]["toxval_records"][0]["toxvalType"] == "LD50"


class TestGetBioactivitySummary:
    def test_missing_dtxsid_is_an_error(self, bio_summary_config):
        from tooluniverse.comptox_tool import CompToxTool

        tool = CompToxTool(bio_summary_config, api_key="test-key")
        result = tool.run({"operation": "get_bioactivity_summary"})
        assert result["status"] == "error"
        assert "dtxsid" in result["error"]

    def test_successful_summary_lookup(self, bio_summary_config):
        from tooluniverse.comptox_tool import CompToxTool

        tool = CompToxTool(bio_summary_config, api_key="test-key")
        body = {
            "dtxsid": "DTXSID5020108",
            "activeMc": 12,
            "totalMc": 300,
            "ntested": 700,
            "nhit": 12,
        }
        with patch("requests.get", return_value=_ok_response(body)):
            result = tool.run(
                {"operation": "get_bioactivity_summary", "dtxsid": "DTXSID5020108"}
            )
        assert result["status"] == "success"
        assert result["data"]["activeMc"] == 12


class TestGetBioactivityAssays:
    def test_missing_dtxsid_is_an_error(self, bio_assays_config):
        from tooluniverse.comptox_tool import CompToxTool

        tool = CompToxTool(bio_assays_config, api_key="test-key")
        result = tool.run({"operation": "get_bioactivity_assays"})
        assert result["status"] == "error"
        assert "dtxsid" in result["error"]

    def test_successful_assay_lookup(self, bio_assays_config):
        from tooluniverse.comptox_tool import CompToxTool

        tool = CompToxTool(bio_assays_config, api_key="test-key")
        body = [
            {"dtxsid": "DTXSID5020108", "aeid": 42, "hitCall": 1.0, "ac50": 15.2}
        ]
        with patch("requests.get", return_value=_ok_response(body)):
            result = tool.run(
                {"operation": "get_bioactivity_assays", "dtxsid": "DTXSID5020108"}
            )
        assert result["status"] == "success"
        assert result["data"]["record_count"] == 1
        assert result["data"]["assay_records"][0]["aeid"] == 42
