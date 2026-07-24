"""Depth tests for epidemiology-public-health coverage tools.

Covers two new tools that reuse existing tool classes (no new registration):

* ``WHOGHO_list_dimension_values`` (BaseRESTTool) — decodes WHO GHO dimension
  codes into human-readable labels and the country->region hierarchy via the
  OData ``/api/DIMENSION/{code}/DimensionValues`` endpoint. Resolves cryptic
  codes returned by WHOGHO_get_indicator_data (SpatialDim='ABW',
  Dim1='SEX_FMLE', region 'AFR') to Titles and parent rollups.
* ``cdc_data_aggregate`` (CDCRESTTool) — server-side SoQL aggregation on the
  Socrata ``/resource/{id}.json`` endpoint ($select/$group/$having/$query),
  which (unlike the legacy /api/views rows endpoint) honors aggregation.

All HTTP is mocked so the suite is offline/deterministic; live verification is
done separately via the CLI.
"""

import json
import os
from urllib.parse import parse_qs, urlparse

import pytest
import requests

import tooluniverse.base_rest_tool as base_rest_tool
from tooluniverse.base_rest_tool import BaseRESTTool
from tooluniverse.cdc_tool import CDCRESTTool

pytestmark = pytest.mark.unit

DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "src",
    "tooluniverse",
    "data",
)


def _load_tool_config(filename, tool_name):
    with open(os.path.join(DATA_DIR, filename)) as fh:
        configs = json.load(fh)
    matches = [c for c in configs if c.get("name") == tool_name]
    assert matches, f"{tool_name} not found in {filename}"
    return matches[0]


class _FakeResponse:
    def __init__(self, status_code=200, json_data=None, text="", headers=None):
        self.status_code = status_code
        self._json_data = json_data
        self.text = text
        self.headers = headers or {"content-type": "application/json"}

    def json(self):
        if self._json_data is None:
            raise ValueError("no JSON body")
        return self._json_data

    def raise_for_status(self):
        if not (200 <= self.status_code < 300):
            raise requests.exceptions.HTTPError(response=self)


# --- Sample WHO GHO DimensionValues payload (OData envelope) ---
_WHO_COUNTRY_PAYLOAD = {
    "@odata.context": "https://ghoapi.azureedge.net/api/$metadata#DimensionValues",
    "value": [
        {
            "Code": "ABW",
            "Title": "Aruba",
            "Dimension": "COUNTRY",
            "ParentDimension": "REGION",
            "ParentCode": "AMR",
            "ParentTitle": "Americas",
        },
        {
            "Code": "AFG",
            "Title": "Afghanistan",
            "Dimension": "COUNTRY",
            "ParentDimension": "REGION",
            "ParentCode": "EMR",
            "ParentTitle": "Eastern Mediterranean",
        },
    ],
}


# ===================== WHOGHO_list_dimension_values =====================


def test_who_dimension_values_parses_country_rollup(monkeypatch):
    """COUNTRY values decode to Titles plus the country->region parent rollup."""
    cfg = _load_tool_config("who_gho_tools.json", "WHOGHO_list_dimension_values")
    tool = BaseRESTTool(cfg)
    captured = {}

    def fake_request(
        session, method, url, params=None, headers=None, timeout=None, max_attempts=None
    ):
        captured["url"] = url
        captured["params"] = params
        return _FakeResponse(json_data=_WHO_COUNTRY_PAYLOAD)

    monkeypatch.setattr(base_rest_tool, "request_with_retry", fake_request)

    out = tool.run({"dimension_code": "COUNTRY"})

    assert out["status"] == "success"
    # The dimension_code must be substituted into the path, not sent as a query.
    assert captured["url"].endswith("/DIMENSION/COUNTRY/DimensionValues")
    assert "dimension_code" not in (captured["params"] or {})

    values = out["data"]["value"]
    aruba = next(v for v in values if v["Code"] == "ABW")
    assert aruba["Title"] == "Aruba"
    # Country -> region hierarchy is exposed via Parent* fields.
    assert aruba["ParentCode"] == "AMR"
    assert aruba["ParentTitle"] == "Americas"


def test_who_dimension_values_path_encodes_code(monkeypatch):
    """A dimension code is URL-path-substituted (not appended as a $ query)."""
    cfg = _load_tool_config("who_gho_tools.json", "WHOGHO_list_dimension_values")
    tool = BaseRESTTool(cfg)
    captured = {}

    sex_payload = {
        "value": [
            {"Code": "SEX_FMLE", "Title": "Female", "Dimension": "SEX"},
            {"Code": "SEX_MLE", "Title": "Male", "Dimension": "SEX"},
        ]
    }

    def fake_request(
        session, method, url, params=None, headers=None, timeout=None, max_attempts=None
    ):
        captured["url"] = url
        return _FakeResponse(json_data=sex_payload)

    monkeypatch.setattr(base_rest_tool, "request_with_retry", fake_request)

    out = tool.run({"dimension_code": "SEX"})
    assert out["status"] == "success"
    assert "/DIMENSION/SEX/DimensionValues" in captured["url"]
    labels = {v["Code"]: v["Title"] for v in out["data"]["value"]}
    assert labels["SEX_FMLE"] == "Female"


def test_who_dimension_values_http_error(monkeypatch):
    """A non-2xx response is returned as a status=error envelope, not raised."""
    cfg = _load_tool_config("who_gho_tools.json", "WHOGHO_list_dimension_values")
    tool = BaseRESTTool(cfg)

    def fake_request(
        session, method, url, params=None, headers=None, timeout=None, max_attempts=None
    ):
        return _FakeResponse(status_code=404, text="Not Found")

    monkeypatch.setattr(base_rest_tool, "request_with_retry", fake_request)
    out = tool.run({"dimension_code": "NOSUCHDIM"})
    assert out["status"] == "error"
    assert out["status_code"] == 404


