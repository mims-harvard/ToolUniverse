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
_QUOTED_PHRASE_ZERO_HITS = {
    "count": "0",
    "errorlist": None,
    "warninglist": {
        "phrasesignored": [],
        "quotedphrasesnotfound": ['"a nonexistent quoted phrase xyzzy"'],
        "outputmessages": ["No items found."],
    },
}


def test_pubmed_routes_through_the_shared_formatter_and_names_itself():
    """PubMed's entry point must produce PubMed's label, not a generic one.

    Fix-54A-1 moved the formatting into
    `tooluniverse.ncbi_eutils_tool.esearch_query_disclosure`, shared with six
    other eutils modules, each passing its own database label. The formatter's
    own behaviour is covered once in
    `tests/unit/test_eutils_dropped_terms_disclosed.py`; what is PubMed-specific
    -- and what breaks if the entry point is rewired to the wrong label or
    bypassed -- is asserted here.
    """
    warning = _surface(_TERMS_DROPPED)["warning"]

    assert "PubMed" in warning
    assert "rs180056600" in warning
    assert "REMAINING terms" in warning
    assert "need not mention the dropped ones" in warning


def test_the_zero_hit_container_still_works():
    """The half that already worked must keep working -- this is the guard.

    `warninglist` handling was correct; the round-53 fix added a second
    container rather than replacing the first. This fixture is the only one in
    the suite exercising `quotedphrasesnotfound`, so it stays here.
    """
    metadata = _surface(_QUOTED_PHRASE_ZERO_HITS)

    assert metadata["quoted_phrases_not_found"] == [
        '"a nonexistent quoted phrase xyzzy"'
    ]
    assert metadata["ncbi_messages"] == ["No items found."]
    assert "BROADER query" in metadata["warning"]
