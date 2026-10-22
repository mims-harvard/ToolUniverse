"""Regression tests for ENA's official limit=0 full-retrieval semantics."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.ena_portal_tool import ENAPortalTool


def _response(payload=None, *, text=""):
    response = MagicMock()
    response.json.return_value = payload
    response.text = text
    response.raise_for_status.return_value = None
    return response


@pytest.mark.parametrize(
    ("endpoint_type", "identifier"),
    [
        ("search_studies", "study_accession"),
        ("search_samples", "sample_accession"),
        ("search_runs", "run_accession"),
    ],
)
def test_limit_zero_is_forwarded_and_does_not_slice_everything_away(
    endpoint_type, identifier
):
    tool = ENAPortalTool(
        {"name": f"ENA_{endpoint_type}", "fields": {"endpoint_type": endpoint_type}}
    )
    records = [{identifier: "record-1"}, {identifier: "record-2"}]
    with patch(
        "tooluniverse.ena_portal_tool.requests.get",
        side_effect=[_response(records), _response(text="count\n2")],
    ) as get:
        result = tool.run({"query": "tax_eq(9606)", "limit": 0})

    assert get.call_args_list[0].kwargs["params"]["limit"] == 0
    assert result["data"] == records
    assert result["metadata"]["all_results_requested"] is True
    assert result["metadata"]["complete"] is True
    assert result["metadata"]["truncated"] is False
    assert result["metadata"]["suggested_limit"] is None


def test_limit_above_old_local_cap_is_forwarded_without_clamping():
    tool = ENAPortalTool(
        {"name": "ENA_studies", "fields": {"endpoint_type": "search_studies"}}
    )
    with patch(
        "tooluniverse.ena_portal_tool.requests.get",
        side_effect=[
            _response([{"study_accession": "PRJNA1"}]),
            _response(text="count\n123403"),
        ],
    ) as get:
        result = tool.run({"query": "tax_eq(9606)", "limit": 10_000})

    assert get.call_args_list[0].kwargs["params"]["limit"] == 10_000
    assert result["metadata"]["retrieval_limit_reached"] is False
    assert result["metadata"]["suggested_limit"] == 0
    assert "limit=0" in result["metadata"]["warning"]


@pytest.mark.parametrize("limit", [-1, -10, True, 1.5, "not-an-integer"])
def test_invalid_limits_fail_instead_of_being_silently_clamped(limit):
    tool = ENAPortalTool(
        {"name": "ENA_studies", "fields": {"endpoint_type": "search_studies"}}
    )
    with patch("tooluniverse.ena_portal_tool.requests.get") as get:
        result = tool.run({"query": "tax_eq(9606)", "limit": limit})

    assert result["status"] == "error"
    assert "non-negative integer" in result["error"]
    get.assert_not_called()


def test_all_search_schemas_expose_official_zero_limit():
    config_path = (
        Path(__file__).parents[2]
        / "src"
        / "tooluniverse"
        / "data"
        / "ena_portal_tools.json"
    )
    configs = {item["name"]: item for item in json.loads(config_path.read_text())}

    for name in (
        "ENAPortal_search_studies",
        "ENAPortal_search_samples",
        "ENAPortal_search_runs_fastq",
    ):
        limit_schema = configs[name]["parameter"]["properties"]["limit"]
        assert limit_schema["minimum"] == 0
        assert "maximum" not in limit_schema
        assert "Use 0" in limit_schema["description"]
