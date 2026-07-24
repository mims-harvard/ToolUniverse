"""Regression guard for Fix-R36A-1: every `DatasetTool`-typed tool
(drugbank_vocab_search, drugbank_vocab_filter, drugbank_full_search,
drugbank_links_search, dict_search, dili_search, diqt_search) marked
search_fields/case_sensitive/exact_match/limit (or field/condition/limit
for the filter variant) as schema-`required`, even though every one of
them has a real, working default value in the tool's own `query_schema`
config block and DatasetTool.run() already merges those defaults in
before applying caller-supplied overrides (`query_params =
deepcopy(self.query_schema)` then overlay `arguments`). Any caller who
supplied only the one truly-essential param (`query`, or `field`+
`condition` for the filter tool) hit a hard schema validation error
before the tool's own default-merging logic ever ran -- confirmed live,
e.g. dict_search({"query": "terfenadine"}) previously failed outright.
"""

import json
from pathlib import Path

import pandas as pd
import pytest

from tooluniverse.dataset_tool import DatasetTool

pytestmark = pytest.mark.unit

_DATA_DIR = Path(__file__).parent.parent.parent / "src" / "tooluniverse" / "data"
_DATASET_TOOL_NAMES = [
    "drugbank_vocab_search",
    "drugbank_vocab_filter",
    "drugbank_full_search",
    "drugbank_links_search",
    "dict_search",
    "dili_search",
    "diqt_search",
]


def _tool_config(name):
    configs = json.loads((_DATA_DIR / "dataset_tools.json").read_text())
    for cfg in configs:
        if cfg["name"] == name:
            return cfg
    raise AssertionError(f"{name} not found in dataset_tools.json")


@pytest.mark.parametrize("name", _DATASET_TOOL_NAMES)
def test_required_params_are_only_the_ones_without_a_query_schema_default(name):
    cfg = _tool_config(name)
    required = set(cfg["parameter"]["required"])
    query_schema_keys = set(cfg.get("query_schema", {}).keys())
    # Nothing that has a query_schema default should still be required.
    assert not (required & query_schema_keys)


def test_search_tools_still_require_query():
    for name in (
        "drugbank_vocab_search",
        "drugbank_full_search",
        "drugbank_links_search",
        "dict_search",
        "dili_search",
        "diqt_search",
    ):
        cfg = _tool_config(name)
        assert cfg["parameter"]["required"] == ["query"]


def test_filter_tool_has_no_required_params():
    cfg = _tool_config("drugbank_vocab_filter")
    assert cfg["parameter"]["required"] == []


def _make_search_tool():
    tool = DatasetTool.__new__(DatasetTool)
    tool.tool_config = {"name": "dict_search"}
    tool.query_schema = {
        "search_fields": ["Trade Name", "Generic/Proper Name(s)"],
        "case_sensitive": False,
        "exact_match": False,
        "limit": 10,
    }
    tool.parameters = {
        "query": {},
        "search_fields": {},
        "case_sensitive": {},
        "exact_match": {},
        "limit": {},
    }
    tool.dataset = pd.DataFrame(
        {
            "Trade Name": ["Seldane"],
            "Generic/Proper Name(s)": ["Terfenadine"],
        }
    )
    return tool


def test_query_only_call_uses_query_schema_defaults_end_to_end():
    tool = _make_search_tool()
    result = tool.run({"query": "terfenadine"})

    assert "error" not in result
    assert result["total_results"] == 1
    assert result["search_parameters"]["search_fields"] == [
        "Trade Name",
        "Generic/Proper Name(s)",
    ]
    assert result["search_parameters"]["limit"] == 10


def _make_filter_tool():
    tool = DatasetTool.__new__(DatasetTool)
    tool.tool_config = {"name": "drugbank_vocab_filter"}
    tool.query_schema = {"field": "Common name", "condition": "contains", "limit": 10}
    tool.parameters = {"field": {}, "condition": {}, "value": {}, "limit": {}}
    tool.dataset = pd.DataFrame({"Common name": ["Aspirin", "Ibuprofen"]})
    return tool


def test_filter_empty_args_falls_back_to_defaults_and_reports_missing_value():
    tool = _make_filter_tool()
    result = tool.run({})

    # field/condition/limit all resolved from query_schema with no schema
    # error; the only real gap (a missing "value" for "contains") is caught
    # by the tool's own runtime validation with an actionable message.
    assert result["status"] == "error"
    assert "value" in result["error"]
    assert "contains" in result["error"]


def test_filter_with_not_empty_condition_needs_no_value():
    tool = _make_filter_tool()
    result = tool.run({"condition": "not_empty"})

    assert "error" not in result
    assert result["total_matches"] == 2
