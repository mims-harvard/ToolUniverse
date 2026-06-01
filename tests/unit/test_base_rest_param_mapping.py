"""Unit tests for config-driven BaseRESTTool query-param mapping.

Regression for Feature-007I-01/02: WHOGHO_search_indicators is a
config-only BaseRESTTool whose documented params are `filter` and `top`,
but the WHO OData API needs `$filter` and `$top`. Before this, the params
were passed through unmapped, so the filter was silently ignored (every
search returned the same unfiltered indicator page) and `top` had no
effect. A `fields.param_mapping` entry now renames them.
"""
import pytest

from tooluniverse.base_rest_tool import BaseRESTTool


def _make_tool(fields):
    return BaseRESTTool(
        {
            "name": "T",
            "type": "BaseRESTTool",
            "fields": {"endpoint": "https://example.org/api", **fields},
            "parameter": {"type": "object", "properties": {}},
        }
    )


@pytest.mark.unit
def test_param_mapping_renames_query_params():
    tool = _make_tool(
        {"param_mapping": {"filter": "$filter", "top": "$top"}}
    )
    assert tool._get_param_mapping() == {"filter": "$filter", "top": "$top"}
    params = tool._build_params({"filter": "contains(IndicatorName,'malaria')", "top": 5})
    assert params["$filter"] == "contains(IndicatorName,'malaria')"
    assert params["$top"] == 5
    # Unmapped raw names must NOT leak through.
    assert "filter" not in params
    assert "top" not in params


@pytest.mark.unit
def test_mapped_value_overrides_default_param():
    # fields.params provides a default $top; the caller's mapped top wins.
    tool = _make_tool(
        {"params": {"$top": 10}, "param_mapping": {"top": "$top"}}
    )
    params = tool._build_params({"top": 3})
    assert params["$top"] == 3


@pytest.mark.unit
def test_no_param_mapping_is_unchanged():
    # Tools without a param_mapping field keep the previous behaviour.
    tool = _make_tool({})
    assert tool._get_param_mapping() == {}
    params = tool._build_params({"foo": "bar"})
    assert params["foo"] == "bar"


@pytest.mark.unit
def test_auth_param_overrides_default_token_when_env_set(monkeypatch):
    # Feature-007K-01: a real env token replaces the public demo token.
    tool = _make_tool(
        {
            "params": {"token": "demo"},
            "auth_param": {"env_var": "WAQI_API_KEY", "param": "token"},
        }
    )
    monkeypatch.setenv("WAQI_API_KEY", "REALKEY123")
    params = tool._build_params({"city": "Boston"})
    assert params["token"] == "REALKEY123"


@pytest.mark.unit
def test_auth_param_keeps_default_token_when_env_unset(monkeypatch):
    tool = _make_tool(
        {
            "params": {"token": "demo"},
            "auth_param": {"env_var": "WAQI_API_KEY", "param": "token"},
        }
    )
    monkeypatch.delenv("WAQI_API_KEY", raising=False)
    params = tool._build_params({"city": "Boston"})
    assert params["token"] == "demo"
