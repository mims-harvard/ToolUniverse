from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

from tooluniverse import vsd_dynamic_rest

pytestmark = pytest.mark.unit


MODULE_PATH = (
    Path(__file__).parents[2] / "examples" / "vsd" / "dynamic_rest_als_case_study.py"
)
SPEC = importlib.util.spec_from_file_location("vsd_dynamic_rest_case_study", MODULE_PATH)
assert SPEC and SPEC.loader
study = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = study
SPEC.loader.exec_module(study)


def _request_metadata(size: int = 100) -> dict:
    return {
        "status_code": 200,
        "content_type": "application/json",
        "response_bytes": size,
        "redirects": 0,
    }


def _trial(nct_id: str, *, status: str, state: str) -> dict:
    return {
        "protocolSection": {
            "identificationModule": {"nctId": nct_id, "briefTitle": f"Study {nct_id}"},
            "statusModule": {"overallStatus": status},
            "designModule": {"phases": ["PHASE2"], "studyType": "INTERVENTIONAL"},
            "conditionsModule": {"conditions": ["Amyotrophic Lateral Sclerosis"]},
            "armsInterventionsModule": {
                "interventions": [{"name": "Investigational therapy", "type": "DRUG"}]
            },
            "sponsorCollaboratorsModule": {"leadSponsor": {"name": "Research center"}},
            "contactsLocationsModule": {
                "locations": [
                    {
                        "facility": "ALS Center",
                        "city": "Boston",
                        "state": state,
                        "country": "United States",
                        "status": "RECRUITING",
                    }
                ]
            },
        }
    }


def test_case_runs_two_real_tooluniverse_calls_and_writes_artifacts(
    monkeypatch, tmp_path: Path
):
    """The study searches, follows an ID, summarizes, and writes stable evidence."""
    trials = [
        _trial("NCT00000002", status="RECRUITING", state="Massachusetts"),
        _trial("NCT00000001", status="NOT_YET_RECRUITING", state="California"),
    ]
    calls = []

    def fake_get(url, params, *, timeout):
        calls.append((url, params, timeout))
        if url.endswith("/studies"):
            return {
                "studies": trials,
                "totalCount": 9,
                "nextPageToken": "next",
            }, _request_metadata()
        assert url.endswith("/studies/NCT00000001")
        return trials[1], _request_metadata()

    monkeypatch.setattr(vsd_dynamic_rest, "_safe_get_json", fake_get)
    evidence = study.run_case()
    json_path, markdown_path = study.write_artifacts(evidence, tmp_path)

    assert len(calls) == 2
    assert calls[0][1]["query.cond"] == "Amyotrophic Lateral Sclerosis"
    assert evidence["detail_follow_up"]["selected_nct_id"] == "NCT00000001"
    assert evidence["detail_follow_up"]["identifier_matches_search"] is True
    assert evidence["search"]["status_counts"] == {
        "NOT_YET_RECRUITING": 1,
        "RECRUITING": 1,
    }
    assert (
        json.loads(json_path.read_text(encoding="utf-8"))["search"]["returned_records"]
        == 2
    )
    report = markdown_path.read_text(encoding="utf-8")
    assert "Reviewed Dynamic REST ALS Validation" in report
    assert "NCT00000001" in report
    assert "not trial matching" in report
