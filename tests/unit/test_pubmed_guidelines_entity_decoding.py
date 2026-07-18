"""Regression guard for Fix-R7B-2/R7E-1: PubMedGuidelinesTool extracted
abstracts via regex on raw, unparsed efetch XML text, so entity references
like "&#x2265;" (confirmed present verbatim in PubMed's real efetch XML,
e.g. "NEWS/NEWS2 &#x2265; 5") were never resolved -- unlike
PubMed_search_articles, which uses a real XML parser that decodes them
automatically. html.unescape() now runs after the tag-strip regex.
"""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.unified_guideline_tools import PubMedGuidelinesTool

pytestmark = pytest.mark.unit

_SEARCH_JSON = {"esearchresult": {"idlist": ["123"], "count": "1"}}
_SUMMARY_JSON = {
    "result": {
        "123": {
            "title": "Sepsis guideline",
            "authors": [{"name": "Doe J"}],
            "pubtype": ["Guideline"],
            "source": "Crit Care Med",
            "pubdate": "2026",
            "elocationid": "",
        }
    }
}
_ABSTRACT_XML = (
    "<PubmedArticleSet><PubmedArticle><MedlineCitation><PMID>123</PMID>"
    "<Article><Abstract><AbstractText>"
    "Criteria include NEWS/NEWS2 &#x2265; 5 and Shock Index &#x2265; 0.7."
    "</AbstractText></Article></MedlineCitation></PubmedArticle></PubmedArticleSet>"
)


def test_abstract_entities_are_decoded():
    tool = PubMedGuidelinesTool({"name": "PubMed_Guidelines_Search"})

    search_resp = MagicMock()
    search_resp.json.return_value = _SEARCH_JSON
    summary_resp = MagicMock()
    summary_resp.json.return_value = _SUMMARY_JSON
    abstract_resp = MagicMock()
    abstract_resp.text = _ABSTRACT_XML

    with patch.object(
        tool.session,
        "get",
        side_effect=[search_resp, summary_resp, abstract_resp],
    ), patch("tooluniverse.unified_guideline_tools.time.sleep"):
        response = tool.run({"query": "sepsis vasopressor"})

    # Fix-R9E-1 wraps the bare-list success case in a
    # {"status": "success", "data": [...]} envelope.
    assert response["status"] == "success"
    results = response["data"]
    assert len(results) == 1
    abstract = results[0]["abstract"]
    assert "≥" in abstract
    assert "&#x2265;" not in abstract
    assert "&amp;" not in abstract