def test_who_dimension_values_network_error(monkeypatch):
    """A connection failure is returned as a status=error envelope, not raised."""
    cfg = _load_tool_config("who_gho_tools.json", "WHOGHO_list_dimension_values")
    tool = BaseRESTTool(cfg)

    def boom(*args, **kwargs):
        raise requests.exceptions.ConnectionError("down")

    monkeypatch.setattr(base_rest_tool, "request_with_retry", boom)
    out = tool.run({"dimension_code": "COUNTRY"})
    assert out["status"] == "error"
    assert "error" in out


# ===================== cdc_data_aggregate =====================


def _cdc_tool():
    cfg = _load_tool_config("cdc_tools.json", "cdc_data_aggregate")
    return CDCRESTTool(cfg)


def test_cdc_aggregate_group_by_builds_select_and_group(monkeypatch):
    """$select/$group are forwarded to the /resource endpoint and parsed."""
    tool = _cdc_tool()
    captured = {}
    payload = [
        {"event": "Acute Hepatitis B", "count_1": "1235"},
        {"event": "Acute Hepatitis C", "count_1": "1231"},
    ]

    def fake_get(url, timeout=None):
        captured["url"] = url
        return _FakeResponse(json_data=payload)

    monkeypatch.setattr(requests, "get", fake_get)

    out = tool.run(
        {
            "dataset_id": "jkcx-ndu8",
            "select_clause": "event, count(*)",
            "group_clause": "event",
            "limit": 5,
        }
    )

    assert out["status"] == "success"
    parsed = urlparse(captured["url"])
    # Must hit the /resource/{id}.json endpoint (NOT the legacy /api/views one).
    assert parsed.path == "/resource/jkcx-ndu8.json"
    qs = parse_qs(parsed.query)
    assert qs["$select"] == ["event, count(*)"]
    assert qs["$group"] == ["event"]
    assert qs["$limit"] == ["5"]

    assert out["data"][0]["event"] == "Acute Hepatitis B"
    assert out["data"][0]["count_1"] == "1235"


def test_cdc_aggregate_count_total(monkeypatch):
    """A bare count(*) returns the total row count server-side."""
    tool = _cdc_tool()
    captured = {}

    def fake_get(url, timeout=None):
        captured["url"] = url
        return _FakeResponse(json_data=[{"count_1": "8588"}])

    monkeypatch.setattr(requests, "get", fake_get)
    out = tool.run({"dataset_id": "jkcx-ndu8", "select_clause": "count(*)"})
    assert out["status"] == "success"
    assert out["data"] == [{"count_1": "8588"}]
    qs = parse_qs(urlparse(captured["url"]).query)
    assert qs["$select"] == ["count(*)"]


def test_cdc_aggregate_full_soql_query_overrides_clauses(monkeypatch):
    """soql_query is forwarded as $query; discrete clauses/limit are dropped."""
    tool = _cdc_tool()
    captured = {}

    def fake_get(url, timeout=None):
        captured["url"] = url
        return _FakeResponse(json_data=[{"event": "Acute Hepatitis B", "n": "1235"}])

    monkeypatch.setattr(requests, "get", fake_get)
    out = tool.run(
        {
            "dataset_id": "jkcx-ndu8",
            "soql_query": (
                "SELECT event, count(*) AS n GROUP BY event ORDER BY n DESC LIMIT 5"
            ),
            # These should be IGNORED in favor of the full $query.
            "select_clause": "event, count(*)",
            "limit": 5,
        }
    )
    assert out["status"] == "success"
    qs = parse_qs(urlparse(captured["url"]).query)
    assert "$query" in qs
    # $query must NOT be mixed with $select / $limit (Socrata rejects that).
    assert "$select" not in qs
    assert "$limit" not in qs
    assert out["data"][0]["n"] == "1235"


def test_cdc_aggregate_missing_dataset_id():
    """A missing dataset_id returns a status=error envelope (no exception)."""
    tool = _cdc_tool()
    out = tool.run({"select_clause": "count(*)"})
    assert out["status"] == "error"
    assert "dataset_id" in out["error"]


def test_cdc_aggregate_http_error_returns_error(monkeypatch):
    """A 400 (bad SoQL) is returned as a status=error envelope, not raised."""
    tool = _cdc_tool()

    def fake_get(url, timeout=None):
        resp = _FakeResponse(
            status_code=400,
            text='{"message":"No such column: bogus"}',
        )
        return resp

    monkeypatch.setattr(requests, "get", fake_get)
    out = tool.run(
        {
            "dataset_id": "jkcx-ndu8",
            "select_clause": "bogus, count(*)",
            "group_clause": "bogus",
        }
    )
    assert out["status"] == "error"
    # Top-level error key matches the return_schema error branch.
    assert "error" in out
    assert "Request failed" in out["error"]


def test_cdc_aggregate_network_error_returns_error(monkeypatch):
    """A connection failure is returned as a status=error envelope, not raised."""
    tool = _cdc_tool()

    def boom(*args, **kwargs):
        raise requests.exceptions.ConnectionError("down")

    monkeypatch.setattr(requests, "get", boom)
    out = tool.run({"dataset_id": "jkcx-ndu8", "select_clause": "count(*)"})
    assert out["status"] == "error"
    assert "Request failed" in out["error"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
