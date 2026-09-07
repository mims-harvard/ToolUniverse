"""WorldBank_get_indicator must not silently drop rows to server-side paging.

Regression: the config pinned ``per_page: "50"`` and exposed no ``page`` /
``per_page`` parameter, so any query matching more than 50 country-year
observations returned only the first page while still reporting
``status: success``. Confirmed live against
https://api.worldbank.org/v2/country/IND;IDN;MMR;BGD/indicator/NY.GDP.PCAP.CD?date=2010:2024&format=json
-- upstream reports ``total: 60`` (4 countries x 15 years) but the tool
returned 50 rows, cutting off part-way through Myanmar so MMR 2010-2019
(2010 = 1010.53) vanished entirely. The only hint was the World Bank
metadata object at ``data[0]`` (``{"page": 1, "pages": 2, ...}``), and
page 2 was unreachable because no paging parameter existed. Top-level
``count`` was 2 -- the length of the ``[metadata, rows]`` envelope, not a
row count.

The fix raises the default ``per_page`` to 1000 (32500 is the documented
maximum; 40000 returns HTTP 400), exposes ``per_page``/``page``, and opts
the tool into ``fields.pagination_disclosure`` so a partial result carries
a top-level ``truncated`` flag, the real ``total_available`` and a
``truncation_note``. ``fields.echo_request_url`` makes the echoed ``url``
include the query string that was actually sent.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.base_rest_tool import BaseRESTTool  # noqa: E402

pytestmark = pytest.mark.unit

CONFIG_PATH = (
    Path(__file__).parent.parent.parent / "src/tooluniverse/data/worldbank_tools.json"
)


def _tool_config(name):
    configs = json.loads(CONFIG_PATH.read_text())
    return next(c for c in configs if c["name"] == name)


class _FakeResponse:
    def __init__(self, payload, url="https://api.worldbank.org/v2/stub?format=json"):
        self.status_code = 200
        self._payload = payload
        self.text = json.dumps(payload)
        self.headers = {"content-type": "application/json"}
        self.url = url

    def json(self):
        return self._payload


def _row(iso3, year):
    return {
        "indicator": {"id": "NY.GDP.PCAP.CD", "value": "GDP per capita (current US$)"},
        "country": {"id": iso3[:2], "value": iso3},
        "countryiso3code": iso3,
        "date": str(year),
        "value": 1000.0,
        "decimal": 1,
    }


def _payload(rows, total, page=1, pages=1, per_page=1000):
    return [
        {
            "page": page,
            "pages": pages,
            "per_page": per_page,
            "total": total,
            "sourceid": "2",
        },
        rows,
    ]


def _run(payload, arguments, response_url=None):
    config = _tool_config("WorldBank_get_indicator")
    tool = BaseRESTTool(config)
    captured = {}

    def fake_request(session, method, url, **kwargs):
        captured["url"] = url
        captured["params"] = kwargs.get("params", {})
        return _FakeResponse(
            payload, url=response_url or "https://api.worldbank.org/v2/stub"
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


def test_default_per_page_is_large_enough_for_ordinary_country_panels():
    fields = _tool_config("WorldBank_get_indicator")["fields"]
    per_page = int(fields["params"]["per_page"])
    # The reported failure was 4 countries x 15 years = 60 rows against a
    # per_page of 50. Anything at or below 60 reintroduces it.
    assert per_page >= 1000
    # 32500 is the largest value the API accepts (40000 -> HTTP 400).
    assert per_page <= 32500


def test_page_and_per_page_are_reachable_as_tool_parameters():
    props = _tool_config("WorldBank_get_indicator")["parameter"]["properties"]
    assert "page" in props, "page 2+ must be reachable through the tool"
    assert "per_page" in props


def test_pagination_disclosure_points_at_worldbank_envelope():
    fields = _tool_config("WorldBank_get_indicator")["fields"]
    disclosure = fields["pagination_disclosure"]
    assert disclosure["total_path"] == [0, "total"]
    assert disclosure["rows_path"] == [1]
    assert fields["echo_request_url"] is True


def test_return_schema_does_not_forbid_extra_envelope_keys():
    schema = _tool_config("WorldBank_get_indicator")["return_schema"]
    assert schema.get("additionalProperties") is not False
    for branch in schema.get("oneOf", []):
        assert branch.get("additionalProperties") is not False


# --------------------------------------------------------------------------
# Runtime behaviour
# --------------------------------------------------------------------------


def test_partial_page_is_flagged_truncated_with_the_real_total():
    rows = [_row("BGD", y) for y in range(2010, 2025)]
    rows += [_row("IDN", y) for y in range(2010, 2025)]
    rows += [_row("IND", y) for y in range(2010, 2025)]
    rows += [_row("MMR", y) for y in range(2020, 2025)]  # cut off mid-Myanmar
    result, _ = _run(
        _payload(rows, total=60, page=1, pages=2, per_page=50),
        {
            "country": "IND;IDN;MMR;BGD",
            "indicator": "NY.GDP.PCAP.CD",
            "date": "2010:2024",
        },
    )

    assert result["status"] == "success"
    assert result["truncated"] is True
    assert result["total_available"] == 60
    # `count` must be the row count, not the length of the [meta, rows] envelope.
    assert result["count"] == 50
    note = result["truncation_note"]
    assert "50 of 60" in note
    assert "page 1 of 2" in note
    assert "per_page" in note and "page" in note


def test_complete_page_is_explicitly_not_truncated():
    rows = [_row("BGD", y) for y in range(2010, 2025)]
    rows += [_row("IDN", y) for y in range(2010, 2025)]
    rows += [_row("IND", y) for y in range(2010, 2025)]
    rows += [_row("MMR", y) for y in range(2010, 2025)]
    result, _ = _run(
        _payload(rows, total=60, page=1, pages=1, per_page=1000),
        {
            "country": "IND;IDN;MMR;BGD",
            "indicator": "NY.GDP.PCAP.CD",
            "date": "2010:2024",
        },
    )

    assert result["truncated"] is False
    assert "truncation_note" not in result
    assert result["count"] == 60
    assert result["total_available"] == 60
    assert any(r["countryiso3code"] == "MMR" and r["date"] == "2010" for r in rows)


def test_empty_result_is_reported_as_no_data_not_as_truncated():
    result, _ = _run(
        _payload([], total=0),
        {"country": "XKX", "indicator": "NY.GDP.PCAP.CD", "date": "1800"},
    )
    assert result["truncated"] is False
    assert result["count"] == 0
    assert result["total_available"] == 0


def test_default_and_caller_supplied_paging_params_reach_the_api():
    _, captured = _run(
        _payload([], total=0),
        {"country": "USA", "indicator": "NY.GDP.PCAP.CD"},
    )
    assert captured["params"]["per_page"] == "1000"

    _, captured = _run(
        _payload([], total=0),
        {"country": "USA", "indicator": "NY.GDP.PCAP.CD", "per_page": 5000, "page": 3},
    )
    assert captured["params"]["per_page"] == 5000
    assert captured["params"]["page"] == 3


def test_echoed_url_includes_the_query_string_actually_sent():
    full = (
        "https://api.worldbank.org/v2/country/USA/indicator/NY.GDP.PCAP.CD"
        "?format=json&per_page=1000&date=2010%3A2024"
    )
    result, _ = _run(
        _payload([], total=0),
        {"country": "USA", "indicator": "NY.GDP.PCAP.CD", "date": "2010:2024"},
        response_url=full,
    )
    assert result["url"] == full


# --------------------------------------------------------------------------
# The shared BaseRESTTool additions must stay opt-in
# --------------------------------------------------------------------------


def test_tools_without_the_new_flags_are_unaffected():
    config = {
        "name": "StubTool",
        "type": "BaseRESTTool",
        "parameter": {"type": "object", "properties": {}},
        "fields": {"endpoint": "https://example.invalid/api"},
    }
    tool = BaseRESTTool(config)

    import tooluniverse.base_rest_tool as mod

    original = mod.request_with_retry
    mod.request_with_retry = lambda session, method, url, **kw: _FakeResponse(
        [{"total": 60}, [{"a": 1}]], url="https://example.invalid/api?x=1"
    )
    try:
        result = tool.run({})
    finally:
        mod.request_with_retry = original

    assert result["url"] == "https://example.invalid/api"
    assert result["count"] == 2  # unchanged: length of the raw list payload
    assert "truncated" not in result
    assert "total_available" not in result
    assert "truncation_note" not in result
