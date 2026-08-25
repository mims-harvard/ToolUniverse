"""Regression guard for Fix-R25: PubMed_search_articles returned
doi=None/doi_url=None for essentially every article published before ~2008.

The DOI was parsed *only* out of the esummary ``elocationid`` display string,
which NCBI leaves empty for older records -- even though the very same
response carries the DOI in the structured ``articleids`` list, two keys away
(confirmed live for PMIDs 15720521, 17354009, 15500562, 14765742, 14627096).
``articleids`` is now the primary source, with the ``elocationid`` parse kept
as a fallback. The same defect existed on the efetch XML path, where older
records carry no <ELocationID> but do list the DOI in <ArticleIdList>.

All assertions below run against synthetic payloads -- no network.
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import tooluniverse
from tooluniverse.pubmed_tool import PubMedRESTTool

pytestmark = pytest.mark.unit

DATA_DIR = Path(tooluniverse.__file__).parent / "data"


def _tool():
    return PubMedRESTTool(
        {
            "name": "PubMed_search_articles",
            "type": "PubMedRESTTool",
            "fields": {
                "db": "pubmed",
                "retmode": "json",
                "endpoint": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
            },
            "parameter": {"type": "object", "properties": {}, "required": []},
        }
    )


def _summarize(record, pmid="15720521"):
    """Run one synthetic esummary record through _fetch_summaries."""
    tool = _tool()
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"result": {"uids": [pmid], pmid: record}}

    with (
        patch.object(tool, "_enforce_rate_limit"),
        patch("tooluniverse.pubmed_tool.request_with_retry", return_value=resp),
    ):
        result = tool._fetch_summaries([pmid])

    assert result["status"] == "success"
    return result["data"][0]


def _record(**overrides):
    base = {
        "uid": "15720521",
        "pubdate": "2005 Feb",
        "title": "Development of a PCR-based diagnostic test",
        "authors": [{"name": "Geyer J"}],
        "fulljournalname": "J Vet Pharmacol Ther",
        "pubtype": ["Journal Article"],
        "elocationid": "",
        "articleids": [],
    }
    base.update(overrides)
    return base


def test_old_record_doi_comes_from_articleids():
    """Empty elocationid + articleids doi entry -> DOI is populated."""
    article = _summarize(
        _record(
            elocationid="",
            articleids=[
                {"idtype": "pubmed", "value": "15720521"},
                {"idtype": "doi", "value": "10.1111/j.1365-2885.2004.00625.x"},
                {"idtype": "pii", "value": "JVP625"},
            ],
        )
    )

    assert article["doi"] == "10.1111/j.1365-2885.2004.00625.x"
    assert article["doi_url"] == "https://doi.org/10.1111/j.1365-2885.2004.00625.x"


def test_articleids_doi_is_not_double_prefixed():
    """The fallback must not leave/insert a 'doi:' prefix in the value."""
    article = _summarize(
        _record(articleids=[{"idtype": "doi", "value": "10.2460/javma.2003.223.1453"}])
    )

    assert article["doi"] == "10.2460/javma.2003.223.1453"
    assert not article["doi"].lower().startswith("doi:")
    assert article["doi_url"].count("https://doi.org/") == 1


def test_modern_record_with_populated_elocationid_is_unchanged():
    """A record where both sources agree still yields the clean DOI."""
    article = _summarize(
        _record(
            elocationid="doi: 10.1002/jat.70166",
            articleids=[
                {"idtype": "pubmed", "value": "41837342"},
                {"idtype": "pmc", "value": "PMC13136416"},
                {"idtype": "doi", "value": "10.1002/jat.70166"},
            ],
        )
    )

    assert article["doi"] == "10.1002/jat.70166"
    assert article["doi_url"] == "https://doi.org/10.1002/jat.70166"


def test_elocationid_still_used_when_articleids_lacks_doi():
    """Pre-existing behaviour: parse elocationid when there is no doi id."""
    article = _summarize(
        _record(
            elocationid="pii: 2026.02.14.705936. doi: 10.64898/2026.02.14.705936",
            articleids=[{"idtype": "pmc", "value": "PMC13136416"}],
        )
    )

    assert article["doi"] == "10.64898/2026.02.14.705936"
    assert "pii" not in article["doi"]
    assert article["doi_url"] == "https://doi.org/10.64898/2026.02.14.705936"


def test_record_with_no_doi_anywhere_returns_none():
    """A genuinely DOI-less record (e.g. PMID 13678080) stays None, not ''."""
    article = _summarize(
        _record(elocationid="", articleids=[{"idtype": "pubmed", "value": "13678080"}])
    )

    assert article["doi"] is None
    assert article["doi_url"] is None


def test_malformed_articleids_do_not_crash():
    """Blank/missing doi values fall through safely instead of yielding ''."""
    article = _summarize(
        _record(
            elocationid="",
            articleids=[
                {"idtype": "doi"},
                {"idtype": "doi", "value": ""},
                {"idtype": "doi", "value": None},
            ],
        )
    )

    assert article["doi"] is None
    assert article["doi_url"] is None


def test_efetch_xml_doi_falls_back_to_articleidlist():
    """Older efetch XML has no <ELocationID> but does list a doi ArticleId."""
    xml = """<?xml version="1.0"?>
