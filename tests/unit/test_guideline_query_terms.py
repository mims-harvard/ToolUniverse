"""Keep biomedical query terms intact for guideline relevance filtering."""

import pytest

from tooluniverse.unified_guideline_tools import _extract_meaningful_terms

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("H1N1", ["h1n1"]),
        ("医疗", ["医疗"]),
        ("COVID-19", ["covid-19"]),
        ("HLA-B*57:01", ["hla-b*57:01"]),
        ("IL-6", ["il-6"]),
    ],
)
def test_meaningful_terms_support_alphanumeric_and_unicode_biomedical_queries(
    query, expected
):
    assert _extract_meaningful_terms(query) == expected


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("management of sepsis in adults", ["sepsis", "adults"]),
        ("diagnosis of anemia in pregnancy", ["diagnosis", "anemia", "pregnancy"]),
        ("use of statins", ["use", "statins"]),
    ],
)
def test_short_english_function_words_are_not_treated_as_search_terms(query, expected):
    """ "of"/"in" substring-match nearly every abstract, disabling the filter."""
    assert _extract_meaningful_terms(query) == expected


def test_short_nonlatin_and_alphanumeric_terms_survive_the_function_word_filter():
    """Dropping short words must not drop specific short terms."""
    assert _extract_meaningful_terms("医疗") == ["医疗"]
    assert _extract_meaningful_terms("T2 mapping") == ["t2", "mapping"]


def test_pubmed_guideline_filter_rejects_records_matching_only_function_words():
    from unittest.mock import MagicMock, patch

    from tooluniverse.unified_guideline_tools import PubMedGuidelinesTool

    tool = PubMedGuidelinesTool({"name": "PubMed_Guidelines_Search"})
    search = MagicMock()
    search.json.return_value = {"esearchresult": {"idlist": ["1", "2"], "count": "2"}}
    summary = MagicMock()
    summary.json.return_value = {
        "result": {
            "1": {
                "title": "Sepsis management in adults",
                "authors": [],
                "pubtype": ["Guideline"],
            },
            # Shares only "of"/"in" with the query.
            "2": {
                "title": "A profile of cartography in medieval Iceland",
                "authors": [],
                "pubtype": ["Guideline"],
            },
        }
    }
    abstract = MagicMock()
    abstract.text = ""

    with (
        patch.object(tool.session, "get", side_effect=[search, summary, abstract]),
        patch("tooluniverse.unified_guideline_tools.time.sleep"),
    ):
        result = tool.run({"query": "management of sepsis in adults"})

    assert [row["pmid"] for row in result["data"]] == ["1"]


def test_pubmed_guideline_filter_does_not_admit_numeric_suffix_matches():
    from unittest.mock import MagicMock, patch

    from tooluniverse.unified_guideline_tools import PubMedGuidelinesTool

    tool = PubMedGuidelinesTool({"name": "PubMed_Guidelines_Search"})
    search = MagicMock()
    search.json.return_value = {"esearchresult": {"idlist": ["1", "2"], "count": "2"}}
    summary = MagicMock()
    summary.json.return_value = {
        "result": {
            "1": {
                "title": "COVID-19 clinical guideline",
                "authors": [],
                "pubtype": ["Guideline"],
            },
            "2": {
                "title": "Health service report for 2019",
                "authors": [],
                "pubtype": ["Guideline"],
            },
        }
    }
    abstract = MagicMock()
    abstract.text = ""

    with (
        patch.object(tool.session, "get", side_effect=[search, summary, abstract]),
        patch("tooluniverse.unified_guideline_tools.time.sleep"),
    ):
        result = tool.run({"query": "COVID-19"})

    assert [row["pmid"] for row in result["data"]] == ["1"]
