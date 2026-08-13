"""Fix-54A-1: NCBI's dropped-term disclosure was read for PubMed only.

Round 53 taught PubMed to read `errorlist` as well as `warninglist`. The
distinction is the whole point and it is the opposite way round from what a
reader expects:

  * `warninglist` is populated when the search ends with ZERO hits -- exactly
    when the caller cannot be misled, because nothing came back.
  * `errorlist.phrasesnotfound` is populated when terms were dropped but hits
    REMAIN -- exactly when the caller is misled.

Eleven other modules here parse esearch responses and read neither container.
The behaviour was measured live across fourteen eutils databases on
2026-08-13; that table lives with the code it justifies, in
`esearch_query_disclosure`'s docstring, and is not restated here. Its result:
every database reported both nonsense phrases in `errorlist.phrasesnotfound`
and returned a count IDENTICAL to the query with those phrases deleted -- i.e.
the dropped terms constrained nothing, and every one of those searches answered
a strictly broader question than the one submitted.

Three tools made this worse than silence by naming a field for the query that
ran and then putting the SUBMITTED query in it (CLI-verified before the fix):

    NCBI_search_nucleotide   data.search_term
      "BRCA1 zzzqqqxyz nonexistentterm12345"        count 66893
    NCBI_SRA_search_runs     data.search_term
      "(RNA-seq zzzqqqxyz nonexistentterm12345)"    count 7209038
    SRA_search_experiments   data.query_used
      "RNA-seq zzzqqqxyz nonexistentterm12345"      total 7209038

These tests call the pure formatter, so no request is made.
"""

import pytest

from tooluniverse.ncbi_eutils_tool import esearch_query_disclosure

pytestmark = pytest.mark.unit

# Verbatim esearchresult fragments from the live responses above.
_NUCCORE_TWO_DROPPED = {
    "count": "7359",
    "idlist": ["2194972897"],
    "querytranslation": "BRCA1[All Fields]",
    "errorlist": {
        "phrasesnotfound": ["zzzqqqxyz", "nonexistentterm12345"],
        "fieldsnotfound": [],
    },
    "warninglist": None,
}

_CLEAN = {
    "count": "7359",
    "idlist": ["2194972897"],
    "querytranslation": "BRCA1[All Fields]",
    "errorlist": None,
    "warninglist": None,
}

# taxonomy, the one probe that came back with zero hits, populated BOTH
# containers -- so the two must not be treated as mutually exclusive.
_ZERO_HIT_BOTH_CONTAINERS = {
    "count": "0",
    "idlist": [],
    "querytranslation": "(Homo sapiens zzzqqqxyz nonexistentterm12345[All Names])",
    "errorlist": {
        "phrasesnotfound": ["Homo", "sapiens", "zzzqqqxyz", "nonexistentterm12345"],
        "fieldsnotfound": [],
    },
    "warninglist": {
        "phrasesignored": [],
        "quotedphrasesnotfound": [],
        "outputmessages": ["No items found."],
    },
}


def test_terms_dropped_while_hits_remain_are_reported():
    """The errorlist case: 7,359 nuccore records for a query two thirds gone."""
    meta = esearch_query_disclosure(_NUCCORE_TWO_DROPPED, source="nuccore")
    assert meta["terms_not_found"] == ["zzzqqqxyz", "nonexistentterm12345"]
    assert meta["query_not_executed_as_submitted"] is True


def test_the_warning_names_every_dropped_term():
    """A warning that omits a dropped term leaves the caller guessing."""
    warning = esearch_query_disclosure(_NUCCORE_TWO_DROPPED, source="nuccore")[
        "warning"
    ]
    assert "zzzqqqxyz" in warning
    assert "nonexistentterm12345" in warning


def test_the_warning_says_the_records_need_not_mention_the_dropped_terms():
    """The actionable half: the hits need not relate to what was dropped."""
    warning = esearch_query_disclosure(_NUCCORE_TWO_DROPPED, source="nuccore")[
        "warning"
    ]
    assert "need not mention the dropped ones" in warning


def test_the_source_database_is_named_in_the_warning():
    """A caller chaining several eutils tools must know which one broadened."""
    assert (
        "nuccore"
        in esearch_query_disclosure(_NUCCORE_TWO_DROPPED, source="nuccore")["warning"]
    )
    assert (
        "MedGen"
        in esearch_query_disclosure(_NUCCORE_TWO_DROPPED, source="MedGen")["warning"]
    )


def test_the_query_actually_executed_is_surfaced():
    """`search_term`/`query_used` report what was SUBMITTED; this reports what ran."""
    meta = esearch_query_disclosure(_NUCCORE_TWO_DROPPED, source="nuccore")
    assert meta["executed_query"] == "BRCA1[All Fields]"


def test_a_query_run_as_submitted_stays_silent():
    """Unaffected responses must keep their existing shape -- no empty key."""
    assert esearch_query_disclosure(_CLEAN, source="nuccore") == {}


def test_both_containers_are_read_when_both_are_populated():
    """The zero-hit taxonomy probe filled errorlist AND warninglist at once."""
    meta = esearch_query_disclosure(_ZERO_HIT_BOTH_CONTAINERS, source="taxonomy")
    assert meta["terms_not_found"] == [
        "Homo",
        "sapiens",
        "zzzqqqxyz",
        "nonexistentterm12345",
    ]
    assert meta["ncbi_messages"] == ["No items found."]


def test_empty_error_containers_are_not_mistaken_for_a_report():
    """`fieldsnotfound: []` accompanies every response; it is not a disclosure."""
    only_empty_lists = dict(
        _CLEAN,
        errorlist={"phrasesnotfound": [], "fieldsnotfound": []},
        warninglist={"phrasesignored": [], "quotedphrasesnotfound": []},
    )
    assert esearch_query_disclosure(only_empty_lists, source="nuccore") == {}


def test_a_non_dict_esearch_result_does_not_raise():
    """esearch returns a bare string on some error paths; callers pass it through."""
    assert esearch_query_disclosure("<html>error</html>", source="nuccore") == {}
    assert esearch_query_disclosure(None, source="nuccore") == {}


def test_an_unrecognised_search_field_is_reported_as_not_applied():
    """A dropped `[field]` tag silently un-restricts the search."""
    meta = esearch_query_disclosure(
        dict(
            _CLEAN,
            errorlist={"phrasesnotfound": [], "fieldsnotfound": ["Notafield"]},
        ),
        source="nuccore",
    )
    assert meta["search_fields_not_found"] == ["Notafield"]
    assert "NOT limited to that field" in meta["warning"]
