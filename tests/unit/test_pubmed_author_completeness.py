"""Regressions for complete PubMed author lists."""

from unittest.mock import Mock

import pytest

from tooluniverse.pubmed_tool import PubMedRESTTool

pytestmark = pytest.mark.unit


def _tool():
    return PubMedRESTTool(
        {
            "name": "PubMed_get_article",
            "fields": {
                "endpoint": "https://example.test/efetch.fcgi",
                "db": "pubmed",
                "retmode": "xml",
            },
            "parameter": {"properties": {}},
        }
    )


def test_esummary_discloses_the_full_author_count(monkeypatch):
    authors = [{"name": f"Author {index}"} for index in range(12)]
    response = Mock(status_code=200)
    response.json.return_value = {
        "result": {"123": {"title": "Consortium study", "authors": authors}}
    }
    monkeypatch.setattr(
        "tooluniverse.pubmed_tool.request_with_retry",
        lambda *args, **kwargs: response,
    )
    tool = _tool()
    monkeypatch.setattr(tool, "_enforce_rate_limit", lambda *args: None)

    result = tool._fetch_summaries(["123"])

    # Search results echo the first 5 names to bound payload size; the full
    # count and the truncation flag make the cut visible.
    assert result["data"][0]["authors"] == [x["name"] for x in authors[:5]]
    assert result["data"][0]["author_count"] == 12
    assert result["data"][0]["authors_truncated"] is True


def test_efetch_keeps_all_authors_collective_names_and_affiliations():
    author_xml = "".join(
        f"""
        <Author>
          <LastName>Author{index}</LastName><ForeName>Person</ForeName>
          <AffiliationInfo><Affiliation>Institute {index}A</Affiliation></AffiliationInfo>
          <AffiliationInfo><Affiliation>Institute {index}B</Affiliation></AffiliationInfo>
        </Author>
        """
        for index in range(11)
    )
    xml = f"""
    <PubmedArticleSet><PubmedArticle><MedlineCitation>
      <PMID>123</PMID><Article><ArticleTitle>Large collaboration</ArticleTitle>
      <AuthorList>{author_xml}<Author><CollectiveName>Example Consortium</CollectiveName></Author></AuthorList>
      <Journal><Title>Example Journal</Title></Journal>
    </Article></MedlineCitation></PubmedArticle></PubmedArticleSet>
    """
    response = Mock(text=xml, url="https://example.test/efetch.fcgi?id=123")

    result = _tool()._parse_efetch_xml(response)

    assert result["data"]["author_count"] == 12
    assert result["data"]["authors"][10]["name"] == "Author10 Person"
    assert result["data"]["authors"][10]["affiliations"] == [
        "Institute 10A",
        "Institute 10B",
    ]
    assert result["data"]["authors"][-1]["name"] == "Example Consortium"
