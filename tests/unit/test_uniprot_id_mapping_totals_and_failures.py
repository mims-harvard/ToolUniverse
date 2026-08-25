"""Regression guard for Fix-R58-3: UniProt_id_mapping reported a page size as
the mapping count and claimed nothing had failed.

Three separate figures were thrown away from a payload the tool already
parsed:

  * `failedIds` -- inputs UniProt could not map at all. `failed_ids` was a
    hardcoded `[]`, so a typo'd accession vanished silently.
  * the `x-total-results` header -- the real number of mappings.
    `mapped_count` reported only the rows on the page returned.
  * the page size itself. Feature-26A-13 noted UniProt's status endpoint can
    303-redirect straight to a results page; that page uses its own
    25-record default rather than the size the tool asks for, and the old
    code took it as the final answer.

Confirmed live (from_db UniProtKB_AC-ID, to_db PDB):

    Q9F663                              -> x-total-results 83,  failedIds []
    Q9F663+NOTAREALACC99+P0DTC2         -> x-total-results 2236,
                                           failedIds ['NOTAREALACC99']

Before the fix the second call returned `mapped_count: 25, failed_ids: []`
with P0DTC2 entirely absent and no indication anything was missing.

Fix-R20A-1 had already settled the same defect for the sibling
UniProtIDMappingTool; this applies its resolution to the second copy of the
logic in UniProtRESTTool. These stub HTTP rather than any private helper, so
they assert what a caller receives.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.uniprot_tool import UniProtRESTTool

pytestmark = pytest.mark.unit

_CONFIG = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "tooluniverse"
    / "data"
    / "uniprot_tools.json"
)


def _tool():
    cfg = next(
        c for c in json.loads(_CONFIG.read_text()) if c["name"] == "UniProt_id_mapping"
    )
    return UniProtRESTTool(cfg)


def _resp(body, headers=None):
    r = MagicMock()
    r.raise_for_status = MagicMock()
    r.json.return_value = body
    r.headers = headers or {}
    r.status_code = 200
    return r


def _rows(n, from_id="Q9F663"):
    return [{"from": from_id, "to": f"PDB{i}"} for i in range(n)]


def _run(status_body, status_headers, results_body, results_headers):
    """Stub the submit/poll/fetch sequence and return the tool's output."""
    calls = []

    def fake_get(url, **kwargs):
        calls.append((url, kwargs.get("params")))
        if "/status/" in url:
            return _resp(status_body, status_headers)
        return _resp(results_body, results_headers)

    tool = _tool()
    with (
        patch(
            "tooluniverse.uniprot_tool.requests.post",
            return_value=_resp({"jobId": "JOB1"}),
        ),
        patch("tooluniverse.uniprot_tool.requests.get", side_effect=fake_get),
    ):
        result = tool.run(
            {
                "ids": ["Q9F663", "NOTAREALACC99", "P0DTC2"],
                "from_db": "UniProtKB_AC-ID",
                "to_db": "PDB",
            }
        )
    return result, calls


def test_failed_ids_are_reported_not_hardcoded_empty():
    result, _ = _run(
        {"jobStatus": "FINISHED"},
        {},
        {"results": _rows(3), "failedIds": ["NOTAREALACC99"]},
        {"x-total-results": "3"},
    )

    assert result["status"] == "success"
    assert result["data"]["failed_ids"] == ["NOTAREALACC99"]


def test_upstream_total_is_surfaced_and_truncation_disclosed():
    result, _ = _run(
        {"jobStatus": "FINISHED"},
        {},
        {"results": _rows(500), "failedIds": []},
        {"x-total-results": "2236"},
    )

    data = result["data"]
    assert data["total_results"] == 2236
    assert data["mapped_count"] == 500
    assert data["truncated"] is True
    assert "500 of 2236" in data["truncation_note"]


def test_complete_result_is_not_flagged_as_truncated():
    result, _ = _run(
        {"jobStatus": "FINISHED"},
        {},
        {"results": _rows(83), "failedIds": []},
        {"x-total-results": "83"},
    )

    data = result["data"]
    assert data["total_results"] == 83
    assert data["mapped_count"] == 83
    assert data["truncated"] is False
    assert "truncation_note" not in data


def test_redirected_status_page_is_refetched_at_full_size():
    """Feature-26A-13's 303 path must not be taken as the final answer.

    The status poll carries a short default page; the fix treats that as
    'job done' and re-fetches with an explicit size, which is what stops the
    silent truncation to 25.
    """
    result, calls = _run(
        {"results": _rows(25), "failedIds": []},
        {"x-total-results": "83"},
        {"results": _rows(83), "failedIds": ["NOTAREALACC99"]},
        {"x-total-results": "83"},
    )

    data = result["data"]
    assert data["mapped_count"] == 83, "took the 25-row redirect page as final"
    assert data["failed_ids"] == ["NOTAREALACC99"]
    results_calls = [(u, p) for u, p in calls if "/results/" in u]
    assert results_calls, "never re-fetched the results endpoint"
    assert results_calls[0][1] == {"size": 500}


def test_falls_back_to_the_status_payload_when_refetch_is_empty():
    """Losing the answer would be worse than returning a short page."""
    result, _ = _run(
        {"results": _rows(25), "failedIds": ["NOTAREALACC99"]},
        {"x-total-results": "25"},
        {},
        {},
    )

    data = result["data"]
    assert data["mapped_count"] == 25
    assert data["failed_ids"] == ["NOTAREALACC99"]
