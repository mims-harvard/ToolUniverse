"""EuropePMC_Guidelines_Search: one request, guidelines by type or title.

Observed live before the change: "persistent idiopathic post-operative chronic
orchialgia" answered total 5, returned 0 -- the bare words `guideline OR
recommendation ...` matched conference proceedings anywhere in the full text,
and the client-side keyword filter then dropped all of them -- and "choroidal
osteomas treatment guidelines" took 110 s, because every row cost a PubMed
abstract request and often a full-text request, one after another.
"""

from unittest.mock import MagicMock, patch

import pytest
import requests

from tooluniverse.unified_guideline_tools import EuropePMCGuidelinesTool

pytestmark = pytest.mark.unit

RECORDS = [
    {
        "title": "Guideline No. 468: Clinical Management of Endometriosis.",
        "pmid": "39999999",
        "pubTypeList": {"pubType": ["Practice Guideline", "Journal Article"]},
        "abstractText": "<h4>Objective</h4><p>To provide <i>evidence-based</i> "
        "guidance.</p><h4>Recommendations</h4><p>Offer hormonal therapy.</p>",
        "journalInfo": {"journal": {"title": "J Obstet Gynaecol Can"}},
        "authorString": "Smith A, Jones B.",
        "firstPublicationDate": "2026-01-05",
    },
    {
        "title": "Consensus recommendations on deep endometriosis imaging",
        "pmcid": "PMC1234567",
        "pubTypeList": {"pubType": ["Journal Article"]},
    },
]


def _payload(records, hit_count=None):
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = {
        "hitCount": len(records) if hit_count is None else hit_count,
        "resultList": {"result": records},
    }
    return resp


def _run(records, hit_count=None, **arguments):
    tool = EuropePMCGuidelinesTool({"name": "EuropePMC_Guidelines_Search"})
    with patch.object(
        tool.session, "get", return_value=_payload(records, hit_count)
    ) as get:
        result = tool.run({"query": "endometriosis", **arguments})
    return result, get


def test_one_request_carries_the_guideline_filter_and_asks_for_abstracts():
    _, get = _run(RECORDS, limit=5)
    assert get.call_count == 1  # nothing fetched per record
    params = get.call_args.kwargs["params"]
    assert params["resultType"] == "core" and params["pageSize"] == 5
    query = params["query"]
    assert query.startswith("TITLE_ABS:(endometriosis) AND (")
    for clause in (
        'PUB_TYPE:"practice guideline"',
        'PUB_TYPE:"guideline"',
        'TITLE:"consensus"',
    ):
        assert clause in query
    # the old full-text keyword condition is gone
    assert " OR recommendation OR " not in query


def test_rows_keep_the_whole_abstract_as_text_and_are_never_dropped():
    result, _ = _run(RECORDS)
    first, second = result["data"]
    assert first["abstract"] == (
        "Objective To provide evidence-based guidance. Recommendations Offer hormonal therapy."
    )
    assert first["content"] == first["abstract"]
    assert first["publication_type"] == "Practice Guideline, Journal Article"
    assert first["journal"] == "J Obstet Gynaecol Can"
    assert first["is_guideline"] is True
    # no abstract and not typed a guideline: kept, flagged by its title
    assert second["abstract"] == "" and second["is_guideline"] is True
    assert second["url"] == "https://europepmc.org/article/PMC/PMC1234567"


def test_envelope_reports_the_upstream_total():
    result, _ = _run(RECORDS[:1], hit_count=145, limit=1)
    assert result["status"] == "success"
    assert result["metadata"]["total"] == 145
    assert result["metadata"]["retrieved"] == 1 and result["metadata"]["returned"] == 1
    assert result["metadata"]["truncated"] is True


def test_no_match_is_an_empty_success():
    result, _ = _run([], hit_count=0)
    assert result["status"] == "success" and result["data"] == []
    assert result["metadata"]["total"] == 0


def test_limit_is_clamped_to_europepmc_page_size():
    _, get = _run([], limit=500)
    assert get.call_args.kwargs["params"]["pageSize"] == 100


def test_http_failure_is_a_visible_error():
    tool = EuropePMCGuidelinesTool({"name": "EuropePMC_Guidelines_Search"})
    with patch.object(
        tool.session, "get", side_effect=requests.exceptions.ConnectionError("reset")
    ):
        result = tool.run({"query": "endometriosis"})
    assert (
        result["status"] == "error" and "Failed to search Europe PMC" in result["error"]
    )


def test_a_heading_does_not_run_into_its_text():
    """Europe PMC closes a heading straight into its text; the shared cleaner
    used by both Europe PMC tools must keep them apart."""
    from tooluniverse.europe_pmc_tool import _extract_text_from_html

    assert (
        _extract_text_from_html("<h4>Objectives</h4>To test <i>in vivo</i>.")
        == "Objectives To test in vivo."
    )
