"""Regression guard for Fix-R73A-1: BRENDA_get_enzyme_kinetics'
_fetch_sabiork_kinetics called the legacy SABIO-RK REST endpoint
(/sabioRestWebServices/searchKineticLaws/entryIDs), retired by SABIO-RK in
2025 -- every request 302-redirects to a JS SPA 404 page (confirmed live via
raw curl). The old code's status_code-!=-200 and XML-ParseError checks
silently swallowed this as "0 entries, success" instead of surfacing a
failure -- confirmed live for EC 1.1.1.1 (alcohol dehydrogenase): reported 0
SABIO-RK entries when the real count is 768. This ports the same Solr-backed
endpoint (https://sabiork.h-its.org/api/ft/proxy-select) that
sabiork_tool.py's SABIORKTool already migrated to.

Fix-R14D-1's own failure-visibility tests (test_brenda_sabiork_failure_
visibility.py) mock _fetch_sabiork_kinetics at the method level and are
unaffected by this internal rewrite -- these tests instead exercise
_fetch_sabiork_kinetics itself, mocking the HTTP layer.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.brenda_tool import BRENDATool

pytestmark = pytest.mark.unit


def _tool():
    return BRENDATool({"name": "BRENDA_get_enzyme_kinetics"})


def _solr_response(num_found, docs):
    r = MagicMock()
    r.raise_for_status = MagicMock()
    r.json.return_value = {"response": {"numFound": num_found, "docs": docs}}
    return r


def test_fetches_via_solr_endpoint_not_legacy_rest():
    tool = _tool()
    with patch("tooluniverse.brenda_tool.requests.get") as mock_get:
        mock_get.return_value = _solr_response(0, [])
        tool._fetch_sabiork_kinetics("1.1.1.1")

    called_url = mock_get.call_args[0][0]
    assert called_url == "https://sabiork.h-its.org/api/ft/proxy-select"
    assert "sabioRestWebServices" not in called_url
    assert mock_get.call_args[1]["params"]["q"] == "ECNumber:1.1.1.1"


def test_real_entry_count_is_reported_not_zero():
    """The core confirmed-live symptom: a well-studied enzyme (EC 1.1.1.1)
    has hundreds of real SABIO-RK entries, not zero."""
    tool = _tool()
    docs = [
        {
            "EntryID": 3805,
            "ECNumber": ["1.1.1.1"],
            "EnzymeName": ["alcohol dehydrogenase"],
            "Organism": ["Saccharomyces cerevisiae"],
            "ParameterType": ["Km", "kcat"],
        }
    ]
    with patch("tooluniverse.brenda_tool.requests.get") as mock_get:
        mock_get.return_value = _solr_response(768, docs)
        result = tool._fetch_sabiork_kinetics("1.1.1.1")

    assert result["total_count"] == 768
    assert len(result["kinetic_laws"]) == 1
    law = result["kinetic_laws"][0]
    assert law["sabiork_entry_id"] == "3805"
    assert law["enzyme_name"] == "alcohol dehydrogenase"
    assert law["parameter_types"] == ["Km", "kcat"]


def test_organism_filter_included_in_query():
    tool = _tool()
    with patch("tooluniverse.brenda_tool.requests.get") as mock_get:
        mock_get.return_value = _solr_response(0, [])
        tool._fetch_sabiork_kinetics("1.1.1.1", organism="Homo sapiens")

    assert mock_get.call_args[1]["params"]["q"] == (
        'ECNumber:1.1.1.1 AND Organism:"Homo sapiens"'
    )


def test_non_200_response_raises_instead_of_silently_returning_zero():
    """The exact confirmed-live failure mode: a redirect-to-404 response.
    Must raise so the caller's existing sabiork_error mechanism (Fix-R14D-1)
    actually fires, instead of silently reporting 0 entries as success."""
    tool = _tool()
    with patch("tooluniverse.brenda_tool.requests.get") as mock_get:
        resp = MagicMock()
        resp.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "404 Client Error"
        )
        mock_get.return_value = resp

        with pytest.raises(requests.exceptions.HTTPError):
            tool._fetch_sabiork_kinetics("1.1.1.1")


def test_non_json_response_raises_instead_of_silently_returning_zero():
    tool = _tool()
    with patch("tooluniverse.brenda_tool.requests.get") as mock_get:
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.side_effect = ValueError("not JSON")
        mock_get.return_value = resp

        with pytest.raises(ValueError):
            tool._fetch_sabiork_kinetics("1.1.1.1")


def test_end_to_end_failure_now_reaches_sabiork_error(monkeypatch):
    """Combines this fix with Fix-R14D-1's existing mechanism: a raised
    exception from _fetch_sabiork_kinetics (now reachable, since the legacy
    silent-swallow paths are gone) must surface via metadata.sabiork_error,
    not silently report kinetic_parameters as an empty-but-successful list."""
    tool = _tool()
    monkeypatch.setattr(
        tool,
        "_fetch_expasy_enzyme",
        lambda ec: {
            "name": "alcohol dehydrogenase",
            "alternative_names": [],
            "catalytic_activity": [],
            "comments": [],
        },
    )
    with patch("tooluniverse.brenda_tool.requests.get") as mock_get:
        resp = MagicMock()
        resp.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "404 Client Error"
        )
        mock_get.return_value = resp

        result = tool._get_enzyme_kinetics({"ec_number": "1.1.1.1"})

    assert result["status"] == "success"
    assert result["data"]["kinetic_parameters"] == []
    assert result["data"]["sabiork_total_entries"] == 0
    assert "sabiork_error" in result["metadata"]
    assert "SABIO-RK" not in result["metadata"]["sources"]


def test_no_parameter_summary_fabricated_when_values_unavailable():
    """The new Solr endpoint doesn't expose raw numeric parameter values
    (confirmed live -- SABIORKTool's own "parameters" field is always
    empty too). parameter_summary must stay honestly absent, not be
    fabricated from empty data."""
    tool = _tool()
    monkeypatch_docs = [
        {
            "EntryID": 3805,
            "ECNumber": ["1.1.1.1"],
            "EnzymeName": ["alcohol dehydrogenase"],
            "ParameterType": ["Km", "kcat"],
        }
    ]
    with patch("tooluniverse.brenda_tool.requests.get") as mock_get, patch.object(
        BRENDATool,
        "_fetch_expasy_enzyme",
        return_value={
            "name": "alcohol dehydrogenase",
            "alternative_names": [],
            "catalytic_activity": [],
            "comments": [],
        },
    ):
        mock_get.return_value = _solr_response(768, monkeypatch_docs)
        result = tool._get_enzyme_kinetics({"ec_number": "1.1.1.1"})

    assert result["status"] == "success"
    assert "parameter_summary" not in result["data"]
    assert result["data"]["sabiork_total_entries"] == 768
