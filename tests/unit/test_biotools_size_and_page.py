"""BioTools searches ignored ``size`` and returned a full server page of 50.

bio.tools always answers with 50 tools and ignores ``size``/``page_size``, so a
documented default of 10 returned 50 and ``page`` skipped 50 at a time whatever ``size``
was. ``size`` and ``page`` are now applied client-side over the 50-tool server pages.
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from tooluniverse.base_rest_tool import BaseRESTTool
from tooluniverse.biotools_tool import BioToolsRESTTool

pytestmark = pytest.mark.unit

DATA = Path(__file__).parent.parent.parent / "src" / "tooluniverse" / "data"
TOTAL = 120


def _config(name):
    tools = json.loads(
        (DATA / "biotools_registry_tools.json").read_text(encoding="utf-8")
    )
    return next(t for t in tools if t["name"] == name)


def _server(calls):
    """Fake bio.tools: pages of 50 out of TOTAL tools, ignoring size."""

    def run(self, arguments):
        page = arguments["page"]
        calls.append(page)
        first = (page - 1) * 50
        ids = [f"tool{i}" for i in range(first, min(first + 50, TOTAL))]
        return {
            "status": "success",
            "data": {
                "count": TOTAL,
                "next": f"?page={page + 1}" if first + 50 < TOTAL else None,
                "previous": None,
                "list": [{"biotoolsID": i} for i in ids],
            },
            "count": len(ids),
        }

    return run


def _search(arguments, name="BioTools_search"):
    calls = []
    tool = BioToolsRESTTool(_config(name))
    with patch.object(BaseRESTTool, "run", _server(calls)):
        result = tool.run(arguments)
    return result, calls


def _ids(result):
    return [t["biotoolsID"] for t in result["data"]["list"]]


def test_default_size_is_ten_not_a_full_page_of_fifty():
    result, calls = _search({"q": "blast"})
    assert _ids(result) == [f"tool{i}" for i in range(10)]
    assert calls == [1]
    assert result["count"] == 10 and result["data"]["count"] == TOTAL


def test_page_advances_by_size_not_by_server_page():
    result, _ = _search({"q": "blast", "size": 3, "page": 2})
    assert _ids(result) == ["tool3", "tool4", "tool5"]
    assert result["data"]["previous"] == "?page=1&size=3"
    assert result["data"]["next"] == "?page=3&size=3"


def test_window_spanning_two_server_pages_is_stitched_together():
    result, calls = _search({"q": "blast", "size": 30, "page": 2})
    assert _ids(result) == [f"tool{i}" for i in range(30, 60)]
    assert calls == [1, 2]


def test_last_page_has_no_next_and_size_is_capped_at_fifty():
    result, _ = _search({"q": "blast", "size": 500, "page": 3})
    assert _ids(result) == [f"tool{i}" for i in range(100, 120)]
    assert result["data"]["next"] is None


@pytest.mark.parametrize("name", ["BioTools_search", "BioTools_search_by_type"])
def test_search_tools_use_the_size_aware_class(name):
    assert _config(name)["type"] == "BioToolsRESTTool"


def test_errors_from_the_server_are_returned_unchanged():
    tool = BioToolsRESTTool(_config("BioTools_search"))
    error = {"status": "error", "error": "BioTools_search API error"}
    with patch.object(BaseRESTTool, "run", lambda self, arguments: error):
        assert tool.run({"q": "x"}) == error
