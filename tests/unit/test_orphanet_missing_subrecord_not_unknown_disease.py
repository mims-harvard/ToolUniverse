"""Regression guard: Orphanet_get_phenotypes reported a missing sub-record as
"this disease does not exist".

Confirmed live for ORPHA:1247 (Schistosomiasis), a current, valid code:

    GET https://api.orphadata.com/rd-phenotypes/orphacodes/1247   -> HTTP 404
    GET https://api.orphadata.com/rd-phenotypes/orphacodes/558     -> HTTP 200
    GET https://api.orphadata.com/rd-phenotypes/orphacodes/99999999 -> HTTP 404

The 404 body is byte-identical for the unknown code and for the valid-but-
unannotated one ({"error":{"code":404,"type":"Query not found"}}), so the
dataset endpoint alone cannot tell them apart. _get_phenotypes blanket-
converted that 404 into "Disease ORPHA:1247 not found. Use
Orphanet_search_diseases to find a valid ORPHA code." -- a false statement
whose advice loops (that search returns 1247 again), while four sibling
tools resolve the same code happily (get_disease, get_icd_mapping,
get_natural_history, search_diseases).

The discriminator is the RDcode Name endpoint, already used by the sibling
operations via _orpha_code_exists (Fix-R20D-1). Confirmed live:

    GET https://api.orphacode.org/EN/ClinicalEntity/orphacode/1247/Name
        -> HTTP 200 {"ORPHAcode":1247,"Preferred term":"Schistosomiasis",...}
    GET https://api.orphacode.org/EN/ClinicalEntity/orphacode/99999999/Name
        -> HTTP 404 "Query not found"

Fixed additively: the status stays "error" in both cases (Orphadata does not
expose "zero phenotypes" as distinct from "no record", so fabricating an
empty phenotype list would not be honest), the unknown-code message is
preserved verbatim, and the valid-code branch now names what is actually
missing and points at sibling tools instead of at a search loop.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.orphanet_tool import OrphanetTool

pytestmark = pytest.mark.unit


def _tool():
    return OrphanetTool({"name": "Orphanet_get_phenotypes"})


def _resp(status_code, json_body=None):
    r = MagicMock()
    r.status_code = status_code
    r.json.return_value = json_body if json_body is not None else {}
    if status_code >= 400:
        import requests

        r.raise_for_status = MagicMock(
            side_effect=requests.exceptions.HTTPError(response=r)
        )
    else:
        r.raise_for_status = MagicMock()
    return r


def _route(name_response):
    """rd-phenotypes 404s; the RDcode Name endpoint answers `name_response`."""

    def fake_get(url, **kwargs):
        if "ClinicalEntity" in url:
            return name_response
        return _resp(404, {"error": {"code": 404, "type": "Query not found"}})

    return fake_get


def _phenotypes(orpha_code, name_response):
    with patch(
        "tooluniverse.orphanet_tool.requests.get", side_effect=_route(name_response)
    ):
        return _tool().run({"operation": "get_phenotypes", "orpha_code": orpha_code})


# --- the core bug: valid code, no rd-phenotypes record ----------------------


def test_valid_code_missing_phenotypes_does_not_claim_disease_not_found():
    result = _phenotypes(
        "1247", _resp(200, {"ORPHAcode": 1247, "Preferred term": "Schistosomiasis"})
    )

    assert result["status"] == "error"
    message = result["error"]
    assert "not found" not in message.lower()
    assert "does not exist" not in message.lower()


def test_valid_code_missing_phenotypes_names_what_is_actually_missing():
    result = _phenotypes(
        "1247", _resp(200, {"ORPHAcode": 1247, "Preferred term": "Schistosomiasis"})
    )

    message = result["error"].lower()
    assert "phenotype annotations" in message
    assert "rd-phenotypes" in message
    assert "1247" in result["error"]
    # The resolved preferred term proves the code really is live.
    assert "Schistosomiasis" in result["error"]


def test_valid_code_missing_phenotypes_does_not_loop_caller_back_to_search():
    """Following the old advice returned ORPHA:1247 again. The message must
    point at sibling tools that do hold data for the code instead."""
    result = _phenotypes(
        "1247", _resp(200, {"ORPHAcode": 1247, "Preferred term": "Schistosomiasis"})
    )

    message = result["error"]
    assert "Orphanet_search_diseases" not in message
    assert "Orphanet_get_disease" in message
    assert "Orphanet_get_natural_history" in message
    assert "Orphanet_get_icd_mapping" in message


def test_missing_preferred_term_still_produces_a_usable_message():
    """If the Name endpoint 200s without a usable term, the message must not
    grow an empty '()' and must still avoid the not-found claim."""
    result = _phenotypes("1247", _resp(200, {"ORPHAcode": 1247}))

    assert result["status"] == "error"
    assert "()" not in result["error"]
    assert "not found" not in result["error"].lower()
    assert "phenotype annotations" in result["error"].lower()


# --- the genuinely-unknown-code path must not regress ----------------------


def test_unknown_orpha_code_still_reports_disease_not_found():
    """The RDcode Name endpoint 404s only for a code that truly does not
    exist -- that path keeps its original message verbatim."""
    result = _phenotypes("99999999", _resp(404))

    assert result["status"] == "error"
    assert result["error"] == (
        "Disease ORPHA:99999999 not found. Use Orphanet_search_diseases to "
        "find a valid ORPHA code."
    )


def test_network_failure_on_discriminator_does_not_fabricate_not_found():
    """"Can't tell" must never become "disease does not exist"."""
    import requests

    def fake_get(url, **kwargs):
        if "ClinicalEntity" in url:
            raise requests.exceptions.ConnectionError("boom")
        return _resp(404)

    with patch("tooluniverse.orphanet_tool.requests.get", side_effect=fake_get):
        result = _tool().run({"operation": "get_phenotypes", "orpha_code": "1247"})

    assert result["status"] == "error"
    assert "not found" not in result["error"].lower()
    assert "phenotype annotations" in result["error"].lower()


# --- unrelated behavior preserved ------------------------------------------


def test_successful_phenotype_lookup_unaffected():
    payload = {
        "data": {
            "results": {
                "Preferred term": "Marfan syndrome",
                "HPODisorderAssociation": [
                    {
                        "HPO": {"HPOId": "HP:0001166", "HPOTerm": "Arachnodactyly"},
                        "HPOFrequency": {"name": "Very frequent (99-80%)"},
                        "DiagnosticCriteria": None,
                    }
                ],
            }
        }
    }

    with patch(
        "tooluniverse.orphanet_tool.requests.get", return_value=_resp(200, payload)
    ):
        result = _tool().run({"operation": "get_phenotypes", "orpha_code": "558"})

    assert result["status"] == "success"
    assert result["data"]["phenotype_count"] == 1
    assert result["data"]["phenotypes"][0]["hpo_id"] == "HP:0001166"


def test_non_404_http_error_still_surfaced_as_http_error():
    with patch("tooluniverse.orphanet_tool.requests.get", return_value=_resp(503)):
        result = _tool().run({"operation": "get_phenotypes", "orpha_code": "558"})

    assert result["status"] == "error"
    assert "HTTP error: 503" in result["error"]


# --- the refactored helper keeps its documented contract -------------------


def test_lookup_orpha_name_returns_term_for_live_code():
    with patch(
        "tooluniverse.orphanet_tool.requests.get",
        return_value=_resp(200, {"Preferred term": "Schistosomiasis"}),
    ):
        assert _tool()._lookup_orpha_name("1247") == (True, "Schistosomiasis")


def test_lookup_orpha_name_reports_unknown_code():
    with patch("tooluniverse.orphanet_tool.requests.get", return_value=_resp(404)):
        assert _tool()._lookup_orpha_name("99999999") == (False, None)


def test_orpha_code_exists_helper_still_lenient_on_network_error():
    """_orpha_code_exists now delegates to _lookup_orpha_name; its existing
    contract (used by five sibling operations) must be unchanged."""
    import requests

    with patch(
        "tooluniverse.orphanet_tool.requests.get",
        side_effect=requests.exceptions.ConnectionError("boom"),
    ):
        assert _tool()._orpha_code_exists("558") is True
