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
