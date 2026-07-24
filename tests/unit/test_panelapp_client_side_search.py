"""Regression guard for Fix-R26C-2: PanelApp_search_panels's `search` param
was a complete no-op server-side. Confirmed live: `search=`, `q=`, and
`name__icontains=` all returned PanelApp's full unfiltered 434-panel list
regardless of value (only an exact full-string `name=` match filters
anything, and its OpenAPI schema documents no search param at all).
PanelAppSearchTool now fetches every panel (paginating the API's fixed
page_size=100) and filters client-side by substring match against
name/disease_group/disease_sub_group.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.panelapp_tool import PanelAppSearchTool

pytestmark = pytest.mark.unit

_PANELS = [
    {"id": 1, "name": "Acute intermittent porphyria", "disease_group": "Gastrohepatology", "disease_sub_group": ""},
    {"id": 2, "name": "Familial breast cancer", "disease_group": "Inherited cancer", "disease_sub_group": ""},
    {"id": 3, "name": "Primary ovarian insufficiency", "disease_group": "Reproductive", "disease_sub_group": ""},
]


def _tool():
    return PanelAppSearchTool({"name": "panelapp_test", "fields": {}, "parameter": {}})


def _resp(results, next_url=None):
    r = MagicMock()
    r.raise_for_status = MagicMock()
    r.json.return_value = {"count": len(results), "next": next_url, "results": results}
    return r


class TestClientSideSearchFiltering:
    def test_filters_by_name_substring(self):
        tool = _tool()
        with patch.object(tool.session, "get", return_value=_resp(_PANELS)):
            result = tool.run({"search": "breast cancer"})

        assert result["status"] == "success"
        assert result["data"]["count"] == 1
        assert result["data"]["results"][0]["name"] == "Familial breast cancer"

    def test_no_match_returns_empty_not_full_list(self):
        # The old behavior (server-side no-op) would have returned all 3
        # panels here; the fix must return zero for a genuine non-match.
        tool = _tool()
        with patch.object(tool.session, "get", return_value=_resp(_PANELS)):
            result = tool.run({"search": "xyzzyqqqnonexistentterm"})

        assert result["data"]["count"] == 0
        assert result["data"]["results"] == []

    def test_matches_disease_group_not_just_name(self):
        tool = _tool()
        with patch.object(tool.session, "get", return_value=_resp(_PANELS)):
            result = tool.run({"search": "reproductive"})

        assert result["data"]["count"] == 1
        assert result["data"]["results"][0]["name"] == "Primary ovarian insufficiency"

    def test_paginates_through_next_url(self):
        tool = _tool()
        page1 = _resp([_PANELS[0]], next_url="https://panelapp.../?page=2")
        page2 = _resp([_PANELS[1]])
        with patch.object(tool.session, "get", side_effect=[page1, page2]):
            result = tool.run({"search": "cancer"})

        assert result["metadata"]["total_panels_searched"] == 2
        assert result["data"]["count"] == 1

    def test_requires_search_param(self):
        tool = _tool()
        result = tool.run({})
        assert result["status"] == "error"
