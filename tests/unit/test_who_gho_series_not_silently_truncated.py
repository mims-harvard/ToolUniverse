"""WHOGHO_get_indicator_data must not return an arbitrary silent subset.

Regression: the config sent ``$top: 20`` with no ``$orderby`` and no
``$count``, so a request for a country's time series came back as 20 rows
in the GHO API's internal ``Id`` order -- an arbitrary, non-chronological
sample -- with nothing in the response indicating rows were missing.
Confirmed live against
https://ghoapi.azureedge.net/api/MDG_0000000020?$filter=SpatialDim eq 'BGD'
which holds 25 rows (2000-2024): the tool returned years
2003, 2010, 2004, 2005, 2020, 2002, ... and silently dropped 2006, 2013,
2017, 2018 and 2021, so a plotted series had invisible, unpredictable
holes.

Verified live that the GHO OData endpoint supports both ``$count=true``
(returns ``@odata.count``: 25 for the query above, 5177 for the whole
indicator) and ``$orderby`` including the composite
``SpatialDim asc,TimeDim asc``. The fix sends both, raises ``$top`` to
100, exposes ``orderby``, and opts into ``fields.pagination_disclosure``
so a capped result carries a top-level ``truncated`` flag, the real
``total_available`` and a ``truncation_note``. ``fields.echo_request_url``
makes the echoed ``url`` include the ``$filter``/``$top`` actually sent.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.base_rest_tool import BaseRESTTool  # noqa: E402

pytestmark = pytest.mark.unit

CONFIG_PATH = (
    Path(__file__).parent.parent.parent / "src/tooluniverse/data/who_gho_tools.json"
)


def _tool_config(name):
    configs = json.loads(CONFIG_PATH.read_text())
    return next(c for c in configs if c["name"] == name)


class _FakeResponse:
    def __init__(self, payload, url="https://ghoapi.azureedge.net/api/STUB"):
        self.status_code = 200
        self._payload = payload
        self.text = json.dumps(payload)
        self.headers = {"content-type": "application/json"}
        self.url = url

    def json(self):
        return self._payload


def _row(year):
    return {
        "Id": 1000 + year,
        "IndicatorCode": "MDG_0000000020",
        "SpatialDimType": "COUNTRY",
        "SpatialDim": "BGD",
        "TimeDim": year,
        "NumericValue": 221.0,
        "Value": "221 [161-291]",
    }


def _run(payload, arguments, response_url=None):
    tool = BaseRESTTool(_tool_config("WHOGHO_get_indicator_data"))
    captured = {}

    def fake_request(session, method, url, **kwargs):
        captured["url"] = url
        captured["params"] = kwargs.get("params", {})
        return _FakeResponse(
            payload, url=response_url or "https://ghoapi.azureedge.net/api/STUB"
        )

    import tooluniverse.base_rest_tool as mod

    original = mod.request_with_retry
    mod.request_with_retry = fake_request
    try:
        return tool.run(dict(arguments)), captured
    finally:
        mod.request_with_retry = original


# --------------------------------------------------------------------------
# Config-level guards
# --------------------------------------------------------------------------


def test_odata_count_and_deterministic_order_are_requested():
    fields = _tool_config("WHOGHO_get_indicator_data")["fields"]
    assert fields["params"]["$count"] == "true"
    orderby = fields["params"]["$orderby"]
    assert "TimeDim" in orderby, "a truncated series must be chronologically ordered"
    assert fields["params"]["$top"] >= 100


def test_orderby_is_exposed_and_mapped_to_the_odata_param():
    config = _tool_config("WHOGHO_get_indicator_data")
    assert "orderby" in config["parameter"]["properties"]
    mapping = config["fields"]["param_mapping"]
    assert mapping["orderby"] == "$orderby"
    # pre-existing mappings must survive
    assert mapping["filter"] == "$filter"
    assert mapping["top"] == "$top"


def test_pagination_disclosure_points_at_the_odata_envelope():
    fields = _tool_config("WHOGHO_get_indicator_data")["fields"]
    disclosure = fields["pagination_disclosure"]
    assert disclosure["total_path"] == ["@odata.count"]
    assert disclosure["rows_path"] == ["value"]
    assert fields["echo_request_url"] is True


def test_return_schema_does_not_forbid_extra_envelope_keys():
    schema = _tool_config("WHOGHO_get_indicator_data")["return_schema"]
    assert schema.get("additionalProperties") is not False
    for branch in schema.get("oneOf", []):
        assert branch.get("additionalProperties") is not False


# --------------------------------------------------------------------------
# Runtime behaviour
# --------------------------------------------------------------------------


def test_row_cap_is_disclosed_with_the_real_total():
    payload = {
        "@odata.count": 25,
        "value": [_row(y) for y in range(2000, 2020)],
    }
    result, _ = _run(
        payload,
        {
            "indicator_code": "MDG_0000000020",
            "filter": "SpatialDim eq 'BGD'",
            "top": 20,
        },
    )

    assert result["status"] == "success"
    assert result["truncated"] is True
    assert result["total_available"] == 25
    assert result["count"] == 20
    note = result["truncation_note"]
    assert "20 of 25" in note
    assert "top" in note


def test_full_series_is_explicitly_not_truncated():
    payload = {
        "@odata.count": 25,
        "value": [_row(y) for y in range(2000, 2025)],
    }
    result, _ = _run(
        payload,
        {"indicator_code": "MDG_0000000020", "filter": "SpatialDim eq 'BGD'"},
    )

    assert result["truncated"] is False
    assert "truncation_note" not in result
    assert result["count"] == 25
    years = [r["TimeDim"] for r in result["data"]["value"]]
    assert years == sorted(years), "series must come back in chronological order"
    assert set(range(2000, 2025)) - set(years) == set(), "no holes in the series"


def test_no_matching_data_is_not_reported_as_truncation():
    result, _ = _run(
        {"@odata.count": 0, "value": []},
        {"indicator_code": "MDG_0000000020", "filter": "SpatialDim eq 'ZZZ'"},
    )
    assert result["truncated"] is False
    assert result["count"] == 0
    assert result["total_available"] == 0


def test_defaults_and_caller_overrides_reach_the_api():
    _, captured = _run(
        {"@odata.count": 0, "value": []},
        {"indicator_code": "MDG_0000000020"},
    )
    params = captured["params"]
    assert params["$count"] == "true"
    assert params["$top"] == 100
    assert "TimeDim" in params["$orderby"]

    _, captured = _run(
        {"@odata.count": 0, "value": []},
        {
            "indicator_code": "MDG_0000000020",
            "filter": "SpatialDim eq 'BGD'",
            "top": 500,
            "orderby": "TimeDim desc",
        },
    )
    params = captured["params"]
    assert params["$top"] == 500
    assert params["$orderby"] == "TimeDim desc"
    assert params["$filter"] == "SpatialDim eq 'BGD'"
    assert "orderby" not in params


def test_echoed_url_includes_the_odata_query_actually_sent():
    full = (
        "https://ghoapi.azureedge.net/api/MDG_0000000020"
        "?%24top=100&%24count=true&%24filter=SpatialDim+eq+%27BGD%27"
    )
    result, captured = _run(
        {"@odata.count": 0, "value": []},
        {"indicator_code": "MDG_0000000020", "filter": "SpatialDim eq 'BGD'"},
        response_url=full,
    )
    # the request target is still the bare endpoint; only the echo is enriched
    assert captured["url"] == "https://ghoapi.azureedge.net/api/MDG_0000000020"
    assert result["url"] == full
