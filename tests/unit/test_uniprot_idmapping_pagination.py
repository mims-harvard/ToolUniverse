"""Regression guard for Fix-R24A-2: UniProtIDMappingTool._submit_and_poll
silently truncated results to UniProt's unpaginated default page size (25)
for jobs that complete almost instantly.

Confirmed live (instrumented poll loop against the real API): for a job
that finishes fast, UniProt's /idmapping/status/{job_id} endpoint can
return the results embedded directly in the status response instead of
{"jobStatus": "FINISHED"} -- e.g. P00533 (EGFR) -> PDB genuinely has 354
matches, but the embedded status-response copy only had 25 (UniProt's
default page size when no `size` param is set). The old code treated that
embedded copy as authoritative and returned it immediately, bypassing the
already-correct paginated fetch (`size=500`) a few lines below. Fixed by
treating an embedded "results" key the same as "FINISHED" -- fall through
to the paginated fetch either way instead of returning early.
"""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.uniprot_idmapping_tool import UniProtIDMappingTool

pytestmark = pytest.mark.unit


def _tool():
    return UniProtIDMappingTool(
        {"name": "uniprot_idmap_test", "fields": {"endpoint_type": "to_pdb"}}
    )


def _resp(json_body):
    r = MagicMock()
    r.raise_for_status = MagicMock()
    r.json.return_value = json_body
    return r


class TestFastJobDoesNotTruncate:
    def test_embedded_status_results_are_not_returned_directly(self):
        tool = _tool()
        submit_resp = _resp({"jobId": "job123"})
        # Status response for a near-instant job: no "jobStatus", just a
        # small embedded (unpaginated) results preview -- confirmed live.
        status_resp = _resp({"results": [{"from": "P00533", "to": "1M17"}] * 25})
        paginated_resp = _resp(
            {"results": [{"from": "P00533", "to": f"PDB{i}"} for i in range(354)]}
        )

        with (
            patch(
                "tooluniverse.uniprot_idmapping_tool.requests.post",
                return_value=submit_resp,
            ),
            patch(
                "tooluniverse.uniprot_idmapping_tool.requests.get",
                side_effect=[status_resp, paginated_resp],
            ) as mock_get,
        ):
            result = tool.run({"uniprot_ids": "P00533"})

        assert result["status"] == "success"
        assert result["data"]["result_count"] == 354
        # The second GET call must be the paginated results fetch with size=500.
        second_call = mock_get.call_args_list[1]
        assert second_call.kwargs["params"] == {"size": 500}

    def test_normal_finished_status_still_works(self):
        tool = _tool()
        submit_resp = _resp({"jobId": "job456"})
        status_resp = _resp({"jobStatus": "FINISHED"})
        paginated_resp = _resp({"results": [{"from": "P00533", "to": "1M17"}]})

        with (
            patch(
                "tooluniverse.uniprot_idmapping_tool.requests.post",
                return_value=submit_resp,
            ),
            patch(
                "tooluniverse.uniprot_idmapping_tool.requests.get",
                side_effect=[status_resp, paginated_resp],
            ),
        ):
            result = tool.run({"uniprot_ids": "P00533"})

        assert result["status"] == "success"
        assert result["data"]["result_count"] == 1
