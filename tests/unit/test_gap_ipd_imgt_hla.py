"""Unit tests for IPDIMGTHLATool (IPD-IMGT/HLA database wrapper).

All HTTP is mocked -- these tests do not hit the live EMBL-EBI API. They cover:
- filter-DSL construction (startsWith/contains/eq, quoting)
- parsing of the data[] list for allele search
- allele detail fetch (success)
- empty search results and 404 not-found handling
- the network-error path
- run() dispatch by tool config name substring
"""

import requests
from unittest.mock import patch, MagicMock

from tooluniverse.ipd_imgt_hla_tool import IPDIMGTHLATool


def _make_tool(name):
    return IPDIMGTHLATool({"name": name, "type": "IPDIMGTHLATool"})


def _mock_response(status_code=200, json_data=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data if json_data is not None else {}
    resp.raise_for_status.return_value = None
    return resp


# ---------------------------------------------------------------------------
# Filter-DSL construction
# ---------------------------------------------------------------------------
def test_build_filter_startswith():
    assert (
        IPDIMGTHLATool._build_filter("name", "A*01:01", "startsWith")
        == 'startsWith(name,"A*01:01")'
    )


def test_build_filter_contains_and_eq():
    assert IPDIMGTHLATool._build_filter("name", "A*01", "contains") == 'contains(name,"A*01")'
    assert IPDIMGTHLATool._build_filter("name", "A*01:01:01:01", "eq") == 'eq(name,"A*01:01:01:01")'


def test_build_filter_invalid_mode_falls_back_to_startswith():
    assert (
        IPDIMGTHLATool._build_filter("name", "B*07", "bogus")
        == 'startsWith(name,"B*07")'
    )


def test_build_filter_strips_embedded_quotes():
    assert (
        IPDIMGTHLATool._build_filter("name", 'A*0"1', "eq") == 'eq(name,"A*01")'
    )


# ---------------------------------------------------------------------------
# Allele search: parse data[]
# ---------------------------------------------------------------------------
def test_search_alleles_parses_data():
    tool = _make_tool("IPD_search_hla_alleles")
    payload = {
        "data": [
            {"accession": "HLA00001", "name": "A*01:01:01:01"},
            {"accession": "HLA01244", "name": "A*01:01:02"},
        ],
        "meta": {"total": 300},
    }
    with patch("tooluniverse.ipd_imgt_hla_tool.requests.get") as mock_get:
        mock_get.return_value = _mock_response(json_data=payload)
        result = tool.run({"name": "A*01:01", "limit": 2})

    assert result["status"] == "success"
    assert result["data"]["count"] == 2
    assert result["data"]["total"] == 300
    assert result["data"]["alleles"][0] == {
        "accession": "HLA00001",
        "name": "A*01:01:01:01",
    }
    # filter DSL passed to the API
    _, kwargs = mock_get.call_args
    assert kwargs["params"]["query"] == 'startsWith(name,"A*01:01")'
    assert kwargs["params"]["limit"] == 2


def test_search_alleles_match_mode_forwarded():
    tool = _make_tool("IPD_search_hla_alleles")
    with patch("tooluniverse.ipd_imgt_hla_tool.requests.get") as mock_get:
        mock_get.return_value = _mock_response(json_data={"data": [], "meta": {}})
        tool.run({"name": "A*01", "match": "contains"})
    _, kwargs = mock_get.call_args
    assert kwargs["params"]["query"] == 'contains(name,"A*01")'


def test_search_alleles_empty_results():
    tool = _make_tool("IPD_search_hla_alleles")
    with patch("tooluniverse.ipd_imgt_hla_tool.requests.get") as mock_get:
        mock_get.return_value = _mock_response(
            json_data={"data": [], "meta": {"total": 0}}
        )
        result = tool.run({"name": "ZZZ*99"})
    assert result["status"] == "success"
    assert result["data"]["count"] == 0
    assert result["data"]["alleles"] == []


def test_search_alleles_requires_name():
    tool = _make_tool("IPD_search_hla_alleles")
    result = tool.run({})
    assert result["status"] == "error"
    assert "name" in result["error"]


def test_search_alleles_invalid_match_mode_errors():
    tool = _make_tool("IPD_search_hla_alleles")
    result = tool.run({"name": "A*01", "match": "bogus"})
    assert result["status"] == "error"
    assert "match" in result["error"].lower()


def test_search_alleles_limit_clamped():
    tool = _make_tool("IPD_search_hla_alleles")
    with patch("tooluniverse.ipd_imgt_hla_tool.requests.get") as mock_get:
        mock_get.return_value = _mock_response(json_data={"data": [], "meta": {}})
        tool.run({"name": "A*01", "limit": 9999})
    _, kwargs = mock_get.call_args
    assert kwargs["params"]["limit"] == 100


# ---------------------------------------------------------------------------
# Allele detail fetch
# ---------------------------------------------------------------------------
def test_get_allele_success():
    tool = _make_tool("IPD_get_hla_allele")
    detail = {
        "accession": "HLA00001",
        "name": "A*01:01:01:01",
        "locus": "HLA-A",
        "class": "I",
    }
    with patch("tooluniverse.ipd_imgt_hla_tool.requests.get") as mock_get:
        mock_get.return_value = _mock_response(json_data=detail)
        result = tool.run({"accession": "HLA00001"})

    assert result["status"] == "success"
    assert result["data"]["accession"] == "HLA00001"
    assert result["data"]["locus"] == "HLA-A"
    # endpoint built from accession
    args, _ = mock_get.call_args
    assert args[0].endswith("/allele/HLA00001")


def test_get_allele_404_not_found():
    tool = _make_tool("IPD_get_hla_allele")
    with patch("tooluniverse.ipd_imgt_hla_tool.requests.get") as mock_get:
        mock_get.return_value = _mock_response(
            status_code=404, json_data={"code": 404, "message": "does not exist"}
        )
        result = tool.run({"accession": "HLA99999999"})
    assert result["status"] == "error"
    assert "HLA99999999" in result["error"]


def test_get_allele_requires_accession():
    tool = _make_tool("IPD_get_hla_allele")
    result = tool.run({})
    assert result["status"] == "error"
    assert "accession" in result["error"]


# ---------------------------------------------------------------------------
# Cell search
# ---------------------------------------------------------------------------
def test_search_cells_success():
    tool = _make_tool("IPD_search_cells")
    payload = {
        "data": [
            {"cellid": "10001", "primary_name": "10839496"},
        ],
        "meta": {"total": 1},
    }
    with patch("tooluniverse.ipd_imgt_hla_tool.requests.get") as mock_get:
        mock_get.return_value = _mock_response(json_data=payload)
        result = tool.run({"query": "10839496", "match": "eq"})

    assert result["status"] == "success"
    assert result["data"]["count"] == 1
    assert result["data"]["cells"][0]["cellid"] == "10001"
    _, kwargs = mock_get.call_args
    assert kwargs["params"]["query"] == 'eq(primary_name,"10839496")'


def test_search_cells_custom_field():
    tool = _make_tool("IPD_search_cells")
    with patch("tooluniverse.ipd_imgt_hla_tool.requests.get") as mock_get:
        mock_get.return_value = _mock_response(json_data={"data": [], "meta": {}})
        tool.run({"query": "Roche", "field": "lab_of_origin"})
    _, kwargs = mock_get.call_args
    assert kwargs["params"]["query"] == 'contains(lab_of_origin,"Roche")'


def test_search_cells_requires_query():
    tool = _make_tool("IPD_search_cells")
    result = tool.run({})
    assert result["status"] == "error"
    assert "query" in result["error"]


# ---------------------------------------------------------------------------
# Error paths and dispatch
# ---------------------------------------------------------------------------
def test_network_error_returns_error_envelope():
    tool = _make_tool("IPD_search_hla_alleles")
    with patch("tooluniverse.ipd_imgt_hla_tool.requests.get") as mock_get:
        mock_get.side_effect = requests.exceptions.ConnectionError("boom")
        result = tool.run({"name": "A*01:01"})
    assert result["status"] == "error"
    assert "Failed to query" in result["error"]


def test_unknown_operation():
    tool = _make_tool("IPD_something_else")
    result = tool.run({"name": "A*01"})
    assert result["status"] == "error"
    assert "Unknown operation" in result["error"]


def test_run_handles_none_arguments():
    tool = _make_tool("IPD_search_hla_alleles")
    result = tool.run(None)
    assert result["status"] == "error"
    assert "name" in result["error"]
