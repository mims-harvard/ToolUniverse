"""Offline unit tests for the Norine non-ribosomal peptide tool."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from tooluniverse.norine_tool import NorineGetPeptideTool

pytestmark = pytest.mark.unit

_CONFIG_PATH = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "tooluniverse"
    / "data"
    / "norine_tools.json"
)

# Minimal name-route payload (top-level "peptides" list).
_NAME_PAYLOAD = {
    "peptides": [
        {
            "general": {
                "id": "NOR00298",
                "name": "tyrocidine A",
                "family": "tyrocidine",
                "category": "peptide",
                "formula": "C66H87N13O13",
                "mw": "1270.4763",
                "activity": ["antimicrobial"],
            },
            "structure": {
                "type": "cyclic",
                "size": 10,
                "composition": "D-Phe,Pro,Phe,D-Phe,Asn,Gln,Tyr,Val,Orn,Leu",
                "smiles": "CC(C)CC...",
            },
            "organism": [{"taxId": "1393", "nameOrga": "Bacillus brevis"}],
            "reference": [{"pmid": "9352938", "title": "tyrocidine operon"}],
        }
    ]
}

# Minimal id-route payload (nested under "norine"."peptide").
_ID_PAYLOAD = {
    "norine": {
        "peptide": [
            {
                "general": {
                    "id": "NOR00123",
                    "name": "[Dha7]MCYST-E(OMe)E(OMe)",
                    "family": "microcystin",
                    "category": "PK-NRP",
                    "formula": "C48H67N7O16",
                    "activity": ["toxin"],
                },
                "structure": {"type": "cyclic", "size": 7},
                "organism": [{"taxId": "1163", "nameOrga": "Anabaena"}],
                "reference": [{"pmid": "9511906"}],
            }
        ]
    }
}


class _FakeResponse:
    """Stand-in for a requests.Response with controllable JSON/status."""

    def __init__(self, payload, status_code=200, text=""):
        self._payload = payload
        self.status_code = status_code
        self.text = text
        self.url = "https://example.test/norine"

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload


def _tool():
    """Build the tool from its real JSON config."""
    config = json.loads(_CONFIG_PATH.read_text())[0]
    return NorineGetPeptideTool(config)


def test_name_route_success_parse():
    """Name lookup normalizes 'peptides' list and surfaces first-record meta."""
    tool = _tool()
    with patch(
        "tooluniverse.norine_tool.requests.get",
        return_value=_FakeResponse(_NAME_PAYLOAD),
    ):
        result = tool.run({"name": "tyrocidine"})
    assert result["status"] == "success"
    assert result["metadata"]["lookup_mode"] == "name"
    assert result["metadata"]["count"] == 1
    assert result["metadata"]["first_record"]["id"] == "NOR00298"
    assert result["data"]["peptides"][0]["structure"]["type"] == "cyclic"


def test_id_route_success_parse_unwraps_norine_peptide():
    """Id lookup unwraps 'norine.peptide' into the same 'peptides' list."""
    tool = _tool()
    with patch(
        "tooluniverse.norine_tool.requests.get",
        return_value=_FakeResponse(_ID_PAYLOAD),
    ) as mock_get:
        result = tool.run({"norine_id": "123"})
    # Id is zero-padded to 5 digits in the request URL.
    assert "/id/json/00123" in mock_get.call_args[0][0]
    assert result["status"] == "success"
    assert result["metadata"]["lookup_mode"] == "id"
    assert result["data"]["peptides"][0]["general"]["id"] == "NOR00123"


def test_empty_list_is_not_found_error():
    """An HTTP 200 with an empty list is reported as a not-found error."""
    tool = _tool()
    with patch(
        "tooluniverse.norine_tool.requests.get",
        return_value=_FakeResponse({"peptides": []}),
    ):
        result = tool.run({"name": "zzznotapeptidezzz"})
    assert result["status"] == "error"
    assert "No Norine peptide found" in result["error"]


def test_missing_arguments_error():
    """Calling with neither name nor norine_id returns an error, no request."""
    tool = _tool()
    with patch("tooluniverse.norine_tool.requests.get") as mock_get:
        result = tool.run({})
    mock_get.assert_not_called()
    assert result["status"] == "error"
    assert "required" in result["error"].lower()


def test_both_arguments_error():
    """Providing both name and norine_id returns an error without a request."""
    tool = _tool()
    with patch("tooluniverse.norine_tool.requests.get") as mock_get:
        result = tool.run({"name": "x", "norine_id": "1"})
    mock_get.assert_not_called()
    assert result["status"] == "error"
    assert "not both" in result["error"]


def test_non_json_response_error():
    """A non-JSON (HTML) body yields a clean error, never an exception."""
    tool = _tool()
    with patch(
        "tooluniverse.norine_tool.requests.get",
        return_value=_FakeResponse(None, status_code=200, text="<html>..."),
    ):
        result = tool.run({"norine_id": "00123"})
    assert result["status"] == "error"
    assert "non-JSON" in result["error"]


def test_http_error_status():
    """A non-200 HTTP status returns an error with the status code."""
    tool = _tool()
    with patch(
        "tooluniverse.norine_tool.requests.get",
        return_value=_FakeResponse(None, status_code=500, text="boom"),
    ):
        result = tool.run({"name": "tyrocidine"})
    assert result["status"] == "error"
    assert "HTTP 500" in result["error"]
