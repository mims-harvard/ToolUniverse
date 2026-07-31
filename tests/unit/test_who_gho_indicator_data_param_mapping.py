"""Regression guard for Fix-R12D-1: WHOGHO_get_indicator_data's `filter` and
`top` schema parameters were silently dropped -- the tool always returned
the same unfiltered, 20-row page regardless of what was requested. Root
cause: unlike its sibling WHOGHO_search_indicators, this tool's config had
no `fields.param_mapping` block, so BaseRESTTool never translated the
declared `filter`/`top` args into the OData `$filter`/`$top` query params
the live GHO OData API actually expects (confirmed live and via raw curl to
ghoapi.azureedge.net).
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.base_rest_tool import BaseRESTTool

pytestmark = pytest.mark.unit

CONFIG_PATH = (
    Path(__file__).parent.parent.parent / "src/tooluniverse/data/who_gho_tools.json"
)


def _tool_config(name):
    configs = json.loads(CONFIG_PATH.read_text())
    return next(c for c in configs if c["name"] == name)


class _FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload if payload is not None else {"value": []}
        self.text = json.dumps(self._payload)
        self.headers = {}

    def json(self):
        return self._payload


def test_config_declares_param_mapping_for_filter_and_top():
    config = _tool_config("WHOGHO_get_indicator_data")
    mapping = config["fields"].get("param_mapping", {})
    assert mapping.get("filter") == "$filter"
    assert mapping.get("top") == "$top"


def test_filter_and_top_are_translated_into_odata_query_params(monkeypatch):
    config = _tool_config("WHOGHO_get_indicator_data")
    tool = BaseRESTTool(config)

    captured = {}

    def fake_request(session, method, url, **kwargs):
        captured["params"] = kwargs.get("params", {})
        return _FakeResponse(200, {"value": []})

    monkeypatch.setattr("tooluniverse.base_rest_tool.request_with_retry", fake_request)

    tool.run(
        {
            "indicator_code": "NCDMORT3070",
            "filter": "SpatialDim eq 'USA'",
            "top": 3,
        }
    )

    params = captured["params"]
    assert params["$filter"] == "SpatialDim eq 'USA'"
    assert params["$top"] == 3
    assert "filter" not in params
    assert "top" not in params


def test_indicator_code_still_substituted_into_path(monkeypatch):
    config = _tool_config("WHOGHO_get_indicator_data")
    tool = BaseRESTTool(config)

    captured = {}

    def fake_request(session, method, url, **kwargs):
        captured["url"] = url
        return _FakeResponse(200, {"value": []})

    monkeypatch.setattr("tooluniverse.base_rest_tool.request_with_retry", fake_request)

    tool.run({"indicator_code": "NCDMORT3070", "top": 3})

    assert captured["url"] == "https://ghoapi.azureedge.net/api/NCDMORT3070"
