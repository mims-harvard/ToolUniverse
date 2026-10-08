"""A drug name that misses only because of extra words is retried with the shorter name.

``FDA_get_dosage_and_storage_information_by_drug_name`` returned NOT_FOUND for
"BETHKIS (tobramycin)" and "OXERVATE (cenegermin-bkbj)", both real products
openFDA has labels for under "BETHKIS" and "OXERVATE". After every existing
stage has come back NOT_FOUND, the label tools now retry once per shorter name:
the two halves of a "BRAND (generic)" name, or the name without trailing
dosage-form words and strengths ("verapamil SR", "metformin 500 mg tablets").
A found result, or any error other than NOT_FOUND, is never retried.

Everything mocks the HTTP layer -- no network.
"""

import json
import sys
import types
import urllib.parse
from unittest.mock import patch

import pytest

from tooluniverse.openfda_tool import (
    FDADrugLabelTool,
    _drug_name_candidates,
    _retry_with_normalised_names,
)

NOT_FOUND = {"error": {"code": "NOT_FOUND", "message": "No matches found!"}}
FOUND = {"results": [{"x": 1}]}
_DRUG_LIST_MODULE = "tooluniverse.data.fda_drugs_with_brand_generic_names_for_tool"


@pytest.mark.parametrize(
    "name, expected",
    [
        ("verapamil SR", ["verapamil"]),
        ("cyanocobalamin nasal spray", ["cyanocobalamin"]),
        ("dalfampridine extended-release", ["dalfampridine"]),
        ("Premarin Vaginal Cream", ["Premarin"]),
        ("Zerviate eye drops", ["Zerviate"]),
        ("metformin 500 mg tablets", ["metformin"]),
        ("BETHKIS (tobramycin)", ["BETHKIS", "tobramycin"]),
        ("OXERVATE (cenegermin-bkbj)", ["OXERVATE", "cenegermin-bkbj"]),
    ],
)
def test_shorter_names_most_specific_first(name, expected):
    assert _drug_name_candidates(name) == expected


@pytest.mark.parametrize(
    "name", ["St. John's Wort", "aluminum-based antacid", "warfarin", "SHAROBEL"]
)
def test_a_name_with_nothing_to_remove_is_never_guessed_at(name):
    assert _drug_name_candidates(name) == []


@pytest.mark.parametrize(
    "result", [FOUND, {"error": {"code": "SERVER_ERROR"}}, "plain text", None]
)
def test_only_a_not_found_is_retried(result):
    calls = []

    def run(args):
        calls.append(args)
        return FOUND

    assert (
        _retry_with_normalised_names(result, {"drug_name": "verapamil SR"}, run)
        is result
    )
    assert calls == []


def test_the_first_retry_that_finds_a_label_wins_and_says_what_was_searched():
    calls = []

    def run(args):
        calls.append(args["drug_name"])
        if args["drug_name"] == "BETHKIS":
            return NOT_FOUND
        return {"results": [{"x": 1}], "note": "broadened"}

    out = _retry_with_normalised_names(
        NOT_FOUND, {"drug_name": "BETHKIS (tobramycin)", "limit": 2}, run
    )
    assert calls == ["BETHKIS", "tobramycin"]
    assert out["name_searched_as"] == "tobramycin"
    assert out["name_normalised_from"] == "BETHKIS (tobramycin)"
    assert out["note"].startswith("broadened ")
    assert "searched as 'tobramycin'" in out["note"]
    assert "bracketed second name" in out["note"]


def test_other_arguments_are_passed_through():
    seen = []

    def run(args):
        seen.append(args)
        return FOUND

    _retry_with_normalised_names(
        NOT_FOUND, {"drug_name": "verapamil SR", "limit": 3, "skip": 1}, run
    )
    assert seen == [{"drug_name": "verapamil", "limit": 3, "skip": 1}]


def test_when_every_retry_fails_the_original_not_found_comes_back():
    args = {"drug_name": "verapamil SR"}
    assert _retry_with_normalised_names(NOT_FOUND, args, lambda a: NOT_FOUND) is (
        NOT_FOUND
    )
    erroring = {"error": {"code": "SERVER_ERROR"}}
    assert _retry_with_normalised_names(NOT_FOUND, args, lambda a: erroring) is (
        NOT_FOUND
    )


