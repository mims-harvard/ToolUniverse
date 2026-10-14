"""Label tools select a product's route, and say which other sections the returned labels carry.

One generic name often covers products of several routes. Measured live on
openFDA (2026-10-14): ``FDA_get_drug_interactions_by_drug_name`` for "atropine
sulfate" returned injection labels and the diphenoxylate/atropine tablets, and
not the eye drops whose label says atropine and MAO inhibitors should not be
combined; budesonide returned capsules and inhalers for a rectal-foam question,
labetalol its tablets for an intravenous one. The label tools (both families)
now take an optional ``route`` in openFDA's own spelling, applied to every query
they send; labels whose openFDA block names no route match on their description
or carton text.

A label tool also returns one section only, so a caller who asked a drug's
interactions never learned that the same label carries a boxed warning or a
pregnancy section. The name-based label tools now return ``other_section_tools``:
each decision section the returned labels carry, the tool that returns it and
how many of the labels carry it.

Everything mocks the HTTP layer -- no network.
"""

import json
import sys
import types
import urllib.parse
from pathlib import Path
from unittest.mock import patch

import pytest

from tooluniverse.fda_label_routes import LABEL_ROUTES, normalise_route, route_clause
from tooluniverse.fda_label_tool import FDALabelTool
from tooluniverse.openfda_tool import (
    LABEL_DECISION_SECTIONS,
    FDADrugLabelTool,
    _section_tool,
)

DATA = Path(__file__).resolve().parents[2] / "src/tooluniverse/data"
NOT_FOUND = {"error": {"code": "NOT_FOUND", "message": "No matches found!"}}
ROUTE_FILTER = 'openfda.route:"OPHTHALMIC"'
_DRUG_LIST_MODULE = "tooluniverse.data.fda_drugs_with_brand_generic_names_for_tool"


def _configs(name="fda_drug_labeling_tools.json"):
    return {t["name"]: t for t in json.loads((DATA / name).read_text())}


class _FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def _found(records):
    return {
        "meta": {"results": {"skip": 0, "limit": 100, "total": len(records)}},
        "results": records,
    }


def _label(route=None, **sections):
    record = {"openfda": {"generic_name": ["ATROPINE SULFATE"]}}
    if route:
        record["openfda"]["route"] = [route]
    record.update(sections)
    return record


@pytest.fixture(autouse=True)
def tiny_drug_list(monkeypatch):
    """Stub the 6 MB closest-name table the spelling stage would otherwise scan."""
    stub = types.ModuleType(_DRUG_LIST_MODULE)
    stub.drug_list = [{"brand_name": "MOTRIN", "generic_name": "IBUPROFEN"}]
    monkeypatch.setitem(sys.modules, _DRUG_LIST_MODULE, stub)


def _run(arguments, respond, tool="FDA_get_drug_interactions_by_drug_name"):
    """Run a label tool with `respond(decoded_url) -> payload`; return (result, urls)."""
    urls = []

    def fake_get(url, *args, **kwargs):
        urls.append(urllib.parse.unquote_plus(url))
        return _FakeResponse(respond(urls[-1]))

    with patch("tooluniverse.openfda_tool.requests.get", side_effect=fake_get):
        return FDADrugLabelTool(_configs()[tool]).run(arguments), urls


# --- the route --------------------------------------------------------------


@pytest.mark.parametrize(
    "given, expected",
    [
        ("ophthalmic", "OPHTHALMIC"),
        (" Intravenous ", "INTRAVENOUS"),
        ("inhalation", "RESPIRATORY (INHALATION)"),
        ("RESPIRATORY (INHALATION)", "RESPIRATORY (INHALATION)"),
        ("otic", "AURICULAR (OTIC)"),
        ("intra-articular", "INTRA-ARTICULAR"),
    ],
)
def test_route_takes_openfda_spelling_in_any_case(given, expected):
    assert normalise_route(given) == (expected, None)


