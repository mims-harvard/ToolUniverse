"""Regression tests for WoRMS_search_species paging.

The search used to hard-code ``data[:5]``: the declared ``limit`` parameter was
ignored entirely, and ``total_found`` reported the size of the single upstream
page (WoRMS caps every AphiaRecordsByName response at 50 records) rather than
the size of the result set. A search for "Gadus" returned 5 records and claimed
``total_found: 50`` when 129 records actually match.
"""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.worms_tool import WoRMSRESTTool


SEARCH_CONFIG = {
    "type": "WoRMSRESTTool",
    "name": "WoRMS_search_species",
    "description": "Search marine species in WoRMS",
    "parameter": {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "limit": {"type": "integer"},
            "offset": {"type": "integer"},
        },
        "required": ["query"],
    },
    "fields": {"return_format": "JSON"},
}


def _record(i):
    return {"AphiaID": 1000 + i, "scientificname": f"Gadus species{i}"}


def _fake_session(total_records):
    """Session whose AphiaRecordsByName pages 50 records at a time like WoRMS."""
    records = [_record(i) for i in range(total_records)]

    def get(url, timeout=None):
        offset = 1
        if "offset=" in url:
            offset = int(url.split("offset=")[1].split("&")[0])
        page = records[offset - 1 : offset - 1 + WoRMSRESTTool._PAGE_SIZE]
        response = MagicMock()
        if not page:
            response.status_code = 204
            response.text = ""
            response.json.return_value = []
            return response
        response.status_code = 200
        response.text = "[...]"
        response.json.return_value = page
        return response

    session = MagicMock()
    session.get.side_effect = get
    return session


def _run(arguments, total_records=129):
    tool = WoRMSRESTTool(dict(SEARCH_CONFIG))
    tool.session = _fake_session(total_records)
    return tool.run(arguments)


@pytest.mark.parametrize("limit", [3, 25, 60])
def test_limit_is_honored(limit):
    """The declared limit drives the page size instead of a hard-coded 5."""
    result = _run({"query": "Gadus", "limit": limit})
    assert result["status"] == "success"
    assert result["count"] == limit
    assert len(result["data"]) == limit
    assert result["has_more"] is True


def test_limit_spans_upstream_page_boundary():
    """A limit above the 50-record upstream page size assembles several pages."""
    result = _run({"query": "Gadus", "limit": 60})
    assert len(result["data"]) == 60
    # Distinct records, not the first page repeated.
    assert len({r["AphiaID"] for r in result["data"]}) == 60


def test_full_result_set_is_reachable():
    """A large limit returns every match, not the first upstream page of 50."""
    result = _run({"query": "Gadus", "limit": 500})
    assert result["count"] == 129
    assert result["has_more"] is False


def test_offset_pages_to_the_tail():
    result = _run({"query": "Gadus", "limit": 50, "offset": 101})
    assert result["count"] == 29
    assert result["has_more"] is False
    assert result["offset"] == 101


def test_default_limit_is_twenty_not_five():
    result = _run({"query": "Gadus"})
    assert result["count"] == 20
    assert result["limit"] == 20


def test_no_stale_total_found_field():
    """The old `total_found` reported the upstream page size, so it is gone."""
    result = _run({"query": "Gadus", "limit": 5})
    assert "total_found" not in result


def test_exact_limit_at_end_reports_no_more():
    result = _run({"query": "Gadus", "limit": 129})
    assert result["count"] == 129
    assert result["has_more"] is False


def test_empty_result_set():
    result = _run({"query": "Zzzz"}, total_records=0)
    assert result["status"] == "success"
    assert result["data"] == []
    assert result["count"] == 0
    assert result["has_more"] is False


def test_non_integer_limit_is_reported_as_error():
    result = _run({"query": "Gadus", "limit": "abc"})
    assert result["status"] == "error"
    assert "integer" in result["error"]


def test_zero_limit_is_rejected():
    result = _run({"query": "Gadus", "limit": 0})
    assert result["status"] == "error"


def test_upstream_failure_surfaces_as_error():
    tool = WoRMSRESTTool(dict(SEARCH_CONFIG))
    session = MagicMock()
    session.get.side_effect = RuntimeError("boom")
    tool.session = session
    result = tool.run({"query": "Gadus"})
    assert result["status"] == "error"
    assert "WoRMS API error" in result["error"]


def test_config_declares_offset_and_envelope_schema():
    """The shipped config must document `offset` and use a oneOf envelope."""
    import json
    from pathlib import Path

    path = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "tooluniverse"
        / "data"
        / "worms_tools.json"
    )
    tools = {t["name"]: t for t in json.loads(path.read_text())}
    search = tools["WoRMS_search_species"]
    assert "offset" in search["parameter"]["properties"]
    assert "oneOf" in search["return_schema"]
    # The endpoint recorded in the config must be the one the code actually calls.
    assert "AphiaRecordsByName" in search["fields"]["endpoint"]


def test_search_does_not_disturb_aphia_operations():
    """Enrichment operations keyed by AphiaID are unaffected by the paging change."""
    config = dict(SEARCH_CONFIG)
    config["fields"] = {"operation": "classification"}
    tool = WoRMSRESTTool(config)
    response = MagicMock()
    response.status_code = 200
    response.text = "{}"
    response.json.return_value = {"AphiaID": 126436, "rank": "Species"}
    session = MagicMock()
    session.get.return_value = response
    tool.session = session
    result = tool.run({"AphiaID": 126436})
    assert result["status"] == "success"
    assert result["data"]["rank"] == "Species"


def test_aphia_operation_requires_id():
    config = dict(SEARCH_CONFIG)
    config["fields"] = {"operation": "synonyms"}
    tool = WoRMSRESTTool(config)
    result = tool.run({})
    assert result["status"] == "error"
    assert "AphiaID" in result["error"]


@patch("tooluniverse.worms_tool.requests")
def test_search_requests_use_offset_query_parameter(_requests):
    """Paging must go through WoRMS's 1-based offset parameter."""
    tool = WoRMSRESTTool(dict(SEARCH_CONFIG))
    tool.session = _fake_session(129)
    tool.run({"query": "Gadus", "limit": 60})
    called = [c.args[0] for c in tool.session.get.call_args_list]
    assert any("offset=1" in u for u in called)
    assert any("offset=51" in u for u in called)
