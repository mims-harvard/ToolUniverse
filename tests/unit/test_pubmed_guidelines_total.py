"""Regression guard for Fix-R57-4: PubMed_Guidelines_Search fetched the number
of matching guidelines and threw it away with a dead expression.

``_search_pubmed_guidelines`` contained the bare statement

    search_data.get("esearchresult", {}).get("count", "0")

whose value was computed and discarded, so the envelope carried only the rows.
Confirmed live: ``{"query": "therapeutic plasma exchange", "limit": 3}``
returned 3 results while
``esearch.fcgi?db=pubmed&term=therapeutic+plasma+exchange+AND+(guideline...)``
reports ``count 94``. A caller sizing a literature corpus reads 3 as the total.

The sibling ``PubMed_search_articles`` already publishes this field, and this
tool already returns a dict envelope (``{"status", "data"}``, added in
Fix-R9E-1), so adding ``metadata`` is additive -- no list-to-dict change of the
kind that keeps the sibling guideline tools deferred.
"""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.unified_guideline_tools import PubMedGuidelinesTool

pytestmark = pytest.mark.unit


def _tool():
    return PubMedGuidelinesTool({"name": "PubMed_Guidelines_Search", "type": "x"})


def _json(payload):
    r = MagicMock()
    r.status_code = 200
    r.json.return_value = payload
    r.raise_for_status.return_value = None
    return r


def _xml(text):
    r = MagicMock()
    r.status_code = 200
    r.text = text
    r.raise_for_status.return_value = None
    return r


ABSTRACTS = "".join(
    f"<PubmedArticle><PMID>{pmid}</PMID>"
    f"<AbstractText>Abstract {pmid}</AbstractText></PubmedArticle>"
    for pmid in ("1", "2")
)


def _dispatch(count, idlist):
    summaries = {
        "result": {
            "uids": idlist,
            **{
                pmid: {"title": f"Guideline {pmid}", "pubdate": "2026"}
                for pmid in idlist
            },
        }
    }

    def fake_get(url, **kwargs):
        if "esearch" in url:
            return _json({"esearchresult": {"idlist": idlist, "count": count}})
        if "esummary" in url:
            return _json(summaries)
        return _xml(ABSTRACTS)

    return fake_get


class TestGuidelineTotal:
    def test_total_is_the_upstream_count_not_the_page_size(self):
        tool = _tool()
        with patch.object(tool.session, "get", side_effect=_dispatch("94", ["1", "2"])):
            result = tool.run({"query": "therapeutic plasma exchange", "limit": 2})

        assert result["status"] == "success"
        assert result["metadata"]["total"] == 94
        assert result["metadata"]["retrieved"] == 2
        assert result["metadata"]["returned"] == len(result["data"])
        assert result["metadata"]["truncated"] is True

    def test_an_unpaged_result_is_not_marked_truncated(self):
        tool = _tool()
        with patch.object(tool.session, "get", side_effect=_dispatch("2", ["1", "2"])):
            result = tool.run({"query": "guideline", "limit": 10})

        assert result["metadata"]["total"] == 2
        assert result["metadata"]["retrieved"] == 2
        assert result["metadata"]["truncated"] is False

    def test_client_side_filtering_is_distinguishable_from_upstream_paging(self):
        """`returned` < `retrieved` means this tool dropped rows itself; only
        `total` > `retrieved` is PubMed withholding more."""
        tool = _tool()
        with patch.object(tool.session, "get", side_effect=_dispatch("2", ["1", "2"])):
            result = tool.run({"query": "zzqqxxwubble", "limit": 10})

        metadata = result["metadata"]
        assert metadata["total"] == 2
        assert metadata["retrieved"] == 2
        assert metadata["returned"] == 0
        assert metadata["truncated"] is False

    def test_no_matches_still_reports_a_total_of_zero(self):
        tool = _tool()
        with patch.object(tool.session, "get", side_effect=_dispatch("0", [])):
            result = tool.run({"query": "zzqqxxwubble", "limit": 5})

        assert result["status"] == "success"
        assert result["data"] == []
        assert result["metadata"]["total"] == 0
        assert result["metadata"]["truncated"] is False

    def test_a_non_numeric_count_does_not_break_the_search(self):
        tool = _tool()
        with patch.object(tool.session, "get", side_effect=_dispatch(None, ["1"])):
            result = tool.run({"query": "anything", "limit": 5})

        assert result["status"] == "success"
        assert result["metadata"]["total"] == 0

    def test_an_upstream_failure_still_returns_the_error_envelope(self):
        """The helper now returns a tuple; the error path must survive it."""
        tool = _tool()
        with patch.object(tool.session, "get", side_effect=OSError("ncbi down")):
            result = tool.run({"query": "anything"})

        assert result["status"] == "error"
        assert "metadata" not in result
