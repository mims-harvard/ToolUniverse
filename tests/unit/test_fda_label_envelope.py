"""Round 026: FDALabelTool returns the standard {status, data, metadata} envelope.

Regression for Feature-026C-1: FDA_search_drug_labels previously returned a bare
list (framework-wrapped to {"result": [...]}), inconsistent with the project-wide
success envelope. All three FDALabelTool query types now return {status, data,
metadata} on success and {status: error, ...} on failure.
"""

from unittest.mock import patch

from tooluniverse.fda_label_tool import FDALabelTool, _ok


def _cfg(query_type):
    return {
        "name": f"FDA_{query_type}",
        "type": "FDALabelTool",
        "fields": {"endpoint": "https://api.fda.gov/drug/label.json", "query_type": query_type},
        "parameter": {"type": "object", "properties": {}},
    }


class _Resp:
    status_code = 200

    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def test_ok_helper_wraps_list_with_count():
    out = _ok([1, 2, 3], query="x")
    assert out["status"] == "success"
    assert out["data"] == [1, 2, 3]
    assert out["metadata"]["count"] == 3
    assert out["metadata"]["source"] == "openFDA drug label"
    assert out["metadata"]["query"] == "x"


def test_ok_helper_does_not_count_dict():
    out = _ok({"brand_name": "X"})
    assert out["status"] == "success"
    assert "count" not in out["metadata"]


def test_search_returns_standard_envelope():
    raw = {"results": [{"openfda": {"brand_name": ["AVYCAZ"]}, "indications_and_usage": ["use"]}]}
    tool = FDALabelTool(_cfg("search"))
    with patch("tooluniverse.fda_label_tool.requests.get", return_value=_Resp(raw)):
        out = tool.run({"drug_name": "Avycaz", "limit": 1})
    assert set(out) >= {"status", "data", "metadata"}
    assert out["status"] == "success"
    assert isinstance(out["data"], list)
    assert out["data"][0]["brand_name"] == "AVYCAZ"
    assert out["metadata"]["query"] == "Avycaz"


def test_search_missing_args_is_error_envelope():
    tool = FDALabelTool(_cfg("search"))
    out = tool.run({})
    assert out["status"] == "error"
    assert "drug_name" in out["error"]


def test_limit_is_optional_with_default():
    """`limit` must NOT be required: it has default=5 in code/schema, so the
    natural call FDA_search_drug_labels(drug_name=...) (no limit) must validate
    and run, not be rejected for a missing 'limit' property."""
    import json
    import os

    here = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    cfg_path = os.path.join(
        here, "src", "tooluniverse", "data", "openfda_label_tools.json"
    )
    cfgs = json.load(open(cfg_path))
    by_name = {t["name"]: t for t in cfgs}
    for name in ("FDA_search_drug_labels", "FDA_list_drug_classes"):
        required = by_name[name]["parameter"].get("required", [])
        assert "limit" not in required, f"{name} must not require 'limit'"
        assert by_name[name]["parameter"]["properties"]["limit"].get("default") == (
            5 if name == "FDA_search_drug_labels" else 20
        )


def test_list_classes_returns_standard_envelope():
    raw = {"results": [{"term": "Cephalosporin", "count": 12}]}
    tool = FDALabelTool(_cfg("list_classes"))
    with patch("tooluniverse.fda_label_tool.requests.get", return_value=_Resp(raw)):
        out = tool.run({"limit": 1})
    assert out["status"] == "success"
    assert out["data"] == [{"drug_class": "Cephalosporin", "count": 12}]
    assert out["metadata"]["count"] == 1
