import json
from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.zooma_tool import ZoomaTool


pytestmark = pytest.mark.unit


def _config():
    with open("src/tooluniverse/data/zooma_tools.json") as handle:
        return next(item for item in json.load(handle) if item["name"] == "ZOOMA_annotate_text")


def _response(payload):
    response = MagicMock()
    response.json.return_value = payload
    response.raise_for_status.return_value = None
    return response


def _annotation(index, confidence="GOOD"):
    return {
        "annotatedProperty": {"propertyValue": "cancer", "propertyType": "disease"},
        "semanticTags": [f"http://purl.obolibrary.org/obo/MONDO_{index:07d}"],
        "confidence": confidence,
        "provenance": {"source": {"name": "zooma", "type": "ONTOLOGY"}},
    }


def test_full_filtered_set_is_exactly_paginated():
    raw = [_annotation(i, "HIGH" if i < 3 else "GOOD") for i in range(8)]
    tool = ZoomaTool(_config())
    with patch("tooluniverse.zooma_tool.requests.get", return_value=_response(raw)):
        first = tool.run(
            {"property_value": "cancer", "min_confidence": "GOOD", "limit": 3}
        )
        second = tool.run(
            {
                "property_value": "cancer",
                "min_confidence": "GOOD",
                "limit": 3,
                "offset": first["metadata"]["next_offset"],
            }
        )
    assert first["metadata"]["raw_annotations"] == 8
    assert first["metadata"]["total_matches"] == 8
    assert first["metadata"]["next_offset"] == 3
    assert {item["curies"][0] for item in first["data"]}.isdisjoint(
        item["curies"][0] for item in second["data"]
    )


def test_confidence_filter_precedes_pagination():
    raw = [_annotation(1, "LOW"), _annotation(2, "HIGH"), _annotation(3, "GOOD")]
    tool = ZoomaTool(_config())
    with patch("tooluniverse.zooma_tool.requests.get", return_value=_response(raw)):
        result = tool.run(
            {"property_value": "cancer", "min_confidence": "GOOD", "limit": 1}
        )
    assert result["metadata"]["raw_annotations"] == 3
    assert result["metadata"]["total_matches"] == 2
    assert result["data"][0]["confidence"] == "HIGH"
    assert result["metadata"]["has_more"] is True


@pytest.mark.parametrize(
    "arguments",
    [
        {"property_value": "cancer", "limit": 0},
        {"property_value": "cancer", "limit": "10"},
        {"property_value": "cancer", "max_results": True},
        {"property_value": "cancer", "offset": -1},
        {"property_value": "cancer", "offset": "2"},
        {"property_value": "cancer", "min_confidence": "EXCELLENT"},
    ],
)
def test_invalid_controls_are_rejected(arguments):
    tool = ZoomaTool(_config())
    with patch("tooluniverse.zooma_tool.requests.get") as get:
        result = tool.run(arguments)
    assert result["status"] == "error"
    get.assert_not_called()


def test_non_array_success_payload_is_not_silent_empty_success():
    tool = ZoomaTool(_config())
    with patch(
        "tooluniverse.zooma_tool.requests.get", return_value=_response({"error": "bad"})
    ):
        result = tool.run({"property_value": "cancer"})
    assert result["status"] == "error"
    assert "JSON array" in result["error"]


def test_limit_parameter_takes_precedence_over_legacy_alias():
    tool = ZoomaTool(_config())
    with patch(
        "tooluniverse.zooma_tool.requests.get",
        return_value=_response([_annotation(i) for i in range(5)]),
    ):
        result = tool.run(
            {"property_value": "cancer", "limit": 2, "max_results": 4}
        )
    assert len(result["data"]) == 2
    assert result["metadata"]["limit"] == 2


def test_ontology_list_is_reachable_through_schema_and_request():
    tool = ZoomaTool(_config())
    with patch(
        "tooluniverse.zooma_tool.requests.get", return_value=_response([])
    ) as get:
        result = tool.run(
            {"property_value": "cancer", "ontologies": ["efo", "uberon"]}
        )
    assert result["status"] == "success"
    assert get.call_args.kwargs["params"]["filter"] == (
        "required:[none],ontologies:[efo,uberon]"
    )


def test_datasource_list_reports_exact_total():
    config = {
        "name": "ZOOMA_list_datasources",
        "fields": {"operation": "list_datasources"},
    }
    with patch(
        "tooluniverse.zooma_tool.requests.get",
        return_value=_response(
            [
                {"name": "uniprot", "type": "DATABASE", "uri": "https://uniprot.org"},
                {"name": "efo", "type": "ONTOLOGY", "uri": "https://ebi.ac.uk/efo"},
            ]
        ),
    ):
        result = ZoomaTool(config).run({})
    assert result["metadata"]["total_datasources"] == 2
    assert result["metadata"]["total_is_exact"] is True
