"""Regression guard: ToolFinderKeyword must not reuse a TF-IDF index that was
built from a different set of tools.

`_run_json_search` decided whether to rebuild the index by comparing the
number of documents already indexed to the number of tools left after the
`categories=[...]` filter. Two different categories of equal size compared
equal, so the second search scored against the first category's index.
`_calculate_tfidf_score` returns 0.0 for any tool missing from the index and
the caller drops everything scoring 0, so the matching tools vanished from
the response. Live example at the time: a `categories=['uniprot']` search
returned 5 tools from a fresh engine and 2 tools from an engine that had
already searched `fda_drug_adverse_event` (both categories hold 18 tools).
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.tool_finder_keyword import ToolFinderKeyword

pytestmark = pytest.mark.unit

GENOMICS_QUERY = "gene expression across tissues"
PHARMACOLOGY_QUERY = "drug adverse event reports"


def _catalogue(n_per_category=4):
    """Two categories of identical size, so counting tools cannot tell them apart."""
    tools = []
    for i in range(n_per_category):
        tools.append(
            {
                "name": f"genomics_tool_{i}",
                "description": "Query gene expression levels across tissues.",
                "type": "RESTTool",
                "category": "genomics",
                "parameter": {"type": "object", "properties": {"gene_id": {}}},
            }
        )
    for i in range(n_per_category):
        tools.append(
            {
                "name": f"pharmacology_tool_{i}",
                "description": "Look up drug dosing and adverse event reports.",
                "type": "RESTTool",
                "category": "pharmacology",
                "parameter": {"type": "object", "properties": {"drug_name": {}}},
            }
        )
    return tools


def _fake_tooluniverse(tools):
    tu = MagicMock()
    tu.all_tool_dict = {t["name"]: t for t in tools}
    tu.return_all_loaded_tools.return_value = list(tools)
    tu._excluded_api_key_tool_configs = {}
    tu._excluded_api_key_tools = {}
    return tu


def _search(finder, query, category):
    return json.loads(
        finder._run_json_search(
            {"description": query, "categories": [category], "limit": 5}
        )
    )


def test_equal_sized_categories_do_not_share_an_index():
    """A category search must not depend on which category was searched before."""
    tools = _catalogue()

    fresh = ToolFinderKeyword({}, tooluniverse=_fake_tooluniverse(tools))
    expected = _search(fresh, PHARMACOLOGY_QUERY, "pharmacology")

    reused = ToolFinderKeyword({}, tooluniverse=_fake_tooluniverse(tools))
    _search(reused, GENOMICS_QUERY, "genomics")
    got = _search(reused, PHARMACOLOGY_QUERY, "pharmacology")

    assert got["total_matches"] == expected["total_matches"]
    assert [t["name"] for t in got["tools"]] == [t["name"] for t in expected["tools"]]
    assert [t["relevance_score"] for t in got["tools"]] == [
        t["relevance_score"] for t in expected["tools"]
    ]


def test_index_holds_only_the_currently_filtered_tools():
    """The index is rebuilt for the new filter, not carried over from the old one."""
    tools = _catalogue()
    finder = ToolFinderKeyword({}, tooluniverse=_fake_tooluniverse(tools))

    _search(finder, GENOMICS_QUERY, "genomics")
    _search(finder, PHARMACOLOGY_QUERY, "pharmacology")

    assert set(finder._tool_index) == {"pharmacology_tool_" + str(i) for i in range(4)}


def test_index_is_reused_when_the_tool_set_is_unchanged():
    """An unchanged filter still reuses the index instead of rebuilding it."""
    tools = _catalogue()
    finder = ToolFinderKeyword({}, tooluniverse=_fake_tooluniverse(tools))

    _search(finder, GENOMICS_QUERY, "genomics")
    first_index = finder._tool_index
    _search(finder, "transcript abundance", "genomics")

    assert finder._tool_index is first_index
