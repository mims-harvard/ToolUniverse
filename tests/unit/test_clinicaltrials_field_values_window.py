import json
from pathlib import Path
from unittest.mock import Mock, patch

from tooluniverse.ctg_tool import ClinicalTrialsTool


_CONFIG_PATH = (
    Path(__file__).resolve().parents[2]
    / "src/tooluniverse/data/clinicaltrials_gov_tools.json"
)


def _config():
    configs = json.loads(_CONFIG_PATH.read_text())
    return next(
        config
        for config in configs
        if config["name"] == "ClinicalTrials_get_field_values"
    )


def _tool():
    tool = ClinicalTrialsTool(_config())
    # Isolate the field-values request from the registry-denominator lookups.
    tool._registry_total_studies = lambda: None
    tool._is_multi_valued_field = lambda field_path: None
    return tool


def _response(unique=1000, accessible=250):
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = [
        {
            "field": "Condition",
            "uniqueValuesCount": unique,
            "missingStudiesCount": 7,
            "topValues": [
                {"value": f"condition-{i}", "studiesCount": 1000 - i}
                for i in range(accessible)
            ],
        }
    ]
    return response


def test_field_values_pages_locally_with_exact_and_accessible_counts_separated():
    tool = _tool()
    with patch("requests.get", return_value=_response()) as get:
        result = tool.run(
            {
                "field": "Condition",
                "page_size": 25,
                "offset": 50,
            }
        )

    assert result["status"] == "success"
    assert len(result["data"]["values"]) == 25
    assert result["data"]["values"][0]["value"] == "condition-50"
    assert result["data"]["unique_values_count"] == 1000
    assert result["data"]["accessible_values_count"] == 250
    assert result["data"]["missing_studies_count"] == 7
    assert result["metadata"]["upstream_truncated"] is True
    assert result["metadata"]["next_offset"] == 75
    assert result["metadata"]["total_results_is_exact"] is True
    sent = get.call_args.kwargs["params"]
    assert "pageSize" not in sent and "offset" not in sent


def test_low_cardinality_field_can_be_reported_complete():
    tool = _tool()
    with patch("requests.get", return_value=_response(unique=6, accessible=6)):
        result = tool.run({"field": "Phase", "page_size": 50, "offset": 0})

    assert result["metadata"]["upstream_truncated"] is False
    assert result["metadata"]["result_set_complete"] is True
    assert result["metadata"]["has_more"] is False
    assert result["data"]["unique_values_count"] == 6


def test_invalid_field_value_local_page_fails_before_network():
    tool = _tool()
    with patch("requests.get") as get:
        assert tool.run({"field": "Phase", "page_size": 0})["status"] == "error"
        assert tool.run({"field": "Phase", "page_size": True})["status"] == "error"
        assert tool.run({"field": "Phase", "offset": -1})["status"] == "error"
        assert tool.run({"field": "Phase", "offset": False})["status"] == "error"
    get.assert_not_called()
