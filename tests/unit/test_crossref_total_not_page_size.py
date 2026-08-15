"""Regression tests: Crossref list searches must report the match total.

``CrossrefRESTTool._process_response`` extracted ``message["items"]`` and set
``count`` to ``len(items)`` while discarding ``message["total-results"]``, which
is the only number Crossref publishes for "how many works actually match". With
the documented ``limit`` defaults (10 for works, 20 for funders/members) that
made the page size look like the size of the result set. Confirmed live against
api.crossref.org:

* ``Crossref_search_works {"query": "CRISPR gene editing", "limit": 3}``
  reported ``count: 3``; ``message["total-results"]`` was 1037333.
* ``Crossref_search_members {"query": "university", "limit": 3}``
  reported ``count: 3``; the true member count is 4032.
* ``Crossref_list_funders {"query": "cancer", "limit": 3}``
  reported ``count: 3``; the true funder count is 746.

The detail endpoints (``/works/{doi}``, ``/members/{id}``, ...) return a
``message`` with no ``items`` and must be left exactly as they were.
"""

import json
from pathlib import Path

import pytest

from tooluniverse.crossref_tool import CrossrefRESTTool

pytestmark = pytest.mark.unit

CONFIG_PATH = (
    Path(__file__).parent.parent.parent / "src/tooluniverse/data/crossref_tools.json"
)
CONFIGS = {c["name"]: c for c in json.loads(CONFIG_PATH.read_text())}


class _FakeResponse:
    """Minimal stand-in for the requests.Response the tool receives."""

    def __init__(self, payload, url="https://api.crossref.org/works?query=x&rows=3"):
        self._payload = payload
        self.url = url

    def json(self):
        return self._payload


def _tool(name="Crossref_search_works"):
    return CrossrefRESTTool(dict(CONFIGS[name]))


def _list_payload(n_items, total, extra=None):
    message = {"items": [{"DOI": f"10.0/{i}"} for i in range(n_items)]}
    if total is not None:
        message["total-results"] = total
    if extra:
        message.update(extra)
    return {"message": message}


# ---------------------------------------------------------------------------
# The total must come from Crossref, not from the page
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("limit", [3, 10, 100])
def test_total_count_is_independent_of_page_size(limit):
    response = _FakeResponse(_list_payload(limit, 1037333))
    result = _tool()._process_response(response, "https://api.crossref.org/works")
    assert result["total_count"] == 1037333, "total must be Crossref's total-results"
    assert result["count"] == limit, "count must stay the page size"
    assert len(result["data"]) == limit


def test_truncation_note_names_the_total_and_the_next_offset():
    response = _FakeResponse(_list_payload(3, 1037333))
    result = _tool()._process_response(response, "https://api.crossref.org/works")
    note = result["note"]
    assert "1037333" in note
    assert "offset=3" in note


def test_no_note_when_the_page_is_the_whole_result_set():
    """/types returns all 30 rows; a truncation note there would be a lie."""
    response = _FakeResponse(
        _list_payload(30, 30), url="https://api.crossref.org/types"
    )
    result = _tool("Crossref_list_types")._process_response(
        response, "https://api.crossref.org/types"
    )
    assert result["total_count"] == 30
    assert result["count"] == 30
    assert "note" not in result


def test_no_note_on_the_last_page():
    response = _FakeResponse(
        _list_payload(2, 12), url="https://api.crossref.org/funders?rows=5&offset=10"
    )
    result = _tool("Crossref_list_funders")._process_response(
        response, "https://api.crossref.org/funders"
    )
    assert result["total_count"] == 12
    assert "note" not in result


def test_offset_is_read_from_the_requested_url():
    """The note must count from the caller's offset, not from zero."""
    response = _FakeResponse(
        _list_payload(3, 746), url="https://api.crossref.org/funders?rows=3&offset=6"
    )
    result = _tool("Crossref_list_funders")._process_response(
        response, "https://api.crossref.org/funders"
    )
    assert "7-9 of 746" in result["note"]
    assert "offset=9" in result["note"]


def test_offset_defaults_to_zero_when_absent_or_unparseable():
    for url in (
        "https://api.crossref.org/works",
        "https://api.crossref.org/works?offset=not-a-number",
    ):
        result = _tool()._process_response(_FakeResponse(_list_payload(3, 99), url), url)
        assert "1-3 of 99" in result["note"]


def test_missing_total_results_leaves_the_response_as_it_was():
    """Never invent a total: absent total-results means no total_count, no note."""
    response = _FakeResponse(_list_payload(3, None))
    result = _tool()._process_response(response, "https://api.crossref.org/works")
    assert "total_count" not in result
    assert "note" not in result
    assert result["count"] == 3


def test_non_integer_total_results_is_ignored():
    response = _FakeResponse(_list_payload(3, "many"))
    result = _tool()._process_response(response, "https://api.crossref.org/works")
    assert "total_count" not in result


def test_empty_result_set_reports_zero_and_no_note():
    response = _FakeResponse(_list_payload(0, 0))
    result = _tool()._process_response(response, "https://api.crossref.org/works")
    assert result["count"] == 0
    assert result["total_count"] == 0
    assert "note" not in result


# ---------------------------------------------------------------------------
# The endpoints that were already correct must not move
# ---------------------------------------------------------------------------


def test_detail_endpoint_response_is_unchanged():
    """A `message` with no `items` is a single record: no count, no total."""
    payload = {"message": {"DOI": "10.1038/nature12373", "title": ["Something"]}}
    result = _tool("Crossref_get_work")._process_response(
        _FakeResponse(payload, "https://api.crossref.org/works/10.1038%2Fnature12373"),
        "https://api.crossref.org/works/10.1038%2Fnature12373",
    )
    assert result == {
        "status": "success",
        "data": payload["message"],
        "url": "https://api.crossref.org/works/10.1038%2Fnature12373",
    }


def test_payload_without_message_wrapper_is_unchanged():
    payload = {"anything": 1}
    result = _tool()._process_response(
        _FakeResponse(payload), "https://api.crossref.org/works"
    )
    assert result == {
        "status": "success",
        "data": payload,
        "url": "https://api.crossref.org/works",
    }


def test_limit_is_still_mapped_to_crossrefs_rows_param():
    """The total fix must not disturb the existing limit->rows mapping."""
    assert _tool()._get_param_mapping()["limit"] == "rows"


# ---------------------------------------------------------------------------
# Config: the paging advice the note gives must be usable
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name", ["Crossref_search_works", "Crossref_list_funders", "Crossref_search_members"]
)
def test_searchable_list_tools_declare_offset(name):
    props = CONFIGS[name]["parameter"]["properties"]
    assert "offset" in props, f"{name}'s truncation note tells callers to pass offset"
    assert props["offset"]["type"] == "integer"


@pytest.mark.parametrize(
    "name", ["Crossref_search_works", "Crossref_list_funders", "Crossref_search_members"]
)
def test_searchable_list_tools_document_total_count(name):
    assert "total_count" in CONFIGS[name]["description"]


def test_return_schema_still_describes_the_inner_payload():
    """Issue #246 convention: return_schema describes `data`, not the envelope.

    total_count/count/note live in the envelope, so these schemas must stay
    array-shaped -- cli.py validates result["data"] against them.
    """
    for name in ("Crossref_search_works", "Crossref_list_funders"):
        schema = CONFIGS[name]["return_schema"]
        types = schema["type"]
        assert "array" in (types if isinstance(types, list) else [types])
        assert "total_count" not in json.dumps(schema)
