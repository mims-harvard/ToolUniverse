"""
Offline regression tests for two "a number that is not what its name says" defects.

Both tools parsed the upstream field carrying the real number and then reported
something else under a name that promised the real number:

1. ``ReactomeContent_search`` set ``total_results`` to ``len(all_entries)`` over a
   single unpaginated upstream page, so it reported Reactome's default page size
   of 10 for every query. Its own ``return_schema`` documents the field as
   "Total number of results". Reactome reports the real figure as
   ``numberOfMatches`` (live: query='DNA repair', species='Homo sapiens',
   types='Pathway' -> numberOfMatches 455 behind 10 returned entries).

2. ``ClinicalTrials_get_database_stats`` read ``totalStudiesCount`` and
   ``averageByteSize``; ClinicalTrials.gov /api/v2/stats/size returns
   ``totalStudies`` and ``averageSizeBytes``. Both fields were silently ``null``
   on every call while ``largest_studies`` populated from the correctly-named
   ``largestStudies``, so the tool looked healthy and served nulls as data.

Everything here mocks the HTTP layer -- no network.
"""

from unittest.mock import patch

import pytest

from tooluniverse.clinicaltrials_tool import CTGovAPITool
from tooluniverse.ctg_tool import ClinicalTrialsTool
from tooluniverse.reactome_content_tool import ReactomeContentTool


# --------------------------------------------------------------------------
# Reactome
# --------------------------------------------------------------------------


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload
        self.status_code = 200

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def _reactome_payload(n_entries, number_of_matches):
    """Shape of a real Reactome /search/query response, trimmed to what we read."""
    return {
        "rowCount": n_entries,
        "numberOfGroups": 1,
        "numberOfMatches": number_of_matches,
        "results": [
            {
                "typeName": "Pathway",
                "entries": [
                    {
                        "stId": f"R-HSA-{1000 + i}",
                        "name": f"Pathway <span class='highlighting'>{i}</span>",
                        "species": ["Homo sapiens"],
                        "compartmentNames": ["nucleoplasm"],
                        "isDisease": False,
                    }
                    for i in range(n_entries)
                ],
            }
        ],
    }


@pytest.fixture
def reactome_search_tool():
    return ReactomeContentTool(
        {"name": "ReactomeContent_search", "fields": {"endpoint": "search"}}
    )


def test_reactome_total_results_is_number_of_matches_not_page_length(
    reactome_search_tool,
):
    """total_results must be upstream numberOfMatches, never the page length."""
    payload = _reactome_payload(n_entries=10, number_of_matches=455)

    with patch(
        "tooluniverse.reactome_content_tool.requests.get",
        return_value=_FakeResponse(payload),
    ):
        result = reactome_search_tool.run({"query": "DNA repair"})

    data = result["data"]
    assert result["status"] == "success"
    # The defect: this was 10, the length of one upstream page.
    assert data["total_results"] == 455
    assert data["total_results"] != len(data["results"])
    # The list is still exactly what upstream handed us -- nothing shrunk.
    assert len(data["results"]) == 10


def test_reactome_reports_how_many_returned_and_that_more_exist(reactome_search_tool):
    """count/has_more/truncation_note tell the caller the list is a slice."""
    payload = _reactome_payload(n_entries=10, number_of_matches=455)

    with patch(
        "tooluniverse.reactome_content_tool.requests.get",
        return_value=_FakeResponse(payload),
    ):
        result = reactome_search_tool.run({"query": "DNA repair"})

    data = result["data"]
    assert data["count"] == 10
    assert data["count"] == len(data["results"])
    assert data["start"] == 0
    assert data["has_more"] is True
    assert result["truncated"] is True
    assert "455" in result["truncation_note"]


def test_reactome_no_truncation_signal_when_page_holds_everything(
    reactome_search_tool,
):
    payload = _reactome_payload(n_entries=3, number_of_matches=3)

    with patch(
        "tooluniverse.reactome_content_tool.requests.get",
        return_value=_FakeResponse(payload),
    ):
        result = reactome_search_tool.run({"query": "very specific thing"})

    data = result["data"]
    assert data["count"] == 3
    assert data["total_results"] == 3
    assert data["has_more"] is False
    assert "truncated" not in result
    assert "truncation_note" not in result


def test_reactome_paging_uses_upstream_start_row_spelling(reactome_search_tool):
    """Reactome's offset parameter is literally named 'Start row', with a space.

    Confirmed in Reactome's own OpenAPI document
    (https://reactome.org/ContentService/v3/api-docs -> /search/query lists
    'Start row') and confirmed live: sending `start=5` is silently ignored and
    re-serves page 0. A plausible-looking `start` would page nowhere and fail
    silently, so pin the exact wire name.
    """
    payload = _reactome_payload(n_entries=5, number_of_matches=455)

    with patch(
        "tooluniverse.reactome_content_tool.requests.get",
        return_value=_FakeResponse(payload),
    ) as mock_get:
        result = reactome_search_tool.run(
            {"query": "DNA repair", "rows": 5, "start": 450}
        )

    sent = mock_get.call_args.kwargs["params"]
    assert sent["rows"] == 5
    assert sent["Start row"] == 450
    assert "start" not in sent

    data = result["data"]
    assert data["start"] == 450
    assert data["count"] == 5
    assert data["total_results"] == 455
    # 450 + 5 == 455, so this is the last page.
    assert data["has_more"] is False