def test_a_not_found_serialised_as_json_is_recognised():
    out = _retry_with_normalised_names(
        json.dumps(NOT_FOUND), {"drug_name": "verapamil SR"}, lambda a: dict(FOUND)
    )
    assert out["name_searched_as"] == "verapamil"


def test_retries_are_capped():
    calls = []

    def run(args):
        calls.append(args["drug_name"])
        return NOT_FOUND

    _retry_with_normalised_names(
        NOT_FOUND, {"drug_name": "BETHKIS (tobramycin)"}, run, max_retries=1
    )
    assert calls == ["BETHKIS"]


def test_it_never_raises_and_never_loses_the_original():
    def boom(args):
        raise RuntimeError("network")

    assert (
        _retry_with_normalised_names(NOT_FOUND, {"drug_name": "verapamil SR"}, boom)
        is NOT_FOUND
    )
    for arguments in ({}, {"drug_name": None}, {"drug_name": "  "}):
        assert _retry_with_normalised_names(NOT_FOUND, arguments, boom) is NOT_FOUND


# --- through the real tool --------------------------------------------------


@pytest.fixture
def tiny_drug_list(monkeypatch):
    """Stub the 6 MB closest-name table the spelling stage would otherwise scan."""
    stub = types.ModuleType(_DRUG_LIST_MODULE)
    stub.drug_list = [{"brand_name": "MOTRIN", "generic_name": "IBUPROFEN"}]
    monkeypatch.setitem(sys.modules, _DRUG_LIST_MODULE, stub)
    return stub


class _FakeResponse:
    status_code = 200

    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


def _tool():
    return FDADrugLabelTool(
        {
            "name": "FDA_get_dosage_and_storage_information_by_drug_name",
            "description": "dose",
            "type": "FDADrugLabel",
            "parameter": {
                "type": "object",
                "properties": {"drug_name": {"type": "string"}},
                "required": ["drug_name"],
            },
            "fields": {
                "search_fields": {
                    "drug_name": ["openfda.brand_name", "openfda.generic_name"]
                },
                "return_fields": ["dosage_and_administration", "how_supplied"],
            },
        }
    )


def _bethkis_only():
    """openFDA knows BETHKIS by its brand name alone."""
    seen = []
    label = {
        "openfda": {"brand_name": ["BETHKIS"], "generic_name": ["TOBRAMYCIN"]},
        "dosage_and_administration": ["300 mg inhaled twice daily ..."],
        "how_supplied": ["Ampules ..."],
    }

    def fake_get(url, *args, **kwargs):
        seen.append(urllib.parse.unquote_plus(url))
        if "BETHKIS" in seen[-1].upper() and "TOBRAMYCIN" not in seen[-1].upper():
            return _FakeResponse(
                {
                    "meta": {"results": {"skip": 0, "limit": 3, "total": 1}},
                    "results": [label],
                }
            )
        return _FakeResponse(NOT_FOUND)

    return fake_get, seen


def test_the_label_tool_finds_a_bracketed_brand_name(tiny_drug_list):
    fake_get, _ = _bethkis_only()
    with patch("tooluniverse.openfda_tool.requests.get", side_effect=fake_get):
        out = _tool().run({"drug_name": "BETHKIS (tobramycin)", "limit": 3})
    assert out["name_searched_as"] == "BETHKIS"
    assert out["name_normalised_from"] == "BETHKIS (tobramycin)"
    assert out["results"][0]["openfda.brand_name"] == ["BETHKIS"]


def test_a_name_that_matches_first_time_issues_no_retry(tiny_drug_list):
    fake_get, seen = _bethkis_only()
    with patch("tooluniverse.openfda_tool.requests.get", side_effect=fake_get):
        out = _tool().run({"drug_name": "BETHKIS", "limit": 3})
    assert "name_searched_as" not in out
    assert len(seen) == 1
