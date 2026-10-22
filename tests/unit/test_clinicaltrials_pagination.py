"""Regressions for ClinicalTrials intervention/sponsor token pagination."""

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from tooluniverse.ctg_tool import ClinicalTrialsTool

pytestmark = pytest.mark.unit


def _configs():
    path = Path(__file__).parents[2] / "src/tooluniverse/data/clinicaltrials_gov_tools.json"
    wanted = {
        "ClinicalTrials_search_by_intervention",
        "ClinicalTrials_search_by_sponsor",
    }
    return {item["name"]: item for item in json.loads(path.read_text()) if item["name"] in wanted}


def _response():
    response = Mock(status_code=200)
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "studies": [],
        "totalCount": 321,
        "nextPageToken": "opaque-next-token",
    }
    return response


def test_both_specialized_configs_expose_next_page_token():
    for config in _configs().values():
        assert "next_page_token" in config["parameter"]["properties"]


@patch("requests.get")
def test_token_is_forwarded_and_metadata_is_complete(mock_get):
    mock_get.return_value = _response()
    tool = ClinicalTrialsTool(_configs()["ClinicalTrials_search_by_intervention"])
    result = tool.run(
        {
            "intervention": "nivolumab",
            "page_size": 3,
            "next_page_token": "prior-token",
        }
    )

    params = mock_get.call_args.kwargs["params"]
    assert params["pageToken"] == "prior-token"
    assert params["pageSize"] == 3
    assert params["countTotal"] == "true"
    assert result["metadata"]["total_results"] == 321
    assert result["metadata"]["has_more"] is True
    assert result["metadata"]["next_page_token"] == "opaque-next-token"


@pytest.mark.parametrize("page_size", [0, 1001, 1.5, True])
def test_invalid_page_size_is_rejected_not_clamped(page_size):
    tool = ClinicalTrialsTool(_configs()["ClinicalTrials_search_by_sponsor"])
    result = tool.run({"sponsor": "NCI", "page_size": page_size})
    assert result["status"] == "error"
    assert result["parameter"] == "page_size"
