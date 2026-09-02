"""Regression guard for Fix-R9E-1: PubMedGuidelinesTool.run() returned
_search_pubmed_guidelines's bare list of results directly on success,
never wrapped in the standard {"status": "success", "data": [...]}
envelope every sibling tool (e.g. PubMed_search_articles) uses. This exact
inconsistency was independently reported by personas across 4 separate
rounds (R5D-2, R7B-1, R7D-2, R9E-1).

Fix-R57-4 gave the same envelope a `metadata` block and moved its assembly
into the helper, so these stub the HTTP session rather than the helper --
the guard is about what `run` hands a caller, not about a private signature.
"""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.unified_guideline_tools import PubMedGuidelinesTool

pytestmark = pytest.mark.unit


def _tool():
    return PubMedGuidelinesTool({"name": "PubMed_Guidelines_Search"})


def _search_returning(pmids, count):
    """Stub esearch/esummary/efetch for one guideline PMID list."""
    summaries = {
        "result": {
            "uids": pmids,
            **{p: {"title": "A guideline", "pubdate": "2026"} for p in pmids},
        }
    }
    abstracts = "".join(
        f"<PubmedArticle><PMID>{p}</PMID>"
        f"<AbstractText>A guideline abstract</AbstractText></PubmedArticle>"
        for p in pmids
    )

    def fake_get(url, **kwargs):
        r = MagicMock()
        r.status_code = 200
        r.raise_for_status.return_value = None
        if "esearch" in url:
            r.json.return_value = {
                "esearchresult": {"idlist": pmids, "count": str(count)}
            }
        elif "esummary" in url:
            r.json.return_value = summaries
        else:
            r.text = abstracts
        return r

    return fake_get


def test_success_result_is_wrapped_in_standard_envelope():
    tool = _tool()
    with patch.object(tool.session, "get", side_effect=_search_returning(["123"], 1)):
        result = tool.run({"query": "guideline"})

    assert result["status"] == "success"
    assert [row["pmid"] for row in result["data"]] == ["123"]


def test_empty_result_is_wrapped_too():
    tool = _tool()
    with patch.object(tool.session, "get", side_effect=_search_returning([], 0)):
        result = tool.run({"query": "an extremely obscure query"})

    assert result["status"] == "success"
    assert result["data"] == []


def test_error_dict_passes_through_unwrapped():
    tool = _tool()
    with patch.object(tool.session, "get", side_effect=OSError("boom")):
        result = tool.run({"query": "sepsis management"})

    assert result["status"] == "error"
    assert "data" not in result


def test_missing_query_still_errors_before_search():
    tool = _tool()
    result = tool.run({})

    assert result == {"status": "error", "error": "Query parameter is required"}
