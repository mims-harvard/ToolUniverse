"""Regression tests for ClinicalTrials.gov single-study identifier handling."""

from unittest.mock import patch

from tooluniverse.clinicaltrials_tool import CTGovAPITool
from tooluniverse.ctg_tool import ClinicalTrialsTool


def _tool():
    return CTGovAPITool(
        {"name": "ClinicalTrials_get_study", "fields": {"operation": "get_study"}}
    )


def test_get_study_rejects_path_like_nct_id_before_request():
    """A path segment can otherwise reach a different ClinicalTrials endpoint."""
    with patch("tooluniverse.clinicaltrials_tool.requests.get") as get:
        result = _tool().run({"nct_id": "../stats/size"})

    assert result == {
        "status": "error",
        "error": "nct_id must be an NCT identifier (e.g., 'NCT04280705')",
    }
    get.assert_not_called()


def test_get_study_normalizes_lowercase_nct_id():
    """Valid identifiers remain usable when an agent emits a lowercase prefix."""
    response = {
        "protocolSection": {
            "identificationModule": {"nctId": "NCT04280705"},
        }
    }
    with patch("tooluniverse.clinicaltrials_tool.requests.get") as get:
        get.return_value.json.return_value = response
        get.return_value.raise_for_status.return_value = None
        result = _tool().run({"nct_id": "nct04280705"})

    assert result["status"] == "success"
    assert result["metadata"]["nct_id"] == "NCT04280705"
    assert get.call_args.args[0].endswith("/NCT04280705")


def test_ctg_get_study_rejects_path_like_nct_id_before_request():
    """The sibling ClinicalTrials wrapper must keep the same URL boundary."""
    tool = ClinicalTrialsTool(
        {
            "name": "ClinicalTrials_get_study",
            "parameter": {"type": "object", "properties": {}},
            "query_schema": {},
            "fields": {"operation": "get_study"},
        }
    )
    with patch("requests.get") as get:
        result = tool._run_get_study({"nct_id": "../stats/size"})

    assert result == {
        "status": "error",
        "error": "nct_id must be an NCT identifier (e.g., 'NCT04280705')",
    }
    get.assert_not_called()
