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
def test_path_alias_is_consumed_not_leaked_into_query_params():
    """Fix-R31B-3: an alias key (e.g. "gene" -> "symbol") left in args after
    _build_url resolves it used to leak into _build_params as an
    unrecognized query param -- confirmed live this isn't harmless:
    PostgREST-backed APIs (e.g. CPIC) try to parse every query key as a
    filter expression and 400 with "failed to parse filter" on it, breaking
    the whole request."""
    tool = _make_tool({"path_aliases": {"gene": "symbol"}})
    args = {"gene": "CYP2D6"}
    url = tool._build_url(args)
    assert url == "https://example.org/api"  # endpoint has no {symbol} placeholder here
    assert "gene" not in args
    assert args["symbol"] == "CYP2D6"
    params = tool._build_params(args)
    assert "gene" not in params
    assert params["symbol"] == "CYP2D6"


@pytest.mark.unit
def test_path_alias_consumed_even_when_canonical_already_present():
    # Both the alias and the canonical name are supplied -- the alias must
    # still be dropped so it doesn't leak as a stray query param.
    tool = _make_tool({"path_aliases": {"gene": "symbol"}})
    args = {"gene": "CYP2D6", "symbol": "CYP2D6"}
    tool._build_url(args)
    assert "gene" not in args
    assert args["symbol"] == "CYP2D6"


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


@pytest.mark.unit
def test_empty_result_note_added_when_data_is_empty_list(monkeypatch):
    """Fix-R32C-4/5: an exact-match backend (e.g. CPIC's PostgREST
    name=eq.{name}) silently returns status:success with an empty list for
    any name not spelled/named exactly as the database stores it --
    confirmed live for well-known aliases ("FK506" for tacrolimus) and
    spelling variants ("cyclosporin" vs the indexed "cyclosporine"),
    indistinguishable from "no PGx data exists for this drug".
    `fields.empty_result_note` surfaces the real constraint."""
    import unittest.mock as mock

    tool = _make_tool({"empty_result_note": "No exact match; try the canonical name."})

    def fake_request(session, method, url, **kwargs):
        resp = mock.MagicMock()
        resp.status_code = 200
        resp.json.return_value = []
        resp.headers = {"content-type": "application/json"}
        resp.text = "[]"
        return resp

    with mock.patch(
        "tooluniverse.base_rest_tool.request_with_retry", side_effect=fake_request
    ):
        result = tool.run({"name": "FK506"})

    assert result["note"] == "No exact match; try the canonical name."


@pytest.mark.unit
def test_empty_result_note_absent_when_data_is_non_empty(monkeypatch):
    import unittest.mock as mock

    tool = _make_tool({"empty_result_note": "No exact match; try the canonical name."})

    def fake_request(session, method, url, **kwargs):
        resp = mock.MagicMock()
        resp.status_code = 200
        resp.json.return_value = [{"name": "cyclosporine"}]
        resp.headers = {"content-type": "application/json"}
        resp.text = '[{"name": "cyclosporine"}]'
        return resp

    with mock.patch(
        "tooluniverse.base_rest_tool.request_with_retry", side_effect=fake_request
    ):
        result = tool.run({"name": "cyclosporine"})

    assert "note" not in result


@pytest.mark.unit
def test_no_empty_result_note_configured_is_unchanged():
    # Tools without empty_result_note keep the previous behaviour (no note).
    import unittest.mock as mock

    tool = _make_tool({})

    def fake_request(session, method, url, **kwargs):
        resp = mock.MagicMock()
        resp.status_code = 200
        resp.json.return_value = []
        resp.headers = {"content-type": "application/json"}
        resp.text = "[]"
        return resp

    with mock.patch(
        "tooluniverse.base_rest_tool.request_with_retry", side_effect=fake_request
    ):
        result = tool.run({"name": "whatever"})

    assert "note" not in result