@pytest.mark.parametrize("given", ["eye", "IV", "eye drops", "by mouth"])
def test_any_other_route_is_rejected_before_a_request(given):
    out, urls = _run({"drug_name": "atropine sulfate", "route": given}, lambda u: {})
    assert out["status"] == "error"
    assert f"Unknown route '{given}'" in out["error"]
    assert all(r in out["error"] for r in LABEL_ROUTES)
    assert urls == []


def test_labels_without_an_openfda_route_match_on_their_own_text():
    clause = route_clause("OPHTHALMIC")
    assert ROUTE_FILTER in clause
    assert "_missing_:openfda.route" in clause
    assert 'description:"ophthalmic"' in clause
    assert 'package_label_principal_display_panel:"ophthalmic"' in clause
    assert 'description:"inhalation"' in route_clause("RESPIRATORY (INHALATION)")


def test_the_route_filters_the_query_and_is_not_sent_as_a_url_parameter():
    out, urls = _run(
        {"drug_name": "atropine sulfate", "route": "ophthalmic", "limit": 5},
        lambda u: _found([_label("OPHTHALMIC", drug_interactions=["MAOI ..."])]),
    )
    assert len(urls) == 1
    search = urls[0].split("search=", 1)[1].split("&", 1)[0]
    assert ROUTE_FILTER in search and '"ATROPINE SULFATE"' in search
    assert "&route=" not in urls[0] and "?route=" not in urls[0]
    assert out["route_applied"] == "OPHTHALMIC"
    assert out["results"][0]["drug_interactions"] == ["MAOI ..."]


def test_every_query_stage_keeps_the_route():
    # NOT_FOUND everywhere: the tool works through its broadening stages and the
    # shorter-name retry, then looks the name up once more WITHOUT the route to say
    # which routes it has. Every request before that lookup carries the route.
    out, urls = _run(
        {"drug_name": "atropine sulfate ophthalmic", "route": "OPHTHALMIC"},
        lambda u: NOT_FOUND,
    )
    with_route = [i for i, u in enumerate(urls) if ROUTE_FILTER in u]
    without = [i for i, u in enumerate(urls) if ROUTE_FILTER not in u]
    assert len(with_route) >= 3  # first query, broadening stages, retry
    assert without and min(without) > max(with_route)
    assert out["error"]["code"] == "NOT_FOUND"


def test_no_label_under_the_route_says_which_routes_the_name_has():
    def respond(url):
        if ROUTE_FILTER in url:
            return NOT_FOUND
        return _found(
            [
                _label("INTRAVENOUS", drug_interactions=["mexiletine"]),
                _label("INTRAVENOUS", drug_interactions=["mexiletine."]),
                _label("ORAL", drug_interactions=["alcohol"]),
            ]
        )

    out, _ = _run({"drug_name": "atropine sulfate", "route": "ophthalmic"}, respond)
    assert out["error"]["code"] == "NOT_FOUND"
    assert out["route_applied"] == "OPHTHALMIC"
    assert out["routes_found_without_route"] == {"INTRAVENOUS": 2, "ORAL": 1}
    assert (
        "No label of 'atropine sulfate' matched route OPHTHALMIC" in out["route_note"]
    )
    assert "INTRAVENOUS 2, ORAL 1" in out["route_note"]


def test_the_lookup_without_the_route_retries_shorter_names_and_ignores_the_limit():
    # "atropine sulfate ophthalmic" matches no name; "atropine sulfate" does.
    def respond(url):
        if ROUTE_FILTER in url or "OPHTHALMIC" in url.upper():
            return NOT_FOUND
        return _found([_label("ORAL", drug_interactions=["x"])] * 5)

    out, urls = _run(
        {"drug_name": "atropine sulfate ophthalmic", "route": "OPHTHALMIC", "limit": 1},
        respond,
    )
    assert out["routes_found_without_route"] == {"ORAL": 5}
    assert "5 label(s) matched" in out["route_note"]
    assert "limit=100" in urls[-1]


def test_a_name_with_no_label_at_all_is_not_blamed_on_the_route():
    out, _ = _run({"drug_name": "notadrug", "route": "ORAL"}, lambda u: NOT_FOUND)
    assert out["routes_found_without_route"] == {}
    assert "the name itself found no label" in out["route_note"]


