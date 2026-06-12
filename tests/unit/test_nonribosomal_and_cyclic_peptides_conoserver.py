"""Offline unit tests for the ConoServer conopeptide tools.

The real source is a ~10 MB not-well-formed XML export, so these tests mock the
HTTP download with a tiny gzipped fixture that deliberately contains an HTML
named entity (``&alpha;``) and a control character to exercise the sanitizer.
"""

import gzip
from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.conoserver_tool import (
    ConoServerGetConopeptideTool,
    ConoServerSearchConopeptidesTool,
    _load_entries,
    _sanitize_xml,
)

pytestmark = pytest.mark.unit

# Fixture XML: includes &alpha; (undefined in XML) and a \x16 control char.
_FIXTURE = (
    '<?xml version="1.0"?>\n'
    '<conoserver database="protein">\n'
    "<entry type=\"protein\">\n"
    "<id>P00001</id><name>SI\x16</name>\n"
    "<alternativeNames><altName>S1</altName></alternativeNames>\n"
    "<class>conotoxin</class>\n"
    "<geneSuperfamily>A superfamily</geneSuperfamily>\n"
    "<cysteineFramewrok>I</cysteineFramewrok>\n"
    "<pharmacologicalFamily>alpha conotoxin</pharmacologicalFamily>\n"
    "<organismLatin>Conus striatus</organismLatin>\n"
    "<sequence>ICCNPACGPKYSCX</sequence>\n"
    '<sequenceModifications><modification position="14" symbol="nh2" '
    'name="C-term amidation"/></sequenceModifications>\n'
    "<monoisotopicMass>1352.51</monoisotopicMass>\n"
    "<reference><authors>Benie et al.</authors><year>2000</year>"
    "<title>Solution structure of &alpha;-conotoxin SI</title>"
    "<pmid>10913630</pmid></reference>\n"
    "</entry>\n"
    "<entry type=\"protein\">\n"
    "<id>P00022</id><name>GVIA</name>\n"
    "<class>conotoxin</class>\n"
    "<pharmacologicalFamily>omega conotoxin</pharmacologicalFamily>\n"
    "<organismLatin>Conus geographus</organismLatin>\n"
    "<sequence>CKSOGSSCSOTSYNCCRSCNOYTKRCY</sequence>\n"
    "</entry>\n"
    "</conoserver>\n"
)


def _mock_get(*_args, **_kwargs):
    resp = MagicMock()
    resp.content = gzip.compress(_FIXTURE.encode("utf-8"))
    resp.raise_for_status = lambda: None
    return resp


@pytest.fixture(autouse=True)
def _clear_cache():
    """Reset the lru_cache so each test loads the fixture fresh."""
    _load_entries.cache_clear()
    yield
    _load_entries.cache_clear()


def test_sanitize_converts_named_entity_and_strips_control():
    """&alpha; becomes a unicode char and control characters are removed."""
    out = _sanitize_xml("a &alpha; b\x16c &amp; d")
    assert "α" in out  # alpha
    assert "\x16" not in out
    assert "&amp;" in out  # predefined XML entity preserved


def test_get_success():
    """A known ID returns the full parsed record."""
    with patch("tooluniverse.conoserver_tool.requests.get", _mock_get):
        out = ConoServerGetConopeptideTool({}).run({"conoserver_id": "P00001"})
    assert out["status"] == "success"
    data = out["data"]
    assert data["id"] == "P00001"
    assert data["sequence"] == "ICCNPACGPKYSCX"
    assert data["pharmacological_family"] == "alpha conotoxin"
    assert data["sequence_modifications"][0]["symbol"] == "nh2"
    assert data["references"][0]["pmid"] == "10913630"
    # the &alpha; entity in the reference title was converted to unicode alpha
    assert "α" in data["references"][0]["title"]


def test_get_is_case_insensitive():
    """Lower-case IDs resolve to the same record."""
    with patch("tooluniverse.conoserver_tool.requests.get", _mock_get):
        out = ConoServerGetConopeptideTool({}).run({"conoserver_id": "p00022"})
    assert out["status"] == "success"
    assert out["data"]["name"] == "GVIA"


def test_get_missing_arg():
    """Omitting the ID returns an error envelope without a network call."""
    out = ConoServerGetConopeptideTool({}).run({})
    assert out["status"] == "error"
    assert "conoserver_id" in out["error"]


def test_get_not_found():
    """An unknown ID yields a clean not-found error."""
    with patch("tooluniverse.conoserver_tool.requests.get", _mock_get):
        out = ConoServerGetConopeptideTool({}).run({"conoserver_id": "ZZZ999"})
    assert out["status"] == "error"
    assert "No ConoServer conopeptide" in out["error"]


def test_search_by_organism():
    """Organism filter matches on the Latin species name."""
    with patch("tooluniverse.conoserver_tool.requests.get", _mock_get):
        out = ConoServerSearchConopeptidesTool({}).run(
            {"organism": "Conus geographus"}
        )
    assert out["status"] == "success"
    assert out["data"]["count"] == 1
    assert out["data"]["results"][0]["id"] == "P00022"


def test_search_multiple_filters_are_anded():
    """Two filters must both match for a record to be returned."""
    with patch("tooluniverse.conoserver_tool.requests.get", _mock_get):
        out = ConoServerSearchConopeptidesTool({}).run(
            {"pharmacological_family": "alpha conotoxin", "organism": "striatus"}
        )
    assert out["status"] == "success"
    assert out["data"]["count"] == 1
    assert out["data"]["results"][0]["id"] == "P00001"


def test_search_no_filter_errors():
    """A search with no filters errors before any network call."""
    out = ConoServerSearchConopeptidesTool({}).run({})
    assert out["status"] == "error"
    assert "at least one filter" in out["error"]


def test_search_limit_clamped():
    """The limit is clamped into [1, 200]."""
    with patch("tooluniverse.conoserver_tool.requests.get", _mock_get):
        out = ConoServerSearchConopeptidesTool({}).run(
            {"class": "conotoxin", "conopeptide_class": "conotoxin", "limit": 9999}
        )
    assert out["status"] == "success"
    assert out["metadata"]["limit"] == 200


def test_network_failure_returns_error():
    """A raised HTTP error is caught and returned as an error envelope."""

    def _boom(*_a, **_k):
        resp = MagicMock()
        resp.raise_for_status = MagicMock(side_effect=RuntimeError("503"))
        return resp

    with patch("tooluniverse.conoserver_tool.requests.get", _boom):
        out = ConoServerGetConopeptideTool({}).run({"conoserver_id": "P00001"})
    assert out["status"] == "error"
    assert "Failed to load ConoServer data" in out["error"]
