"""Round 037: FDALabelTool must never answer a drug-name lookup with another drug.

Regression for Fix-037. `_query_drug_fields` used to fall back to an *unquoted*
query, `openfda.generic_name:yellow fever vaccine`, which bound the field to its
first token only and let the rest match free text anywhere in the label -- so
FDA_get_drug_label answered "yellow fever vaccine" with naproxen, as a success.
See `_name_queries` in fda_label_tool.py for the measured detail.

Every query the tool issues must now keep all of its terms bound to the name
field; `_run` below asserts that invariant on every request of every test.

All tests here mock the HTTP layer -- no network.
"""

import re
from unittest.mock import patch

import pytest

from tooluniverse.fda_label_tool import FDALabelTool

# A query is safe only if every term sits inside quotes behind the field prefix:
# either one quoted phrase, or a parenthesised AND of quoted terms. A phrase may
# contain a backslash-escaped quote, which still does not end it.
_PHRASE = r'"(?:[^"\\]|\\.)*"'
_BOUND_QUERY = re.compile(rf"[\w.]+:(?:{_PHRASE}|\({_PHRASE}(?: AND {_PHRASE})*\))\Z")


def _cfg(query_type):
    return {
        "name": f"FDA_{query_type}",
        "type": "FDALabelTool",
        "fields": {
            "endpoint": "https://api.fda.gov/drug/label.json",
            "query_type": query_type,
        },
        "parameter": {"type": "object", "properties": {}},
    }


class _Resp:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def _label(generic):
    return {"openfda": {"generic_name": [generic]}, "id": f"spl-{generic}"}


def _run(query_type, arguments, corpus):
    """Run the tool against a fake openFDA that only answers `corpus` queries.

    `corpus` maps an exact search expression to the records it returns; every
    other expression 404s, exactly as openFDA does for a no-hit search. The
    queries actually issued are captured and returned for per-test assertions.

    Every issued query is checked against `_BOUND_QUERY` here rather than in the
    individual tests, so a test added later cannot silently opt out of the
    invariant this module exists to protect. The check runs after `run()`
    returns, not inside `fake_get`: the tool wraps `run()` in a catch-all
    `except Exception`, which would swallow an AssertionError into an ordinary
    error envelope and let the failure pass unnoticed.
    """
    issued = []

    def fake_get(url, params=None, timeout=None):
        q = params["search"]
        issued.append(q)
        if q in corpus:
            return _Resp({"results": corpus[q]})
        return _Resp({"error": {"code": "NOT_FOUND"}}, status_code=404)

    tool = FDALabelTool(_cfg(query_type))
    with patch("tooluniverse.fda_label_tool.requests.get", side_effect=fake_get):
        out = tool.run(arguments)

    for q in issued:
        assert _BOUND_QUERY.fullmatch(q), f"unbound query issued: {q}"
    return out, issued


# --------------------------------------------------------------------------
# The defect: a multi-word name with no exact match must not return a drug.
# --------------------------------------------------------------------------


@pytest.mark.parametrize("name", ["yellow fever vaccine", "typhoid vaccine"])
def test_get_label_multi_word_no_match_is_an_honest_miss(name):
    out, issued = _run("get", {"drug_name": name}, corpus={})

    assert out["status"] == "error"
    assert name in out["error"]
    # A miss has to tell the caller what to do next, like the sibling section
    # tools do, rather than just failing.
    assert out["suggestion"]
    assert "data" not in out

    # The specific query that caused the defect must never be issued again.
    assert f"openfda.generic_name:{name}" not in issued


@pytest.mark.parametrize("name", ["yellow fever vaccine", "typhoid vaccine"])
def test_search_multi_word_no_match_returns_no_records(name):
    out, issued = _run("search", {"drug_name": name, "limit": 5}, corpus={})

    assert out["status"] == "success"
    assert out["data"] == []
    assert out["metadata"]["count"] == 0
    assert out["suggestion"]

    assert f"openfda.generic_name:{name}" not in issued


def test_unrelated_label_is_unreachable_even_when_the_api_would_serve_it():
    """The corpus below answers ONLY the old unbound query, with naproxen.

    This reproduces the live failure directly: if the tool still emitted
    `openfda.generic_name:yellow fever vaccine` it would return NAPROXEN as a
    success. It must miss instead.
    """
    corpus = {"openfda.generic_name:yellow fever vaccine": [_label("NAPROXEN")]}
    out, _ = _run("get", {"drug_name": "yellow fever vaccine"}, corpus)

    assert out["status"] == "error"


# --------------------------------------------------------------------------
# The behaviour that has to survive: single-token salt-form matching.
# --------------------------------------------------------------------------