def test_without_a_route_nothing_about_routes_is_added():
    out, urls = _run(
        {"drug_name": "atropine sulfate", "limit": 5},
        lambda u: _found([_label("INTRAVENOUS", drug_interactions=["x"])]),
    )
    assert "route_applied" not in out and "routes_found_without_route" not in out
    assert "openfda.route:" not in urls[0]


def test_a_tool_that_searches_on_route_keeps_using_it():
    out, urls = _run(
        {"route": "ORAL", "limit": 2},
        lambda u: _found([dict(_label("ORAL"), route=["ORAL"])]),
        tool="FDA_get_drug_names_by_route",
    )
    assert len(urls) == 1 and '"ORAL"' in urls[0]
    assert "_missing_:openfda.route" not in urls[0]  # no product filter added
    assert "route_applied" not in out and out.get("status") != "error"


def test_every_label_section_tool_declares_the_route():
    for tool in _configs().values():
        if tool.get("type") != "FDADrugLabel":
            continue
        props = tool["parameter"]["properties"]
        if (
            "drug_name" not in tool["fields"].get("search_fields", {})
            or "skip" not in props
        ):
            continue
        assert props["route"]["type"] == ["string", "null"], tool["name"]
        assert "OPHTHALMIC" in props["route"]["description"], tool["name"]
        assert "route" not in tool["parameter"].get("required", []), tool["name"]
    for name in ("FDA_search_drug_labels", "FDA_get_drug_label"):
        props = _configs("openfda_label_tools.json")[name]["parameter"]["properties"]
        assert props["route"]["type"] == ["string", "null"], name


def test_the_label_window_points_at_the_route():
    rows = [_label("ORAL", drug_interactions=[f"oral {i}"]) for i in range(9)] + [
        _label("OPHTHALMIC", drug_interactions=["eye"])
    ]
    out, _ = _run({"drug_name": "atropine sulfate"}, lambda u: _found(rows))
    assert "call again with route" in out["label_window_note"]


# --- the other sections ---------------------------------------------------------


def test_the_response_names_the_other_decision_sections_and_their_tools():
    record = _label(
        "INTRAVENOUS",
        drug_interactions=["mexiletine ..."],
        pregnancy=["Animal reproduction studies ..."],
        boxed_warning=["WARNING ..."],
        contraindications=[],
        description=["Atropine sulfate injection ..."],
    )
    other = _label("INTRAVENOUS", drug_interactions=["..."], pregnancy=["..."])
    out, _ = _run(
        {"drug_name": "atropine sulfate", "limit": 3}, lambda u: _found([record, other])
    )
    # label order, the requested section left out, an empty section left out, only
    # decision sections (description is not one), and names only -- no content
    assert out["other_section_tools"] == {
        "boxed_warning": {
            "tool": "FDA_get_boxed_warning_info_by_drug_name",
            "labels": 1,
        },
        "pregnancy": {
            "tool": "FDA_get_pregnancy_effects_info_by_drug_name",
            "labels": 2,
        },
    }
    assert all(
        "other_sections_present" not in r and "pregnancy" not in r
        for r in out["results"]
    )
    assert "Of the 2 label(s) returned" in out["other_sections_note"]


def test_sections_already_attached_under_their_own_key_are_not_listed_again():
    # a PLR label with no 'drug_interactions' gets its warnings_and_cautions
    # attached as the related section; it must not also be listed as "other"
    record = _label(
        "ORAL",
        warnings_and_cautions=["5.1 Serotonin syndrome ..."],
        drug_interactions=None,
        overdosage=["..."],
    )
    out, _ = _run(
        {"drug_name": "atropine sulfate", "limit": 3}, lambda u: _found([record])
    )
    assert out["results"][0].get("related_sections_present") == [
        "warnings_and_cautions"
    ]
    assert list(out["other_section_tools"]) == ["overdosage"]


