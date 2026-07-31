"""WHOGHO_get_indicator_data must map filter/top args to WHO GHO's OData
query params.

Regression (Fix-R24B-1): the config had no `fields.param_mapping`, so
BaseRESTTool sent the caller's `filter`/`top` arguments as literal
unprefixed query params (`filter=...`, `top=...`). WHO GHO's OData API
silently ignores unrecognized params, so every call fell back to the
hardcoded default `$top=20` with no filter applied at all -- confirmed
live that a country-scoped query returned 20 rows from unrelated
countries. The sibling tool WHOGHO_search_indicators already carries the
correct `{"filter": "$filter", "top": "$top"}` mapping; this tool was
missing it.
"""

import json
import os

import pytest

pytestmark = pytest.mark.unit

_CONFIG = os.path.join(
    os.path.dirname(__file__),
    "..",
    "..",
    "src",
    "tooluniverse",
    "data",
    "who_gho_tools.json",
)


def _tool(name):
    with open(_CONFIG) as fh:
        for t in json.load(fh):
            if isinstance(t, dict) and t.get("name") == name:
                return t
    raise AssertionError(f"{name} not found in who_gho_tools.json")


def test_get_indicator_data_maps_filter_and_top_to_odata_params():
    tool = _tool("WHOGHO_get_indicator_data")
    mapping = tool.get("fields", {}).get("param_mapping", {})
    assert mapping.get("filter") == "$filter"
    assert mapping.get("top") == "$top"


def test_search_indicators_mapping_unaffected():
    tool = _tool("WHOGHO_search_indicators")
    mapping = tool.get("fields", {}).get("param_mapping", {})
    assert mapping.get("filter") == "$filter"
    assert mapping.get("top") == "$top"
