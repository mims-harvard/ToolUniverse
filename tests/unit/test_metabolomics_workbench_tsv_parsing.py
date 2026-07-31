"""Regression guard for Fix-R22B-2: MetabolomicsWorkbenchTool's fallback for
non-JSON responses returned one giant string with literal \\t/\\n characters
embedded, instead of parsed rows.

Confirmed live: the moverz/REFMET exact-mass search endpoint ignores the
requested "/json" URL suffix and returns plain tab-separated text. The old
`except ValueError: return {"status": "success", "data": response.text}`
fallback handed that raw TSV straight back, inconsistent with every sibling
endpoint in this tool family (which return real JSON objects/arrays) and
hard for a downstream consumer to parse. Fixed by adding a `_parse_tsv_text`
helper that converts a tab-delimited response body into a list of row
dicts before falling back to the raw string.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.metabolomics_workbench_tool import MetabolomicsWorkbenchTool

pytestmark = pytest.mark.unit

_TSV_BODY = (
    "Input m/z\tMatched m/z\tDelta\tName\tFormula\n"
    "386.354865\t386.3549\t.0000\t5alpha-Cholestanone\tC27H46O\n"
    "386.354865\t386.3549\t.0000\tCholesterol\tC27H46O\n"
)


def _tool(context):
    return MetabolomicsWorkbenchTool(
        {"name": "mw_test", "fields": {"context": context}}
    )


def _resp(text):
    r = MagicMock()
    r.raise_for_status = MagicMock()
    r.text = text
    r.json.side_effect = ValueError("not json")
    return r


def test_tsv_body_parsed_into_row_dicts():
    tool = _tool("exactmass")
    resp = _resp(_TSV_BODY)

    with patch("tooluniverse.metabolomics_workbench_tool.requests.get", return_value=resp):
        result = tool.run({"mass_value": 386.354865, "tolerance": 0.01})

    assert result["status"] == "success"
    assert isinstance(result["data"], list)
    assert len(result["data"]) == 2
    assert result["data"][0] == {
        "Input m/z": "386.354865",
        "Matched m/z": "386.3549",
        "Delta": ".0000",
        "Name": "5alpha-Cholestanone",
        "Formula": "C27H46O",
    }
    assert result["data"][1]["Name"] == "Cholesterol"


def test_non_tabular_text_falls_back_to_raw_string():
    """A genuinely non-tabular text response (no tab in the first line)
    still falls back to the raw string, not a spuriously "parsed" mess."""
    tool = _tool("exactmass")
    resp = _resp("Service temporarily unavailable, please try again later.")

    with patch("tooluniverse.metabolomics_workbench_tool.requests.get", return_value=resp):
        result = tool.run({"mass_value": 100.0})

    assert result["status"] == "success"
    assert result["data"] == "Service temporarily unavailable, please try again later."


def test_single_line_text_falls_back_to_raw_string():
    """A single line (header only, no data rows) isn't a real table --
    fall back rather than returning an empty/misleading parse."""
    tool = _tool("exactmass")
    resp = _resp("Input m/z\tMatched m/z\tName")

    with patch("tooluniverse.metabolomics_workbench_tool.requests.get", return_value=resp):
        result = tool.run({"mass_value": 100.0})

    assert result["status"] == "success"
    assert result["data"] == "Input m/z\tMatched m/z\tName"


def test_genuine_json_response_unaffected():
    tool = _tool("compound")
    resp = _resp('{"name": "Cholesterol", "pubchem_cid": "5997"}')
    resp.json.side_effect = None
    resp.json.return_value = {"name": "Cholesterol", "pubchem_cid": "5997"}

    with patch("tooluniverse.metabolomics_workbench_tool.requests.get", return_value=resp):
        result = tool.run({"input_value": "cholesterol"})

    assert result["status"] == "success"
    assert result["data"]["name"] == "Cholesterol"
