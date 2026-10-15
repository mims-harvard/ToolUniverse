"""BridgeDb_search listed the exact gene symbol last.

The service returns matches in no useful order: for "TP53" the identifier TP53
itself came 20th, after TP53TG3, TP53BP1, TP53I3 ... An agent reading the top of
the list saw the wrong genes. Exact matches now come first, then identifiers that
start with the query; nothing is dropped.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.bridgedb_tool import BridgeDbTool

pytestmark = pytest.mark.unit

TSV = "\n".join(
    f"{identifier}\tHGNC"
    for identifier in ["TP53TG3", "TP53BP1", "MDM2-TP53", "TP53", "tp53-dt", "TP53INP1"]
)


def _search(query, text=TSV, status=200):
    tool = BridgeDbTool({"name": "BridgeDb_search", "fields": {"operation": "search"}})
    tool.session = MagicMock()
    tool.session.get.return_value = MagicMock(status_code=status, text=text)
    return tool._search({"query": query})


def test_exact_identifier_is_first_then_prefix_matches_then_the_rest():
    ids = [r["identifier"] for r in _search("TP53")["data"]["results"]]
    assert ids[0] == "TP53"
    assert ids[1:5] == [
        "TP53TG3",
        "TP53BP1",
        "tp53-dt",
        "TP53INP1",
    ]  # prefix, original order
    assert ids[-1] == "MDM2-TP53"


def test_matching_is_case_insensitive_and_nothing_is_dropped():
    result = _search("tp53")["data"]
    assert result["results"][0]["identifier"] == "TP53"
    assert result["count"] == 6 == len(result["results"])


def test_empty_response_still_succeeds_with_no_results():
    result = _search("zzzz", text="", status=204)
    assert result["status"] == "success" and result["data"]["results"] == []
