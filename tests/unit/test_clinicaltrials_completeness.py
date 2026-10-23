from unittest.mock import MagicMock, patch

from tooluniverse.ctg_tool import ClinicalTrialsTool


def _tool(operation):
    return ClinicalTrialsTool(
        {
            "name": f"ClinicalTrials_{operation}",
            "type": "ClinicalTrialsTool",
            "fields": {"operation": operation},
            "query_schema": {},
            "parameter": {"properties": {}},
        }
    )


def _response(payload):
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = payload
    return response


@patch("requests.get")
def test_get_study_does_not_silently_cap_detail_lists(mock_get):
    arm_groups = [
        {"label": f"Arm {i}", "type": "EXPERIMENTAL", "interventionNames": []}
        for i in range(12)
    ]
    interventions = [
        {"name": f"Drug {i}", "type": "DRUG", "description": "test"} for i in range(14)
    ]
    primary = [{"measure": f"Outcome {i}"} for i in range(7)]
    locations = [{"facility": f"Site {i}"} for i in range(8)]
    references = [{"pmid": str(i)} for i in range(9)]
    mock_get.return_value = _response(
        {
            "protocolSection": {
                "identificationModule": {"nctId": "NCT06447662"},
                "armsInterventionsModule": {
                    "armGroups": arm_groups,
                    "interventions": interventions,
                },
                "outcomesModule": {"primaryOutcomes": primary},
                "contactsLocationsModule": {"locations": locations},
                "referencesModule": {"references": references},
            }
        }
    )

    data = _tool("get_study").run({"nct_id": "NCT06447662"})["data"]

    assert data["arm_count"] == len(data["arms"]) == 12
    assert data["intervention_count"] == len(data["interventions"]) == 14
    assert data["primary_outcome_count"] == len(data["primary_outcomes"]) == 7
    assert data["location_count"] == len(data["locations"]) == 8
    assert data["reference_count"] == len(data["references"]) == 9


@patch("requests.get")
def test_search_preserves_all_interventions_and_honors_aliases(mock_get):
    interventions = [{"name": f"Drug {i}"} for i in range(12)]
    mock_get.return_value = _response(
        {
            "totalCount": 1,
            "studies": [
                {
                    "protocolSection": {
                        "identificationModule": {"nctId": "NCT00000001"},
                        "armsInterventionsModule": {"interventions": interventions},
                    }
                }
            ],
        }
    )

    study = _tool("search").run({"query": "precision oncology", "max_results": 25})[
        "data"
    ]["studies"][0]

    assert study["intervention_count"] == 12
    assert len(study["interventions"]) == 5
    assert study["interventions_truncated"] is True
    params = mock_get.call_args.kwargs["params"]
    assert params["query.term"] == "precision oncology"
    assert params["pageSize"] == 25
