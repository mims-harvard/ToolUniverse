"""Fix-53B-1: PubMed read one of NCBI's two disclosure containers.

esearch drops terms it cannot match and answers a broader query. It reports
that in `warninglist` when the search ends with ZERO hits, and in `errorlist`
when terms were dropped but hits REMAIN. `_search_warning_metadata` read only
`warninglist`, so the disclosure fired exactly when the caller could not be
misled -- nothing came back -- and stayed silent exactly when they could.

Measured live against eutils esearch.fcgi on 2026-08-13:

    term  "benzene hematotoxicity NQO1 GSTT1 rs180056600"
      count 4
      errorlist   {"phrasesnotfound": ["rs180056600"], "fieldsnotfound": []}
      warninglist null

    term  "zzzqqqxyz toluene diisocyanate nonexistentterm12345"
      count 1477
      errorlist   {"phrasesnotfound": ["zzzqqqxyz", "nonexistentterm12345"]}
      warninglist null

    term  '"a nonexistent quoted phrase xyzzy"'
      count 0
      errorlist   null
      warninglist {"quotedphrasesnotfound": [...],
                   "outputmessages": ["No items found."]}

An industrial hygienist asking for a named susceptibility variant received
four papers that do not mention it, and a `metadata` block whose only keys were
count, total, query and source. The second query is worse: 1,477 hits for a
question two thirds of which was discarded.

These tests call the pure static formatter, so no request is made.
"""

import pytest

from tooluniverse.pubmed_tool import PubMedRESTTool

pytestmark = pytest.mark.unit

_surface = PubMedRESTTool._search_warning_metadata

# Verbatim esearchresult fragments from the live responses above.
_TERMS_DROPPED = {
    "count": "4",
    "errorlist": {"phrasesnotfound": ["rs180056600"], "fieldsnotfound": []},
    "warninglist": None,
    "querytranslation": '"benzene"[All Fields] AND "NQO1"[All Fields]',
}
_TWO_TERMS_DROPPED = {
    "count": "1477",
    "errorlist": {
        "phrasesnotfound": ["zzzqqqxyz", "nonexistentterm12345"],
        "fieldsnotfound": [],
    },
    "warninglist": None,
}
_QUOTED_PHRASE_ZERO_HITS = {
    "count": "0",
    "errorlist": None,
    "warninglist": {
        "phrasesignored": [],
        "quotedphrasesnotfound": ['"a nonexistent quoted phrase xyzzy"'],
        "outputmessages": ["No items found."],
    },
}
_FIELD_DROPPED = {
    "count": "812",
    "errorlist": {"phrasesnotfound": [], "fieldsnotfound": ["Notafield"]},
    "warninglist": None,
}
_CLEAN = {"count": "56", "errorlist": None, "warninglist": None}


def test_a_dropped_term_is_reported_when_results_still_come_back():
    """The silent case. Pre-fix this returned `{}` -- no disclosure at all."""
    metadata = _surface(_TERMS_DROPPED)

    assert metadata["terms_not_found"] == ["rs180056600"]
    assert metadata["query_not_executed_as_submitted"] is True


def test_the_warning_says_the_articles_need_not_mention_the_dropped_term():
    """A caller reading only `warning` must learn what they are looking at."""
    warning = _surface(_TERMS_DROPPED)["warning"]

    assert "rs180056600" in warning
    assert "REMAINING terms" in warning
    assert "need not mention the dropped ones" in warning


def test_every_dropped_term_is_listed_not_just_the_first():
    metadata = _surface(_TWO_TERMS_DROPPED)

    assert metadata["terms_not_found"] == ["zzzqqqxyz", "nonexistentterm12345"]


def test_an_unrecognised_search_field_is_reported_as_an_ignored_restriction():
    """A dropped `[field]` tag widens the search silently, like a dropped term."""
    metadata = _surface(_FIELD_DROPPED)

    assert metadata["search_fields_not_found"] == ["Notafield"]
    assert "NOT limited to that field" in metadata["warning"]


def test_the_zero_hit_container_still_works():
    """The half that already worked must keep working -- this is the guard.

    `warninglist` handling was correct; the fix adds a second container rather
    than replacing the first.
    """
    metadata = _surface(_QUOTED_PHRASE_ZERO_HITS)

    assert metadata["quoted_phrases_not_found"] == [
        '"a nonexistent quoted phrase xyzzy"'
    ]
    assert metadata["ncbi_messages"] == ["No items found."]
    assert "BROADER query" in metadata["warning"]


def test_the_executed_query_is_surfaced_for_the_errorlist_path_too():
    """Knowing a term was dropped is less use than seeing what ran instead."""
    assert _surface(_TERMS_DROPPED)["executed_query"].startswith('"benzene"')


def test_an_empty_errorlist_is_not_a_warning():
    """NCBI sends `fieldsnotfound: []` on healthy queries; it must stay quiet."""
    assert _surface({"count": "4", "errorlist": {"fieldsnotfound": []}}) == {}


def test_a_clean_query_keeps_its_existing_metadata_shape():
    assert _surface(_CLEAN) == {}
    assert _surface({}) == {}
    assert _surface(None) == {}
