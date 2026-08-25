"""Unit tests for the FDA Orange Book drug search. Network mocked.

Covers two fixes:

* openFDA answers a well-formed query that matches nothing with HTTP 404 plus a
  ``{"error": {"code": "NOT_FOUND"}}`` body. That has to read as an empty result,
  not as a dead endpoint, so a caller can tell "no such product" from "the API is
  down". A 404 without that body is still a real failure.
* ``drug_name`` used to be a plain alias for ``generic_name``, so it searched only
  the active-ingredient field and a brand name passed to it could never match. It
  now matches the brand name OR the active-ingredient name.
"""

import json
from importlib.resources import files
from unittest.mock import MagicMock, patch

from tooluniverse.fda_orange_book_tool import FDAOrangeBookTool


def _tool_configs():
    return json.loads(
        (files("tooluniverse.data") / "fda_orange_book_tools.json").read_text()
    )


def _config(name="FDA_OrangeBook_search_drug"):
    return next(t for t in _tool_configs() if t["name"] == name)

_ONE_HIT = {
    "meta": {"results": {"total": 1}},
    "results": [
        {
            "application_number": "NDA214985",
            "sponsor_name": "IDORSIA",
            "products": [
                {
                    "brand_name": "QUVIVIQ",
                    "active_ingredients": [{"name": "DARIDOREXANT HYDROCHLORIDE"}],
                    "dosage_form": "TABLET",
                    "route": "ORAL",
                    "marketing_status": "Prescription",
                    "reference_drug": "Yes",
                    "te_code": None,
                }
            ],
        }
    ],
}


def _tool():
    return FDAOrangeBookTool(_config())


def _resp(status=200, json_body=None, raise_exc=None):
    r = MagicMock()
    r.status_code = status
    if json_body is None and status == 404:
        r.json.side_effect = ValueError("no json")
    else:
        r.json.return_value = json_body
    if raise_exc is not None:
        r.raise_for_status.side_effect = raise_exc
    else:
        r.raise_for_status.return_value = None
    return r


def _search_param(mock_get):
    """Return the openFDA 'search' expression the tool actually sent."""
    return mock_get.call_args.kwargs["params"]["search"]


# ---------------- 404 means "zero matches", not "endpoint missing" ------------
def test_openfda_404_not_found_is_an_empty_success():
    body = {"error": {"code": "NOT_FOUND", "message": "No matches found!"}}
    with patch(
        "tooluniverse.fda_orange_book_tool.requests.get",
        return_value=_resp(404, body),
    ):
        out = _tool().run({"drug_name": "zzzznotadrugzzzz"})

    assert out["status"] == "success"
    assert out["data"]["drugs"] == []
    assert out["data"]["count"] == 0
    assert out["data"]["total"] == 0
    # The caller must be told this is an empty result rather than a failure.
    assert "note" in out["data"]
    assert "not an API failure" in out["data"]["note"]


def test_openfda_404_without_not_found_body_stays_an_error():
    """A genuinely missing endpoint must not be swallowed as 'no results'."""
    import requests

    err = requests.exceptions.HTTPError("404 Client Error: Not Found for url: ...")
    err.response = MagicMock(status_code=404)
    with patch(
        "tooluniverse.fda_orange_book_tool.requests.get",
        return_value=_resp(404, None, raise_exc=err),
    ):
        out = _tool().run({"drug_name": "anything"})

    assert out["status"] == "error"
    assert "404" in out["error"]


def test_successful_search_has_no_empty_result_note():
    with patch(
        "tooluniverse.fda_orange_book_tool.requests.get",
        return_value=_resp(200, _ONE_HIT),
    ):
        out = _tool().run({"drug_name": "Quviviq"})

    assert out["status"] == "success"
    assert out["data"]["count"] == 1
    assert out["data"]["drugs"][0]["application_number"] == "NDA214985"
    assert "note" not in out["data"]


# ---------------- drug_name matches brand names too --------------------------
def test_drug_name_searches_brand_and_ingredient_fields():
    with patch(
        "tooluniverse.fda_orange_book_tool.requests.get",
        return_value=_resp(200, _ONE_HIT),
    ) as get:
        _tool().run({"drug_name": "Quviviq"})

    search = _search_param(get)
    assert 'products.brand_name:"Quviviq"' in search
    assert 'products.active_ingredients.name:"Quviviq"' in search
    # openFDA needs a space-delimited operator; "+OR+" URL-encodes to %2BOR%2B,
    # which openFDA cannot parse and answers with a 404.
    assert " OR " in search
    assert "+OR+" not in search


def test_generic_name_still_searches_only_the_ingredient_field():
    with patch(
        "tooluniverse.fda_orange_book_tool.requests.get",
        return_value=_resp(200, _ONE_HIT),
    ) as get:
        _tool().run({"generic_name": "DARIDOREXANT"})

    search = _search_param(get)
    assert search == 'products.active_ingredients.name:"DARIDOREXANT"'


def test_multiple_terms_join_with_a_parsable_and_operator():
    with patch(
        "tooluniverse.fda_orange_book_tool.requests.get",
        return_value=_resp(200, _ONE_HIT),
    ) as get:
        _tool().run({"brand_name": "QUVIVIQ", "application_number": "NDA214985"})

    search = _search_param(get)
    assert " AND " in search
    assert "+AND+" not in search


def test_no_search_terms_is_an_input_error():
    out = _tool().run({})
    assert out["status"] == "error"
    assert "brand_name" in out["error"]
    assert "drug_name" in out["error"]


def test_drug_name_is_declared_in_the_tool_schema():
    """The behaviour and the published schema must agree."""
    assert "drug_name" in _config()["parameter"]["properties"]