<PubmedArticleSet><PubmedArticle>
  <MedlineCitation>
    <PMID>15720521</PMID>
    <Article>
      <Journal><Title>J Vet Pharmacol Ther</Title></Journal>
      <ArticleTitle>PCR-based diagnostic test</ArticleTitle>
    </Article>
  </MedlineCitation>
  <PubmedData><ArticleIdList>
    <ArticleId IdType="pubmed">15720521</ArticleId>
    <ArticleId IdType="doi">10.1111/j.1365-2885.2004.00625.x</ArticleId>
  </ArticleIdList></PubmedData>
</PubmedArticle></PubmedArticleSet>"""

    resp = MagicMock()
    resp.text = xml
    resp.url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    parsed = _tool()._parse_efetch_xml(resp)

    assert parsed["status"] == "success"
    assert parsed["data"]["doi"] == "10.1111/j.1365-2885.2004.00625.x"
    assert (
        parsed["data"]["doi_url"] == "https://doi.org/10.1111/j.1365-2885.2004.00625.x"
    )


def test_efetch_xml_elocationid_still_wins_and_no_doi_stays_none():
    """ELocationID remains primary; a record with neither source stays None."""
    with_eloc = """<?xml version="1.0"?>
<PubmedArticleSet><PubmedArticle>
  <MedlineCitation><PMID>41837342</PMID><Article>
    <Journal><Title>J Appl Toxicol</Title></Journal>
    <ArticleTitle>Modern article</ArticleTitle>
    <ELocationID EIdType="doi">10.1002/jat.70166</ELocationID>
  </Article></MedlineCitation>
</PubmedArticle></PubmedArticleSet>"""

    resp = MagicMock()
    resp.text = with_eloc
    resp.url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    assert _tool()._parse_efetch_xml(resp)["data"]["doi"] == "10.1002/jat.70166"

    without_any = """<?xml version="1.0"?>
<PubmedArticleSet><PubmedArticle>
  <MedlineCitation><PMID>13678080</PMID><Article>
    <Journal><Title>Old Journal</Title></Journal>
    <ArticleTitle>No DOI anywhere</ArticleTitle>
  </Article></MedlineCitation>
  <PubmedData><ArticleIdList>
    <ArticleId IdType="pubmed">13678080</ArticleId>
  </ArticleIdList></PubmedData>
</PubmedArticle></PubmedArticleSet>"""

    resp2 = MagicMock()
    resp2.text = without_any
    resp2.url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    data = _tool()._parse_efetch_xml(resp2)["data"]
    assert data["doi"] is None
    assert data["doi_url"] is None


def test_search_tool_config_still_declares_doi_fields():
    """The tool contract advertising doi/doi_url is resolved via the package
    directory, not a cwd-relative path."""
    config_path = DATA_DIR / "pubmed_tools.json"
    assert config_path.is_file(), f"missing {config_path}"

    configs = json.loads(config_path.read_text())
    search = next(c for c in configs if c["name"] == "PubMed_search_articles")
    assert search["type"] == "PubMedRESTTool"
