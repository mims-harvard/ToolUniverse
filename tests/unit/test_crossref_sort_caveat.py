"""Regression guard for Fix-R12A-2: Crossref_search_works accepts an
undeclared `sort` passthrough param (BaseRESTTool forwards any caller arg
straight through as a query param). Confirmed live and via raw curl to
api.crossref.org that combining `query=` with `sort=is-referenced-by-count`
makes Crossref return globally top-cited works with no relevance to the
query -- this is genuine upstream Crossref API behavior, not a ToolUniverse
bug, but the tool description previously gave no warning about it. Lock in
the caveat so it can't be silently dropped in a future docs edit.
"""

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

CONFIG_PATH = (
    Path(__file__).parent.parent.parent / "src/tooluniverse/data/crossref_tools.json"
)


def test_search_description_warns_about_sort_and_query_interaction():
    configs = json.loads(CONFIG_PATH.read_text())
    config = next(c for c in configs if c["name"] == "Crossref_search_works")
    description = config["description"].lower()
    assert "sort" in description
    assert "relevance" in description
