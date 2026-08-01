from __future__ import annotations

import json

import pytest

from tooluniverse import ToolUniverse
from tooluniverse.vsd_coverage import (
    VSDCoverageError,
    normalize_capability_request,
    resolve_capability,
)

pytestmark = pytest.mark.unit


class _Registry:
    tool_files = {}

    def __init__(self, tools):
        self.all_tools = tools


def _dynamic_tool(name="ExistingRecords"):
    return {
        "name": name,
        "type": "VSDDynamicRESTTool",
        "description": "Retrieve reviewed disease registry records by disease.",
        "category": "special_tools",
        "parameter": {
            "type": "object",
            "properties": {"disease": {"type": "string"}},
            "required": ["disease"],
        },
        "return_schema": {
            "type": "object",
            "properties": {"registry_id": {"type": "string"}},
        },
        "vsd_operation": {
            "method": "GET",
            "endpoint": "https://registry.example.org/v1/diseases",
            "response_schema": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {"registry_id": {"type": "string"}},
                },
            },
        },
        "vsd_capability": {"operation_id": "registry.search_diseases"},
    }


def test_exact_operation_identity_prevents_duplicate_generation():
    result = resolve_capability(
        _Registry([_dynamic_tool()]),
        {
            "description": "Retrieve disease registry records",
            "provider": "registry.example.org",
            "operation_id": "registry.search_diseases",
            "required_inputs": ["disease"],
            "output_fields": ["registry_id"],
        },
    )["data"]

    assert result["classification"] == "existing_exact"
    assert result["recommended_action"] == "use_existing"
    assert result["matches"][0]["operation_match"] is True


def test_same_provider_different_operation_is_partial_not_missing():
    result = resolve_capability(
        _Registry([_dynamic_tool()]),
        {
            "description": "Retrieve registry investigator contact information",
            "provider": "https://registry.example.org",
            "required_inputs": ["investigator_id"],
            "output_fields": ["email"],
        },
    )["data"]

    assert result["classification"] == "existing_partial"
    assert result["recommended_action"] == "review_existing_or_extend_provider"
    assert result["matches"][0]["provider_match"] is True


def test_composed_workflows_are_included_in_coverage_results():
    workflow = {
        "name": "RareDiseaseEvidenceWorkflow",
        "type": "ComposeTool",
        "description": "Combine rare disease genes, phenotypes, and literature evidence.",
        "required_tools": ["ExistingRecords", "PubMed_search_articles"],
        "parameter": {
            "type": "object",
            "properties": {"disease": {"type": "string"}},
        },
    }
    result = resolve_capability(
        _Registry([_dynamic_tool(), workflow]),
        {"description": "rare disease genes phenotypes literature evidence"},
    )["data"]

    assert result["workflow_matches"] == 1
    assert any(match["kind"] == "workflow" for match in result["matches"])


def test_genuinely_unmatched_capability_is_missing_and_not_persisted(tmp_path):
    registry = _Registry([_dynamic_tool()])
    result = resolve_capability(
        registry,
        {"description": "quantum microscope calibration waveform optimizer"},
    )["data"]

    assert result["classification"] == "missing"
    assert result["matches"] == []
    assert list(tmp_path.iterdir()) == []
    assert "not persisted" in result["privacy"]


@pytest.mark.parametrize(
    "capability, message",
    [
        ({"description": "x"}, "3-500"),
        ({"description": "valid request", "endpoint": "http://example.org"}, "HTTPS"),
        (
            {
                "description": "valid request",
                "provider": "one.example.org",
                "endpoint": "https://two.example.org/path",
            },
            "does not match",
        ),
        (
            {"description": "valid request", "required_inputs": ["bad field"]},
            "stable field",
        ),
    ],
)
def test_request_validation_fails_closed(capability, message):
    with pytest.raises(VSDCoverageError, match=message):
        normalize_capability_request(capability)


def test_capability_and_registry_digests_are_deterministic():
    registry = _Registry([_dynamic_tool()])
    request = {"description": "Retrieve disease registry records"}
    first = resolve_capability(registry, request)["data"]
    second = resolve_capability(registry, request)["data"]

    assert first["capability_id"] == second["capability_id"]
    assert first["registry_sha256"] == second["registry_sha256"]
    json.dumps(first, allow_nan=False)


def test_real_registry_resolves_als_to_orphanet_without_loading_every_tool():
    tooluniverse = ToolUniverse()
    try:
        tooluniverse.load_tools(include_tools=["VSDResolveCapability"], quiet=True)
        result = tooluniverse.run_one_function(
            {
                "name": "VSDResolveCapability",
                "arguments": {
                    "description": "rare disease registry genes and phenotypes",
                    "required_inputs": ["disease"],
                    "limit": 10,
                },
            },
            use_cache=False,
        )
    finally:
        tooluniverse.close()

    assert result["status"] == "success"
    assert result["data"]["classification"] != "missing"
    names = {match["name"] for match in result["data"]["matches"]}
    assert {"Orphanet_get_genes", "Orphanet_get_phenotypes"} & names
    assert len(tooluniverse.all_tools) <= 1


def test_real_registry_recognizes_existing_fda_label_capability():
    tooluniverse = ToolUniverse()
    try:
        result = resolve_capability(
            tooluniverse,
            {
                "description": "retrieve FDA drug label by set identifier",
                "provider": "FDA",
                "required_inputs": ["set_id"],
                "limit": 10,
            },
        )["data"]
    finally:
        tooluniverse.close()

    assert result["classification"] != "missing"
    assert any("FDA" in match["name"] for match in result["matches"])