def test_the_tools_named_are_for_the_labels_actually_returned():
    # no caller limit: the window shows 8 of 10 labels; only label 10 has a boxed warning
    rows = [
        _label("ORAL", drug_interactions=[f"x {i}"], overdosage=["y"]) for i in range(9)
    ]
    rows.append(_label("ORAL", drug_interactions=["z"], boxed_warning=["WARNING"]))
    out, _ = _run({"drug_name": "atropine sulfate"}, lambda u: _found(rows))
    assert len(out["results"]) == 8
    assert out["other_section_tools"] == {
        "overdosage": {"tool": "FDA_get_overdosage_info_by_drug_name", "labels": 8}
    }


def test_no_other_sections_no_extra_keys():
    out, _ = _run(
        {"drug_name": "atropine sulfate", "limit": 3},
        lambda u: _found([_label("ORAL", drug_interactions=["x"])]),
    )
    assert "other_section_tools" not in out and "other_sections_note" not in out


def test_reverse_lookup_tools_are_not_given_section_tools():
    record = _label("ORAL", indications_and_usage=["hypertension"], boxed_warning=["W"])
    out, _ = _run(
        {"indication": "hypertension", "limit": 2},
        lambda u: _found([record]),
        tool="FDA_get_drug_names_by_indication",
    )
    assert "other_section_tools" not in out
    assert all("other_sections_present" not in r for r in out.get("results", []))


def test_every_decision_section_has_a_tool_that_returns_it():
    configs = _configs()
    for section in LABEL_DECISION_SECTIONS:
        tool = _section_tool(section)
        assert tool in configs, (section, tool)
        assert section in configs[tool]["fields"]["return_fields"], (section, tool)
        assert "drug_name" in configs[tool]["fields"]["search_fields"], tool


# --- FDALabelTool (FDA_search_drug_labels / FDA_get_drug_label) -----------------


def _run_label_tool(query_type, arguments, respond):
    issued = []

    def fake_get(url, params=None, timeout=None, headers=None, **kwargs):
        issued.append(params["search"])
        payload = respond(params["search"])
        if payload is None:
            return _FakeResponse({"error": {"code": "NOT_FOUND"}}, status_code=404)
        return _FakeResponse({"results": payload})

    cfg = {
        "name": f"FDA_{query_type}",
        "type": "FDALabelTool",
        "fields": {"query_type": query_type},
        "parameter": {"type": "object", "properties": {}},
    }
    with patch("tooluniverse.fda_label_tool.requests.get", side_effect=fake_get):
        return FDALabelTool(cfg).run(arguments), issued


def test_label_tool_applies_the_route_to_every_name_query():
    eye = {
        "id": "eye",
        "openfda": {"generic_name": ["ATROPINE SULFATE"], "route": ["OPHTHALMIC"]},
    }
    out, issued = _run_label_tool(
        "get",
        {"drug_name": "atropine sulfate", "route": "ophthalmic"},
        lambda q: [eye] if 'openfda.brand_name:"atropine sulfate"' in q else None,
    )
    assert out["status"] == "success" and out["data"]["route"] == "OPHTHALMIC"
    assert out["metadata"]["route"] == "OPHTHALMIC"
    assert issued and all(
        q.endswith("AND " + route_clause("OPHTHALMIC")) for q in issued
    )


def test_label_tool_without_a_label_for_the_route_says_so():
    out, issued = _run_label_tool(
        "search", {"drug_name": "atropine sulfate", "route": "RECTAL"}, lambda q: None
    )
    assert out["status"] == "success" and out["data"] == []
    assert "No label of this drug matched route RECTAL" in out["suggestion"]
    assert all(route_clause("RECTAL") in q for q in issued)
    out, _ = _run_label_tool(
        "get", {"drug_name": "atropine sulfate", "route": "RECTAL"}, lambda q: None
    )
    assert out["error"].endswith("with route RECTAL")


def test_label_tool_rejects_an_unknown_route_and_ignores_a_missing_one():
    out, issued = _run_label_tool(
        "get", {"drug_name": "x", "route": "eye"}, lambda q: None
    )
    assert out["status"] == "error" and "Unknown route 'eye'" in out["error"]
    assert issued == []
    _, issued = _run_label_tool(
        "search", {"drug_name": "x", "route": None}, lambda q: None
    )
    assert issued and not any("openfda.route" in q for q in issued)
