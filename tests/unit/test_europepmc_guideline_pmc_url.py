"""Europe PMC guideline results must link to the canonical PMC article route."""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.unified_guideline_tools import EuropePMCGuidelinesTool

pytestmark = pytest.mark.unit

ABSTRACT = "Clinical practice guideline abstract with enough text. " * 8


def _search_payload(**fields):
    result = {
        "title": "Clinical practice guideline for testing links",
        "pubType": "Guideline",
    }
    result.update(fields)
    search = MagicMock()
    search.raise_for_status.return_value = None
    search.json.return_value = {
        "hitCount": 1,
        "resultList": {"result": [result]},
    }
    return search


def test_pmc_only_result_uses_the_pmc_article_url_prefix():
    tool = EuropePMCGuidelinesTool({"name": "EuropePMC_Guidelines_Search"})
    search = _search_payload(pmcid="PMC3257300")

    with (
        patch.object(tool.session, "get", return_value=search),
        patch.object(tool, "_get_europepmc_abstract", return_value=ABSTRACT),
        patch.object(tool, "_get_europepmc_full_content", return_value=""),
    ):
        result = tool.run({"query": "testing", "limit": 1})

    assert result["data"][0]["url"] == "https://europepmc.org/article/PMC/PMC3257300"


def test_pmid_result_still_uses_the_med_article_route():
    tool = EuropePMCGuidelinesTool({"name": "EuropePMC_Guidelines_Search"})
    search = _search_payload(pmid="12345678", pmcid="PMC3257300")

    with (
        patch.object(tool.session, "get", return_value=search),
        patch.object(tool, "_get_europepmc_abstract", return_value=ABSTRACT),
        patch.object(tool, "_get_europepmc_full_content", return_value=""),
    ):
        result = tool.run({"query": "testing", "limit": 1})

    assert result["data"][0]["url"] == "https://europepmc.org/article/MED/12345678"
