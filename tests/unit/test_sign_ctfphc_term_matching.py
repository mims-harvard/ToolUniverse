"""SIGN and CTFPHC searches match query terms, not the whole query as one substring.

Both filter a fixed index page client-side, and kept a row only if the entire
query was a substring of its title, so "asthma management in children" or
"screening for breast cancer in women" matched nothing. SIGN_list_guidelines
also answered [] to a topic SIGN does not use ("ophthalmology"; SIGN says
"Eye") instead of saying which topics exist.
"""

from unittest.mock import patch

import pytest

from tooluniverse import unified_guideline_tools as U

pytestmark = pytest.mark.unit

SIGN_ROWS = [
    {
        "number": 158,
        "title": "British guideline on the management of asthma",
        "topic": "Respiratory",
        "published": "2019",
        "url": "u1",
    },
    {
        "number": 154,
        "title": "Pharmacological management of glycaemic control in people with type 2 diabetes",
        "topic": "Endocrine Nutritional and Metabolic",
        "published": "2017",
        "url": "u2",
    },
    {
        "number": 116,
        "title": "Optimising glycaemic control in people with type 1 diabetes",
        "topic": "Endocrine Nutritional and Metabolic",
        "published": "2010",
        "url": "u3",
    },
    {
        "number": 144,
        "title": "Glaucoma referral and safe discharge",
        "topic": "Eye",
        "published": "2015",
        "url": "u4",
    },
]


def _sign(tool_cls, arguments):
    tool = tool_cls({"name": "t"})
    with patch.object(U, "_fetch_sign_table", return_value=SIGN_ROWS):
        return tool.run(arguments)


def test_multi_word_query_finds_the_guideline():
    rows = _sign(U.SIGNSearchGuidelinesTool, {"query": "asthma management in children"})
    assert [r["number"] for r in rows] == [158]


def test_rows_matching_more_query_words_come_first():
    rows = _sign(U.SIGNSearchGuidelinesTool, {"query": "type 2 diabetes management"})
    assert [r["number"] for r in rows][:2] == [154, 116]


def test_no_term_matches_is_an_empty_list():
    assert _sign(U.SIGNSearchGuidelinesTool, {"query": "orchialgia"}) == []


def test_unknown_topic_lists_signs_topics():
    result = _sign(U.SIGNListGuidelinesTool, {"topic": "ophthalmology"})
    assert result["status"] == "error" and "Eye" in result["error"]
    assert result["available_topics"] == [
        "Endocrine Nutritional and Metabolic",
        "Eye",
        "Respiratory",
    ]


def test_known_topic_still_filters_case_insensitively():
    rows = _sign(U.SIGNListGuidelinesTool, {"topic": "eye"})
    assert [r["number"] for r in rows] == [144]


def test_ctfphc_search_matches_terms():
    guidelines = [
        {
            "title": "Breast Cancer (Update) – Draft Recommendations (2024)",
            "url": "b",
            "year": "2024",
        },
        {"title": "Colorectal Cancer (2016)", "url": "c", "year": "2016"},
        {"title": "Depression in Adults (2013)", "url": "d", "year": "2013"},
    ]
    tool = U.CTFPHCSearchGuidelinesTool({"name": "t"})
    with patch.object(U, "_fetch_ctfphc_links", return_value=guidelines):
        rows = tool.run({"query": "screening for breast cancer in women"})
    assert [r["url"] for r in rows] == ["b", "c"]


def test_rank_by_terms_keeps_catalogue_order_on_ties():
    rows = [{"title": "Cancer A"}, {"title": "Cancer B"}]
    assert U._rank_by_terms(rows, "cancer", ("title",)) == rows
