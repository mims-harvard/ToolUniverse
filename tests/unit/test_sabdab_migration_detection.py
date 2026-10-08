"""The SAbDab2 migration, now followed rather than only detected.

This file used to guard a stopgap. SAbDab moved to a React app that serves the
same 200 text/html shell for every route, so the old REST-style endpoints
returned HTML and neither tool noticed: get_structure reported success with the
page's byte count mislabelled as structure content, and get_structure_summary's
error implied the entry was not an antibody complex even for its own examples.
The guard added then detected HTML and said so, and its docstring recorded that
"a full SAbDab2 API integration ... is a bigger-scope redesign, not attempted
here".

That integration has now happened: the tools read SAbDab 2's JSON API, keyed by
extended PDB ID, covered by tests/unit/test_sabdab_reads_the_api.py. What
remains worth guarding is the invariant that produced the stopgap -- a 200 that
is not JSON must never be reported as data -- asserted here against the new
implementation, with `json()` raising the way requests actually raises on HTML.
"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.sabdab_tool import SAbDabTool

pytestmark = pytest.mark.unit


def _tool(operation):
    return SAbDabTool(
        {
            "name": f"SAbDab_{operation}",
            "type": "SAbDabTool",
            "fields": {"operation": operation},
            "parameter": {"type": "object", "properties": {}},
        }
    )


class _HtmlResponse:
    """A 200 serving the app shell, as every unknown SAbDab path still does."""

    status_code = 200
    headers = {"Content-Type": "text/html; charset=utf-8"}
    text = '<!doctype html><html><head><title>SAbDab2</title></head></html>'

    @staticmethod
    def json():
        raise ValueError("Expecting value: line 1 column 1 (char 0)")


@pytest.mark.parametrize(
    "operation", ["get_structure", "get_structure_summary", "get_summary"]
)
def test_an_html_200_is_never_reported_as_data(operation):
    """The failure that started this: HTML counted as a successful result."""
    with patch(
        "tooluniverse.sabdab_tool.requests.get", return_value=_HtmlResponse()
    ):
        result = _tool(operation).run({"operation": operation, "pdb_id": "1n8z"})

    assert result["status"] == "error", (
        f"{operation} reported success for a 200 text/html response"
    )
    assert "not JSON" in result["error"] or "not an API route" in result["error"]


def test_search_survives_an_html_200_without_claiming_results():
    """Search makes a request only for the catalogue size, so it degrades."""
    with patch(
        "tooluniverse.sabdab_tool.requests.get", return_value=_HtmlResponse()
    ):
        result = _tool("search_structures").run(
            {"operation": "search_structures", "query": "anti-CD20"}
        )

    assert result["status"] == "success"
    assert result["data"]["searched"] is False
    assert result["data"]["catalogue_size"] is None, (
        "an unreachable count must be null, not a stale or invented number"
    )
