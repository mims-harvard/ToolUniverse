"""Health Canada Drug Product Database tools: search by brand name, DIN and
active ingredient, and one product's full record. HTTP is faked with
responses recorded on 2026-11-18 (tests/fixtures/health_canada_dpd/README.md)."""

import json
from pathlib import Path

import pytest
import requests

from tooluniverse import health_canada_dpd_tool as D

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests" / "fixtures" / "health_canada_dpd"
CONFIGS = {
    c["name"]: c
    for c in json.loads(
        (
            ROOT / "src" / "tooluniverse" / "data" / "health_canada_dpd_tools.json"
        ).read_text()
    )
}
NOT_FOUND = object()


def _load(name):
    return json.loads((FIXTURES / name).read_text())


class _Response:
    def __init__(self, body, status=200):
        self.body, self.status_code = body, status

    def json(self):
        if isinstance(self.body, Exception):
            raise self.body
        return self.body


@pytest.fixture
def http(monkeypatch):
    """Serve recorded bodies by (resource, sorted query); 404 for the rest."""
    routes = {}
    calls = []

    def fake(url, params=None, timeout=None):
        resource = url.replace(D.DPD_BASE_URL + "/", "").strip("/")
        query = {k: v for k, v in (params or {}).items() if k not in ("lang", "type")}
        assert params["lang"] == "en" and params["type"] == "json"
        calls.append((resource, query))
        key = (resource, tuple(sorted((k, str(v)) for k, v in query.items())))
        body = routes.get(key, NOT_FOUND)
        if body is NOT_FOUND:
            return _Response(None, 404)
        return _Response(body)

    monkeypatch.setattr(D.requests, "get", fake)

    def route(resource, body, **query):
        routes[(resource, tuple(sorted((k, str(v)) for k, v in query.items())))] = body

    route.calls = calls
    return route


def _run(name, arguments):
    return D.HealthCanadaDPDTool(CONFIGS[name]).run(arguments)


def _serve_gleevec_73824(http):
    for resource in (
        "drugproduct",
        "activeingredient",
        "status",
        "form",
        "route",
        "schedule",
        "therapeuticclass",
        "pharmaceuticalstd",
    ):
        http(resource, _load(f"{resource}_73824.json"), id=73824)


def test_every_tool_names_its_operation():
    assert set(CONFIGS) == {
        "HealthCanadaDPD_search_products",
        "HealthCanadaDPD_search_by_ingredient",
        "HealthCanadaDPD_get_product",
    }
    for config in CONFIGS.values():
        assert config["type"] == "HealthCanadaDPDTool"
        assert config["name"].endswith(config["fields"]["operation"])


def test_search_by_brand_returns_every_status(http):
    http("drugproduct", _load("drugproduct_brand_gleevec.json"), brandname="gleevec")
    result = _run("HealthCanadaDPD_search_products", {"brand_name": "gleevec"})
    assert result["status"] == "success"
    assert [r["drug_code"] for r in result["data"]] == [68714, 73824, 73825]
    first = result["data"][0]
    assert first["din"] == "02244725"
    assert first["company"] == "NOVARTIS PHARMACEUTICALS CANADA INC"
    assert first["descriptor"] is None  # "" upstream
    assert result["metadata"]["total_matching"] == 3


def test_marketed_only_sends_status_2(http):
    http(
        "drugproduct",
        _load("drugproduct_brand_gleevec_marketed.json"),
        brandname="gleevec",
        status=2,
    )
    result = _run(
        "HealthCanadaDPD_search_products",
        {"brand_name": "gleevec", "marketed_only": True},
    )
    assert [r["drug_code"] for r in result["data"]] == [73824, 73825]


def test_search_by_din_pads_to_eight_digits(http):
    http("drugproduct", _load("drugproduct_din_02253275.json"), din="02253275")
    result = _run("HealthCanadaDPD_search_products", {"din": "2253275"})
    assert [r["drug_code"] for r in result["data"]] == [73824]


def test_limit_caps_rows_but_not_the_total(http):
    http("drugproduct", _load("drugproduct_brand_gleevec.json"), brandname="gleevec")
    result = _run(
        "HealthCanadaDPD_search_products", {"brand_name": "gleevec", "limit": 1}
    )
    assert len(result["data"]) == 1
    assert result["metadata"]["total_matching"] == 3


def test_no_match_is_an_empty_success(http):
    http("drugproduct", [], brandname="xyzzy")
    result = _run("HealthCanadaDPD_search_products", {"brand_name": "xyzzy"})
    assert result["status"] == "success" and result["data"] == []


@pytest.mark.parametrize(
    "arguments, message",
    [
        ({}, "brand_name"),
        ({"din": "ABC"}, "din must be"),
        ({"din": "123456789"}, "din must be"),
        ({"brand_name": "x", "limit": "many"}, "limit"),
    ],
)
def test_search_products_rejects_bad_input_without_a_call(http, arguments, message):
    result = _run("HealthCanadaDPD_search_products", arguments)
    assert result["status"] == "error"
    assert message in result["error"]
    assert http.calls == []


