"""An over-specified query_term returns zero studies, and must say why.

Filed as #870. ClinicalTrials.gov combines the words of `query.term` with AND
against the indexed record text, so a descriptive query -- the normal thing an
agent writes, an acronym plus the drug, the indication and the line of therapy
-- comes back as zero studies with status success. That is indistinguishable
from "no such trial exists", and the metadata made it worse by declaring
`total_results_is_exact` on the zero.

Measured 2026-11-13:

    query_term="KEYNOTE-045"                                   -> 1 study,
                                                                  NCT02256436
    query_term="KEYNOTE-045 pembrolizumab urothelial carcinoma
                second-line platinum"                          -> 0 studies

Every word of the second is true of that trial. 51,291 studies match at least
one of those words.

The answer follows the one already in this module for rewritten queries:
disclose, never substitute. The caller asked for all of those words and still
gets exactly what they matched; what changes is that the zero now carries the
count for the OR'd wording beside it.

The diagnostic has to be able to come back negative, or it is decoration: a
query of nonsense words must say the AND was NOT the cause.
"""

import pytest

from tooluniverse.ctg_tool import _ESSIE_OPERATOR_RE, _term_match_check


def _never_called(_probe):
    raise AssertionError("no probe should be issued for this input")


def _counting(total):
    def fetch(probe):
        fetch.seen = probe
        return total

    fetch.seen = None
    return fetch


def test_a_many_worded_query_is_diagnosed():
    fetch = _counting(51291)
    check = _term_match_check(
        {"query.term": "KEYNOTE-045 pembrolizumab urothelial carcinoma platinum"}, fetch
    )
    assert check["terms_are_combined_with"] == "AND"
    assert check["studies_matching_any_term"] == 51291
    assert " OR " in check["relaxed_query"]
    assert "too specific" in check["note"]


def test_the_probe_is_count_only_and_keeps_every_other_filter():
    fetch = _counting(7)
    _term_match_check(
        {
            "query.term": "one two three",
            "filter.overallStatus": "RECRUITING",
            "pageToken": "abc",
        },
        fetch,
    )
    probe = fetch.seen
    assert probe["pageSize"] == 1
    assert probe["fields"] == "NCTId"
    assert probe["countTotal"] == "true"
    assert probe["filter.overallStatus"] == "RECRUITING", (
        "the two counts are only comparable if every other filter is inherited"
    )
    assert "pageToken" not in probe


def test_nonsense_words_are_told_apart_from_an_over_specified_query():
    check = _term_match_check({"query.term": "zzqq wwxx yyvv"}, _counting(0))
    assert check["studies_matching_any_term"] == 0
    assert "not an artefact" in check["note"], (
        "a check that says the same thing whatever the counts carries no information"
    )
    assert "too specific" not in check["note"]


@pytest.mark.parametrize(
    "term",
    ["KEYNOTE-045", "two words", "", None, 42],
)
def test_nothing_is_probed_when_there_is_nothing_to_diagnose(term):
    assert _term_match_check({"query.term": term}, _never_called) is None


@pytest.mark.parametrize(
    "term",
    [
        "cancer AND lung AND phase",
        "AREA[LastUpdatePostDate]RANGE[2023-01-15,MAX] one two",
        '"exact phrase here"',
        "(a b c)",
    ],
)
def test_a_caller_driving_essie_syntax_is_left_alone(term):
    assert _ESSIE_OPERATOR_RE.search(term)
    assert _term_match_check({"query.term": term}, _never_called) is None


def test_a_failed_probe_says_so_rather_than_claiming_a_count():
    def exploding(_probe):
        raise TimeoutError("upstream took too long")

    check = _term_match_check({"query.term": "one two three"}, exploding)
    assert "studies_matching_any_term" not in check
    assert "TimeoutError" in check["note"]