def test_single_token_still_matches_salt_forms():
    corpus = {
        'openfda.generic_name:"tofacitinib"': [
            _label("TOFACITINIB CITRATE"),
            _label("TOFACITINIB"),
        ]
    }
    out, issued = _run("search", {"drug_name": "tofacitinib"}, corpus)

    assert out["status"] == "success"
    assert [r["generic_name"] for r in out["data"]] == [
        "TOFACITINIB CITRATE",
        "TOFACITINIB",
    ]
    # One token means the AND form is identical to the phrase form, so it must
    # not cost a second request.
    assert issued == ['openfda.generic_name:"tofacitinib"']


def test_single_token_get_label_returns_the_salt_form_record():
    corpus = {'openfda.generic_name:"mefloquine"': [_label("MEFLOQUINE HYDROCHLORIDE")]}
    out, _ = _run("get", {"drug_name": "mefloquine"}, corpus)

    assert out["status"] == "success"
    assert out["data"]["generic_name"] == "MEFLOQUINE HYDROCHLORIDE"


def test_exact_multi_word_name_matches_on_the_phrase_query():
    name = "amoxicillin and clavulanate potassium"
    corpus = {f'openfda.generic_name:"{name}"': [_label(name.upper())]}
    out, issued = _run("get", {"drug_name": name}, corpus)

    assert out["status"] == "success"
    assert out["data"]["generic_name"] == name.upper()
    # The phrase hit first, so the AND fallback was never needed.
    assert issued == [f'openfda.generic_name:"{name}"']


# --------------------------------------------------------------------------
# The all-tokens fallback: recall the old form was supposed to add, without
# ever leaving the name field.
# --------------------------------------------------------------------------


def test_all_tokens_fallback_recovers_a_reordered_name():
    """The name "trimethoprim and sulfamethoxazole" is labelled the other way round.

    The phrase query misses it; AND-ing both tokens inside generic_name finds
    the 86 "SULFAMETHOXAZOLE AND TRIMETHOPRIM" labels, and because both terms
    stay bound to the field the hit still genuinely contains the search terms.
    """
    corpus = {
        'openfda.generic_name:("trimethoprim" AND "and" AND "sulfamethoxazole")': [
            _label("SULFAMETHOXAZOLE AND TRIMETHOPRIM")
        ]
    }
    out, issued = _run(
        "get", {"drug_name": "trimethoprim and sulfamethoxazole"}, corpus
    )

    assert out["status"] == "success"
    assert out["data"]["generic_name"] == "SULFAMETHOXAZOLE AND TRIMETHOPRIM"
    assert len(issued) == 2


def test_hyphenated_single_word_name_is_tokenised_not_left_unquoted():
    """The name "co-trimoxazole" is one whitespace token but two Lucene terms.

    Gating the old unquoted fallback on `len(name.split()) == 1` would have
    kept the defect here: unquoted, the hyphen splits and "co" matched a
    sunscreen and two homeopathic remedies on the live API.
    """
    out, issued = _run("get", {"drug_name": "co-trimoxazole"}, corpus={})

    assert out["status"] == "error"
    assert "openfda.generic_name:co-trimoxazole" not in issued
    assert 'openfda.generic_name:("co" AND "trimoxazole")' in issued


def test_brand_name_is_tried_after_generic_name():
    corpus = {'openfda.brand_name:"Eliquis"': [_label("APIXABAN")]}
    out, issued = _run("get", {"drug_name": "Eliquis"}, corpus)

    assert out["status"] == "success"
    assert out["data"]["generic_name"] == "APIXABAN"
    assert issued == [
        'openfda.generic_name:"Eliquis"',
        'openfda.brand_name:"Eliquis"',
    ]


def test_embedded_quote_cannot_break_out_of_the_query():
    """A quote in the name must be escaped, not close the phrase early."""
    out, issued = _run("get", {"drug_name": 'ace" OR "x'}, corpus={})

    assert out["status"] == "error"
    assert issued[0] == 'openfda.generic_name:"ace\\" OR \\"x"'


def test_indication_search_is_escaped_too():
    """The indication path builds a query from caller text as well.

    Unescaped it had the same escape hatch as the name path: measured live,
    `indications_and_usage:"pain"` matches 24,135 labels but
    `indications_and_usage:"pain" OR "x"` matches 57,661, the extra ones having
    nothing to do with the indication asked for.
    """
    _, issued = _run("search", {"indication": 'pain" OR "x'}, corpus={})

    assert issued == ['indications_and_usage:"pain\\" OR \\"x"']


def test_indication_search_returns_matching_labels():
    corpus = {'indications_and_usage:"hypertension"': [_label("LISINOPRIL")]}
    out, issued = _run("search", {"indication": "hypertension"}, corpus)

    assert out["status"] == "success"
    assert [r["generic_name"] for r in out["data"]] == ["LISINOPRIL"]
    assert issued == ['indications_and_usage:"hypertension"']
