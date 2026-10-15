"""RxNorm_get_exact_concepts: exact matching, every match reported, no choice made.

The payloads below are the live RxNorm responses for these names, trimmed to
the fields the tool reads. All network calls are mocked.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import jsonschema
import pytest
import requests

from tooluniverse.rxnorm_extended_tool import MAX_EXACT_CONCEPTS, RxNormExtendedTool

pytestmark = pytest.mark.unit

BASE = "https://rxnav.nlm.nih.gov/REST/"
CONFIG = json.loads(
    (
        Path(__file__).resolve().parents[2]
        / "src/tooluniverse/data/rxnorm_extended_tools.json"
    ).read_text()
)
ENTRY = next(t for t in CONFIG if t["name"] == "RxNorm_get_exact_concepts")

NAMES = {
    "acetaminophen": ["161"],
    "paracetamol": ["161"],
    "tylenol": ["202433"],
    "heparin": ["235473", "5224"],
    "ceftriaxon": [],
}
PROPERTIES = {
    "161": {
        "rxcui": "161",
        "name": "acetaminophen",
        "synonym": "",
        "tty": "IN",
        "language": "ENG",
        "suppress": "N",
        "umlscui": "",
    },
    "202433": {
        "rxcui": "202433",
        "name": "Tylenol",
        "synonym": "",
        "tty": "BN",
        "language": "ENG",
        "suppress": "N",
        "umlscui": "",
    },
    "235473": {
        "rxcui": "235473",
        "name": "heparin, porcine",
        "synonym": "",
        "tty": "PIN",
        "language": "ENG",
        "suppress": "N",
        "umlscui": "",
    },
    "5224": {
        "rxcui": "5224",
        "name": "heparin",
        "synonym": "",
        "tty": "IN",
        "language": "ENG",
        "suppress": "N",
        "umlscui": "",
    },
}


def _response(payload, status_code=200):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = payload
    resp.raise_for_status = MagicMock()
    return resp


def _rxnorm(names=NAMES, properties=PROPERTIES):
    def get(url, params=None, timeout=None):
        if url == BASE + "rxcui.json":
            ids = names.get(params["name"].lower(), [])
            return _response({"idGroup": {"rxnormId": ids}} if ids else {"idGroup": {}})
        rxcui = url[len(BASE + "rxcui/") : -len("/properties.json")]
        return _response({"properties": properties[rxcui]})

    return get


def _run(drug_name, get=None):
    tool = RxNormExtendedTool({"fields": {"operation": "get_exact_concepts"}})
    with patch(
        "tooluniverse.rxnorm_extended_tool.requests.get", side_effect=get or _rxnorm()
    ) as mock:
        return tool.run({"drug_name": drug_name}), mock


def _valid(result):
    jsonschema.validate(result, ENTRY["return_schema"])
    return result


def test_config_entry_routes_to_this_operation_and_requires_a_name():
    assert ENTRY["type"] == "RxNormExtendedTool"
    assert ENTRY["fields"]["operation"] == "get_exact_concepts"
    assert ENTRY["parameter"]["required"] == ["drug_name"]


def test_lookup_uses_exact_mode_restricted_to_active_rxnorm():
    _, mock = _run("acetaminophen")
    url, kwargs = mock.call_args_list[0].args[0], mock.call_args_list[0].kwargs
    assert url == BASE + "rxcui.json"
    assert kwargs["params"] == {"name": "acetaminophen", "search": 0, "allsrc": 0}


def test_one_active_ingredient_resolves_with_its_canonical_name():
    result, _ = _run("acetaminophen")
    data = _valid(result)["data"]
    assert result["status"] == "success"
    assert data["resolution"] == "unique_active_IN_concept"
    assert data["canonical_ingredient_name"] == "acetaminophen"
    assert data["all_rxcuis"] == ["161"]
    assert data["concepts"][0]["term_type_label"] == "Ingredient (generic)"


def test_a_synonym_resolves_to_the_concept_rxnorm_names_not_to_the_input():
    data = _valid(_run("paracetamol")[0])["data"]
    assert data["input_name"] == "paracetamol"
    assert data["canonical_ingredient_name"] == "acetaminophen"


def test_a_brand_name_is_reported_but_never_resolved_as_an_ingredient():
    data = _valid(_run("Tylenol")[0])["data"]
    assert data["resolution"] == "requires_identity_review"
    assert data["canonical_ingredient_name"] is None
    assert data["concepts"][0]["tty"] == "BN"


def test_several_matches_are_all_returned_and_none_is_chosen():
    data = _valid(_run("heparin")[0])["data"]
    assert data["resolution"] == "multiple_concepts"
    assert data["canonical_ingredient_name"] is None
    assert {c["tty"] for c in data["concepts"]} == {"IN", "PIN"}


def test_a_misspelling_is_not_corrected_into_another_concept():
    result, mock = _run("ceftriaxon")
    data = _valid(result)["data"]
    assert data["resolution"] == "no_exact_concept"
    assert data["all_rxcuis"] == [] and data["concepts"] == []
    assert mock.call_count == 1


def test_too_many_matches_are_reported_without_fetching_any_properties():
    ids = [str(i) for i in range(1, MAX_EXACT_CONCEPTS + 2)]
    result, mock = _run("broad", get=_rxnorm(names={"broad": ids}, properties={}))
    data = _valid(result)["data"]
    assert data["resolution"] == "multiple_concepts"
    assert data["all_rxcuis"] == ids and data["concepts"] == []
    assert "properties_not_retrieved" in data
    assert mock.call_count == 1


def test_surrounding_whitespace_is_the_only_normalization():
    result, mock = _run("  acetaminophen ")
    assert mock.call_args_list[0].kwargs["params"]["name"] == "acetaminophen"
    assert result["data"]["input_name"] == "  acetaminophen "
    assert result["data"]["query_name"] == "acetaminophen"


@pytest.mark.parametrize("value", [None, "", "   ", 7])
def test_a_missing_or_blank_name_is_an_error(value):
    tool = RxNormExtendedTool({"fields": {"operation": "get_exact_concepts"}})
    with patch("tooluniverse.rxnorm_extended_tool.requests.get") as mock:
        result = tool.run({"drug_name": value})
    assert result["status"] == "error"
    mock.assert_not_called()


def test_a_network_failure_is_an_error_that_keeps_the_request_trail():
    def get(url, params=None, timeout=None):
        raise requests.exceptions.ConnectionError("unreachable")

    result, _ = _run("acetaminophen", get=get)
    assert result["status"] == "error"
    assert "RxNorm API request failed" in result["error"]
    assert result["metadata"]["requests"][0]["params"]["name"] == "acetaminophen"
    _valid(result)


def test_properties_for_a_different_concept_are_rejected():
    wrong = {"161": dict(PROPERTIES["5224"])}
    result, _ = _run("acetaminophen", get=_rxnorm(properties=wrong))
    assert result["status"] == "error"
    assert "mismatched" in result["error"]
    assert result["data"]["resolution"] is None


def test_a_malformed_identifier_list_is_an_error_not_an_empty_answer():
    def get(url, params=None, timeout=None):
        return _response({"idGroup": {"rxnormId": ["161", "not-an-id"]}})

    result, _ = _run("acetaminophen", get=get)
    assert result["status"] == "error"
    assert "malformed" in result["error"]