def test_search_by_ingredient_groups_rows_and_adds_product_names(http):
    http(
        "activeingredient",
        _load("activeingredient_imatinib.json"),
        ingredientname="imatinib",
    )
    for code in (68714, 73824, 73825):
        http("drugproduct", _load(f"drugproduct_{code}.json"), id=code)
    result = _run(
        "HealthCanadaDPD_search_by_ingredient", {"ingredient": "imatinib", "limit": 3}
    )
    assert result["status"] == "success"
    assert [r["drug_code"] for r in result["data"]] == [68714, 73824, 73825]
    row = result["data"][2]
    assert row["brand_name"] == "GLEEVEC" and row["din"] == "02253283"
    assert row["matched_ingredients"] == [
        {
            "ingredient": "IMATINIB (IMATINIB MESYLATE)",
            "strength": "400",
            "strength_unit": "MG",
            "dosage_value": None,
            "dosage_unit": None,
        }
    ]
    assert result["metadata"]["total_products"] == 6
    # one ingredient search plus one product lookup per returned row
    assert len(http.calls) == 4


def test_search_by_ingredient_caps_limit_at_25(http):
    http("activeingredient", [], ingredientname="x")
    result = _run(
        "HealthCanadaDPD_search_by_ingredient", {"ingredient": "x", "limit": 500}
    )
    assert result["status"] == "success" and result["data"] == []


def test_search_by_ingredient_requires_a_name(http):
    result = _run("HealthCanadaDPD_search_by_ingredient", {"ingredient": "  "})
    assert result["status"] == "error"
    assert http.calls == []


def test_get_product_joins_every_sub_resource(http):
    _serve_gleevec_73824(http)
    result = _run("HealthCanadaDPD_get_product", {"drug_code": 73824})
    assert result["status"] == "success"
    data = result["data"]
    assert data["brand_name"] == "GLEEVEC"
    assert data["active_ingredients"][0]["ingredient"] == "IMATINIB (IMATINIB MESYLATE)"
    assert data["active_ingredients"][0]["strength"] == "100"
    assert data["status"] == "Marketed"
    assert data["original_market_date"] == "2005-04-05"
    assert data["dosage_forms"] == ["Tablet"]
    assert data["routes"] == ["Oral"]
    assert data["schedules"] == ["PRESCRIPTION"]
    assert data["atc"] == [{"code": "L01EA01", "name": "IMATINIB"}]


def test_get_product_by_din_looks_up_the_code_first(http):
    http("drugproduct", _load("drugproduct_din_02253275.json"), din="02253275")
    _serve_gleevec_73824(http)
    result = _run("HealthCanadaDPD_get_product", {"din": "02253275"})
    assert result["data"]["drug_code"] == 73824
    assert http.calls[0] == ("drugproduct", {"din": "02253275"})


def test_get_product_reads_404_sub_resources_as_empty(http):
    http("drugproduct", _load("drugproduct_73824.json"), id=73824)
    result = _run("HealthCanadaDPD_get_product", {"drug_code": 73824})
    assert result["status"] == "success"
    data = result["data"]
    assert data["active_ingredients"] == []
    assert data["dosage_forms"] == [] and data["atc"] == []
    assert data["status"] is None
    assert data["pharmaceutical_standard"] is None


def test_unknown_drug_code_is_not_found_even_though_dpd_answers_200(http):
    """drugproduct/?id=<unknown> returns drug_code 0 and nulls, not a 404."""
    http("drugproduct", _load("drugproduct_unknown_id_58989.json"), id=58989)
    result = _run("HealthCanadaDPD_get_product", {"drug_code": 58989})
    assert result == {
        "status": "error",
        "error": "No Health Canada DPD product with drug_code 58989",
    }


def test_unknown_din_is_not_found(http):
    http("drugproduct", [], din="99999999")
    result = _run("HealthCanadaDPD_get_product", {"din": "99999999"})
    assert result["status"] == "error"
    assert "DIN 99999999" in result["error"]


@pytest.mark.parametrize(
    "arguments, message",
    [({}, "drug_code"), ({"drug_code": "gleevec"}, "integer"), ({"din": "x"}, "din")],
)
def test_get_product_rejects_bad_input(http, arguments, message):
    result = _run("HealthCanadaDPD_get_product", arguments)
    assert result["status"] == "error"
    assert message in result["error"]


def test_server_error_is_reported(monkeypatch):
    monkeypatch.setattr(
        D.requests, "get", lambda *a, **k: _Response({"Message": "boom"}, 500)
    )
    result = _run("HealthCanadaDPD_search_products", {"brand_name": "x"})
    assert result == {
        "status": "error",
        "error": "Health Canada DPD returned HTTP 500 for drugproduct",
    }


def test_timeout_is_an_error_not_an_exception(monkeypatch):
    def boom(*args, **kwargs):
        raise requests.exceptions.Timeout()

    monkeypatch.setattr(D.requests, "get", boom)
    result = _run("HealthCanadaDPD_get_product", {"drug_code": 1})
    assert result["status"] == "error"
    assert "timed out" in result["error"]
