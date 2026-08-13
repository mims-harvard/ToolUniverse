"""A paged ClinicalTrials.gov response must not publish its page size as a total.

ClinicalTrials.gov v2 returns `totalCount` on a first page and omits it on every
subsequent page -- that is, exactly when `pageToken` was supplied. The fallback

    "total_count": data.get("totalCount") or len(studies),

therefore filled the gap with the number of rows on the current page.

Measured live 2026-08-13, `query_cond: "silicosis"` with `page_size: 3`:

    page 1  total_count 20  (correct)
    page 2  total_count  3  (the page size)

Reproduced on mesothelioma: 64 then 5. Nothing in the response distinguished
the invented figure from the real one, so paging a query to the end left the
caller holding a denominator equal to their last page. The sibling
ClinicalTrialsSearchTool already omits the key in this situation rather than
inventing one.

Offline: the HTTP transport is patched, so no ClinicalTrials.gov request is made.
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.unit

CONFIG = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "tooluniverse"
    / "data"
    / "clinicaltrials_gov_tools.json"
)


def _config():
    """The shipped config, so the test cannot drift from the real tool."""
    with open(CONFIG) as fh:
        for cfg in json.load(fh):
            if cfg["name"] == "ClinicalTrials_search_studies":
                return cfg
    raise AssertionError(
        "ClinicalTrials_search_studies not in clinicaltrials_gov_tools.json"
    )


def _study(nct):
    return {
        "protocolSection": {
            "identificationModule": {"nctId": nct, "briefTitle": f"Study {nct}"},
            "statusModule": {"overallStatus": "COMPLETED"},
            "designModule": {"studyType": "INTERVENTIONAL", "phases": ["PHASE2"]},
            "conditionsModule": {"conditions": ["Silicosis"]},
        }
    }


class _Response:
    status_code = 200

    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def _search(payload, arguments):
    from tooluniverse.ctg_tool import ClinicalTrialsTool

    tool = ClinicalTrialsTool(_config())
    with patch("requests.get", return_value=_Response(payload)):
        return tool._run_search(arguments)["data"]


PAGED = {"studies": [_study(f"NCT0000000{i}") for i in range(3)]}
FIRST = dict(PAGED, totalCount=20, nextPageToken="tok")


class TestPagedResponse:
    def test_total_count_is_null_rather_than_the_page_size(self):
        data = _search(PAGED, {"query_cond": "silicosis", "page_token": "tok"})
        assert data["total_count"] is None
        assert data["total_count"] != len(data["studies"])

    def test_the_null_is_explained(self):
        data = _search(PAGED, {"query_cond": "silicosis", "page_token": "tok"})
        assert "does not report" in data["total_count_note"]
        assert "first page" in data["total_count_note"].lower()

    def test_the_rows_themselves_still_come_back(self):
        """Suppressing the total must not cost the caller the page."""
        data = _search(PAGED, {"query_cond": "silicosis", "page_token": "tok"})
        assert len(data["studies"]) == 3


class TestUnpagedResponse:
    def test_a_reported_total_is_passed_through_unchanged(self):
        data = _search(FIRST, {"query_cond": "silicosis"})
        assert data["total_count"] == 20
        assert "total_count_note" not in data

    def test_a_genuine_zero_survives(self):
        """The old `or` could not express this: 0 is falsy but true.

        A query matching nothing reports totalCount 0, which the fallback
        replaced with len(studies) -- also 0 here, so the bug was invisible
        until a page had rows. The guard is on `is None` for that reason.
        """
        data = _search({"studies": [], "totalCount": 0}, {"query_cond": "zzznotreal"})
        assert data["total_count"] == 0
        assert "total_count_note" not in data
