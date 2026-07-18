"""Regression guard for Fix-R10E-3: NCBI Bookshelf-type records (e.g. WHO
monographs/guidelines, doctype="book") store their title under
`booktitle` instead of `title`, and have no individual `authors` list --
confirmed live via raw esummary for PMID 34787987 ("WHO guideline for
clinical management of exposure to lead"), whose `title`/`authors` were
both empty while `booktitle` and `publishername` had the real values.
PubMedGuidelinesTool now falls back to those fields instead of silently
returning blanks.
"""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.unified_guideline_tools import PubMedGuidelinesTool

pytestmark = pytest.mark.unit

_SEARCH_JSON = {"esearchresult": {"idlist": ["34787987"], "count": "1"}}
_SUMMARY_JSON = {
    "result": {
        "34787987": {
            "title": "",
            "authors": [],
            "booktitle": "WHO guideline for clinical management of exposure to lead",
            "publishername": "World Health Organization",
            "pubtype": ["Book"],
            "source": "",
            "pubdate": "2021",
            "elocationid": "",
        }
    }
}
_ABSTRACT_XML = (
    "<PubmedArticleSet><PubmedArticle><MedlineCitation><PMID>34787987</PMID>"
    "<Article><Abstract><AbstractText>Guidance on managing lead exposure."
    "</AbstractText></Article></MedlineCitation></PubmedArticle></PubmedArticleSet>"
)


def test_book_record_falls_back_to_booktitle_and_publishername():
    tool = PubMedGuidelinesTool({"name": "PubMed_Guidelines_Search"})

    search_resp = MagicMock()
    search_resp.json.return_value = _SEARCH_JSON
    summary_resp = MagicMock()
    summary_resp.json.return_value = _SUMMARY_JSON
    abstract_resp = MagicMock()
    abstract_resp.text = _ABSTRACT_XML

    with patch.object(
        tool.session, "get", side_effect=[search_resp, summary_resp, abstract_resp]
    ), patch("tooluniverse.unified_guideline_tools.time.sleep"):
        response = tool.run({"query": "lead exposure"})

    # Fix-R9E-1 wraps the bare-list success case in a
    # {"status": "success", "data": [...]} envelope.
    assert response["status"] == "success"
    result = response["data"]
    assert len(result) == 1
    record = result[0]
    assert record["title"] == "WHO guideline for clinical management of exposure to lead"
    assert record["authors"] == "World Health Organization"


def test_regular_article_authors_unaffected():
    tool = PubMedGuidelinesTool({"name": "PubMed_Guidelines_Search"})
    summary = {
        "result": {
            "123": {
                "title": "A normal article",
                "authors": [{"name": "Doe J"}, {"name": "Smith A"}],
                "pubtype": ["Journal Article"],
                "source": "J Med",
                "pubdate": "2024",
                "elocationid": "",
            }
        }
    }
    search_resp = MagicMock()
    search_resp.json.return_value = {"esearchresult": {"idlist": ["123"], "count": "1"}}
    summary_resp = MagicMock()
    summary_resp.json.return_value = summary
    abstract_resp = MagicMock()
    abstract_resp.text = ""

    with patch.object(
        tool.session, "get", side_effect=[search_resp, summary_resp, abstract_resp]
    ), patch("tooluniverse.unified_guideline_tools.time.sleep"):
        response = tool.run({"query": "normal article"})

    # Fix-R9E-1 wraps the bare-list success case in a
    # {"status": "success", "data": [...]} envelope.
    assert response["status"] == "success"
    record = response["data"][0]
    assert record["title"] == "A normal article"
    assert record["authors"] == "Doe J, Smith A"