def test_reactome_rows_widens_the_page_beyond_the_old_hard_cap(reactome_search_tool):
    """The old code hard-capped results at 30; an explicit rows must be honoured."""
    payload = _reactome_payload(n_entries=100, number_of_matches=455)

    with patch(
        "tooluniverse.reactome_content_tool.requests.get",
        return_value=_FakeResponse(payload),
    ):
        result = reactome_search_tool.run({"query": "DNA repair", "rows": 100})

    data = result["data"]
    assert data["count"] == 100
    assert len(data["results"]) == 100
    assert data["total_results"] == 455


def test_reactome_falls_back_to_page_length_when_matches_absent(reactome_search_tool):
    """If upstream ever omits numberOfMatches, degrade to the old behaviour."""
    payload = _reactome_payload(n_entries=4, number_of_matches=None)
    del payload["numberOfMatches"]

    with patch(
        "tooluniverse.reactome_content_tool.requests.get",
        return_value=_FakeResponse(payload),
    ):
        result = reactome_search_tool.run({"query": "anything"})

    assert result["data"]["total_results"] == 4


@pytest.mark.parametrize("bad_rows", [0, -1, 1001])
def test_reactome_rejects_out_of_range_rows(reactome_search_tool, bad_rows):
    with patch("tooluniverse.reactome_content_tool.requests.get") as mock_get:
        result = reactome_search_tool.run({"query": "x", "rows": bad_rows})

    assert result["status"] == "error"
    assert "rows" in result["error"]
    mock_get.assert_not_called()


def test_reactome_rejects_negative_start(reactome_search_tool):
    with patch("tooluniverse.reactome_content_tool.requests.get") as mock_get:
        result = reactome_search_tool.run({"query": "x", "start": -1})

    assert result["status"] == "error"
    assert "start" in result["error"]
    mock_get.assert_not_called()


# --------------------------------------------------------------------------
# ClinicalTrials.gov /api/v2/stats/size
# --------------------------------------------------------------------------

# Exact shape of the live response (values from a real call).
CTG_STATS_PAYLOAD = {
    "totalStudies": 597913,
    "averageSizeBytes": 17275,
    "percentiles": {"5%": 4558, "50%": 9825, "99%": 149545},
    "ranges": [
        {"sizeRange": "0 - 10 kb", "studiesCount": 316150},
        {"sizeRange": "10 - 20 kb", "studiesCount": 187915},
    ],
    "largestStudies": [{"id": "NCT02723955", "sizeBytes": 3596689}],
}

# Keys the two implementations used to read. Neither has ever been returned by
# ClinicalTrials.gov -- pin that so nobody "restores" them.
NEVER_UPSTREAM_KEYS = ["totalStudiesCount", "averageByteSize"]


@pytest.mark.parametrize("absent_key", NEVER_UPSTREAM_KEYS)
def test_ctg_stats_payload_does_not_contain_the_old_keys(absent_key):
    assert absent_key not in CTG_STATS_PAYLOAD


@pytest.fixture
def ctg_stats_tool():
    return ClinicalTrialsTool(
        {
            "name": "ClinicalTrials_get_database_stats",
            "query_schema": {},
            "parameter": {"type": "object", "properties": {}, "required": []},
            "fields": {"operation": "stats_size"},
        }
    )


def test_ctg_tool_maps_total_studies_and_average_size_bytes(ctg_stats_tool):
    """ctg_tool.py read totalStudiesCount/averageByteSize -> both were null."""
    with patch("requests.get", return_value=_FakeResponse(CTG_STATS_PAYLOAD)):
        result = ctg_stats_tool.run({})

    data = result["data"]
    assert data["total_studies"] == 597913
    assert data["average_byte_size"] == 17275
    # The defect presented these as null while largest_studies populated,
    # which is what made the tool look healthy.
    assert data["total_studies"] is not None
    assert data["average_byte_size"] is not None
    assert data["largest_studies"] == CTG_STATS_PAYLOAD["largestStudies"]


def test_ctg_tool_surfaces_the_size_distribution(ctg_stats_tool):
    """percentiles/ranges were parsed and discarded despite being advertised."""
    with patch("requests.get", return_value=_FakeResponse(CTG_STATS_PAYLOAD)):
        result = ctg_stats_tool.run({})

    data = result["data"]
    assert data["byte_size_percentiles"] == CTG_STATS_PAYLOAD["percentiles"]
    assert data["size_ranges"] == CTG_STATS_PAYLOAD["ranges"]


def test_ctgov_api_tool_maps_average_size_bytes():
    """clinicaltrials_tool.py had the right totalStudies but wrong averageByteSize."""
    tool = CTGovAPITool({"name": "x", "fields": {"operation": "stats_size"}})

    with patch(
        "tooluniverse.clinicaltrials_tool.requests.get",
        return_value=_FakeResponse(CTG_STATS_PAYLOAD),
    ):
        data = tool._get_stats_size()["data"]

    assert data["total_studies"] == 597913
    assert data["average_byte_size"] == 17275
    assert data["byte_size_percentiles"] == CTG_STATS_PAYLOAD["percentiles"]
    assert data["size_ranges"] == CTG_STATS_PAYLOAD["ranges"]


def test_both_clinicaltrials_implementations_agree_on_the_same_payload(ctg_stats_tool):
    """The two implementations disagreed; pin that they no longer do."""
    with patch("requests.get", return_value=_FakeResponse(CTG_STATS_PAYLOAD)):
        ctg = ctg_stats_tool.run({})["data"]

    other_tool = CTGovAPITool({"name": "x", "fields": {"operation": "stats_size"}})
    with patch(
        "tooluniverse.clinicaltrials_tool.requests.get",
        return_value=_FakeResponse(CTG_STATS_PAYLOAD),
    ):
        ctgov = other_tool._get_stats_size()["data"]

    for field in ("total_studies", "average_byte_size", "byte_size_percentiles"):
        assert ctg[field] == ctgov[field], field
