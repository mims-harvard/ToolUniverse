"""Keep every section of structured abstracts used in guideline results."""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.unified_guideline_tools import (
    EuropePMCGuidelinesTool,
    PubMedGuidelinesTool,
)

pytestmark = pytest.mark.unit


_MULTI_SECTION_XML = (
    "<PubmedArticleSet><PubmedArticle><MedlineCitation><PMID>123</PMID>"
    "<Article><Abstract>"
    '<AbstractText Label="BACKGROUND">Background <i>evidence</i>.</AbstractText>'
    '<AbstractText Label="RESULTS">Results &amp; conclusions.</AbstractText>'
    "</Abstract></Article></MedlineCitation></PubmedArticle></PubmedArticleSet>"
)


def test_pubmed_guideline_result_keeps_all_abstract_sections():
    tool = PubMedGuidelinesTool({"name": "PubMed_Guidelines_Search"})
    search = MagicMock()
    search.json.return_value = {"esearchresult": {"idlist": ["123"], "count": "1"}}
    summary = MagicMock()
    summary.json.return_value = {
        "result": {
            "123": {
                "title": "Evidence guideline for testing",
                "authors": [],
                "pubtype": ["Guideline"],
                "source": "J Test",
                "pubdate": "2026",
                "elocationid": "",
            }
        }
    }
    abstract = MagicMock()
    abstract.text = _MULTI_SECTION_XML

    with (
        patch.object(tool.session, "get", side_effect=[search, summary, abstract]),
        patch("tooluniverse.unified_guideline_tools.time.sleep"),
    ):
        result = tool.run({"query": "evidence testing"})

    assert (
        result["data"][0]["abstract"] == "Background evidence. Results & conclusions."
    )


def test_europepmc_abstract_fetch_keeps_all_sections_and_inline_text():
    tool = EuropePMCGuidelinesTool({"name": "EuropePMC_Guidelines_Search"})
    response = MagicMock()
    response.content = _MULTI_SECTION_XML.encode()
    response.raise_for_status.return_value = None

    with patch.object(tool.session, "get", return_value=response):
        abstract = tool._get_europepmc_abstract("123")

    assert abstract == "Background evidence. Results & conclusions."


def test_pubmed_malformed_abstract_xml_returns_a_visible_error():
    tool = PubMedGuidelinesTool({"name": "PubMed_Guidelines_Search"})
    search = MagicMock()
    search.json.return_value = {"esearchresult": {"idlist": ["123"], "count": "1"}}
    summary = MagicMock()
    summary.json.return_value = {"result": {"123": {}}}
    abstract = MagicMock()
    abstract.text = "<PubmedArticle><AbstractText>unterminated"

    with (
        patch.object(tool.session, "get", side_effect=[search, summary, abstract]),
        patch("tooluniverse.unified_guideline_tools.time.sleep"),
    ):
        result = tool.run({"query": "evidence"})

    assert result["status"] == "error"
    assert "parse PubMed abstract XML" in result["error"]
