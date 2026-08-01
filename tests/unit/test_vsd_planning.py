from __future__ import annotations

import json

import pytest

from tooluniverse import ToolUniverse
from tooluniverse.base_tool import BaseTool
from tooluniverse.tool_finder_keyword import ToolFinderKeyword
from tooluniverse.vsd_planning import (
    VSDPlanWorkflow,
    VSDPlanningError,
    attach_capability_coverage,
    plan_workflow,
)

pytestmark = pytest.mark.unit


def _dynamic_tool(name="ExistingRegistryRecords"):
    return {
        "name": name,
        "type": "VSDDynamicRESTTool",
        "category": "special_tools",
        "description": "Retrieve reviewed disease registry records by disease.",
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


def _workflow(required_tools=None):
    return {
        "name": "RareDiseaseEvidenceWorkflow",
        "type": "ComposeTool",
        "category": "compose_tools",
        "description": "Combine rare disease genes phenotypes and literature evidence.",
        "required_tools": required_tools or ["ExistingRegistryRecords"],
        "parameter": {
            "type": "object",
            "properties": {"disease": {"type": "string"}},
        },
    }


class _Registry:
    tool_files = {}

    def __init__(self, tools):
        self.all_tools = tools
        self.all_tool_dict = {tool["name"]: tool for tool in tools}


def _capabilities():
    return [
        {
            "step_id": "registry",
            "description": "retrieve disease registry records",
            "provider": "registry.example.org",
            "operation_id": "registry.search_diseases",
            "required_inputs": ["disease"],
            "output_fields": ["registry_id"],
        },
        {
            "step_id": "contacts",
            "description": "retrieve registry investigator contacts",
            "provider": "registry.example.org",
            "required_inputs": ["investigator_id"],
            "output_fields": ["email"],
            "depends_on": ["registry"],
        },
        {
            "step_id": "calibration",
            "description": "quantum microscope calibration waveform optimizer",
            "depends_on": ["registry"],
        },
        {
            "step_id": "optional_export",
            "description": "interplanetary registry hologram export",
            "optional": True,
        },
    ]


def test_plan_orders_dependencies_and_routes_only_real_gaps_to_discovery():
    result = plan_workflow(
        _Registry([_dynamic_tool()]),
        goal="Build a reviewed rare disease registry evidence package",
        capabilities=_capabilities(),
        limit=5,
    )["data"]
    by_id = {step["step_id"]: step for step in result["steps"]}

    assert [step["step_id"] for step in result["steps"]] == [
        "registry",
        "contacts",
        "calibration",
        "optional_export",
    ]
    assert by_id["registry"]["state"] == "ready_existing"
    assert by_id["registry"]["finder_handoff"]["next_tool"] == "get_tool_info"
    assert by_id["contacts"]["state"] == "needs_review"
    assert by_id["calibration"]["state"] == "missing"
    assert by_id["calibration"]["finder_handoff"] == {
        "next_tool": "VSDDiscoverAPICandidates",
        "arguments": {
            "query": "quantum microscope calibration waveform optimizer",
            "limit": 5,
        },
        "execution_allowed": False,
    }
    assert by_id["optional_export"]["state"] == "optional_gap"
    assert result["overall_action"] == "discover_missing_capabilities"
    assert result["required_gap_count"] == 1
    assert result["optional_gap_count"] == 1
    assert result["execution_allowed"] is False


def test_exact_composed_workflow_is_preferred_when_dependencies_exist():
    registry = _Registry([_dynamic_tool(), _workflow()])
    result = plan_workflow(
        registry,
        goal="combine rare disease genes phenotypes literature evidence",
        capabilities=[
            {
                "step_id": "registry",
                "description": "retrieve disease registry records",
                "provider": "registry.example.org",
                "operation_id": "registry.search_diseases",
            }
        ],
    )["data"]

    assert result["overall_action"] == "use_existing_workflow"
    assert result["workflow_shortcut"]["name"] == "RareDiseaseEvidenceWorkflow"
    assert result["workflow_shortcut"]["can_auto_load_from_registry"] is True
    assert result["workflow_shortcut"]["dependencies_in_registry"] == [
        "ExistingRegistryRecords"
    ]


def test_workflow_with_missing_named_dependency_is_reported_not_recommended():
    result = plan_workflow(
        _Registry([_dynamic_tool(), _workflow(["MissingTool"])]),
        goal="combine rare disease genes phenotypes literature evidence",
        capabilities=[
            {
                "step_id": "registry",
                "description": "retrieve disease registry records",
                "provider": "registry.example.org",
                "operation_id": "registry.search_diseases",
            }
        ],
    )["data"]

    assert result["overall_action"] == "compose_existing_tools"
    assert result["workflow_shortcut"] is None
    assert result["workflow_candidates"][0]["dependencies_missing_from_registry"] == [
        "MissingTool"
    ]


def test_incomplete_workflow_limit_does_not_hide_complete_shortcut():
    incomplete = _workflow(["MissingTool"])
    incomplete["name"] = "AIncompleteWorkflow"
    complete = _workflow()
    complete["name"] = "BCompleteWorkflow"
    result = plan_workflow(
        _Registry([_dynamic_tool(), incomplete, complete]),
        goal="combine rare disease genes phenotypes literature evidence",
        capabilities=[
            {
                "step_id": "workflow",
                "description": "combine rare disease genes phenotypes literature evidence",
            }
        ],
        limit=1,
    )["data"]

    assert result["workflow_candidate_count"] == 2
    assert result["workflow_candidates"][0]["name"] == "AIncompleteWorkflow"
    assert result["workflow_shortcut"]["name"] == "BCompleteWorkflow"


def test_matching_workflow_is_not_a_shortcut_for_unrelated_exact_steps():
    unrelated = _dynamic_tool("UnrelatedExactTool")
    unrelated["description"] = "Retrieve weather station observations."
    unrelated["vsd_capability"] = {"operation_id": "weather.observations"}
    result = plan_workflow(
        _Registry([_dynamic_tool(), unrelated, _workflow()]),
        goal="combine rare disease genes phenotypes literature evidence",
        capabilities=[
            {
                "step_id": "weather",
                "description": "retrieve weather station observations",
                "operation_id": "weather.observations",
            }
        ],
    )["data"]

    assert result["steps"][0]["state"] == "ready_existing"
    assert result["workflow_candidates"][0]["name"] == "RareDiseaseEvidenceWorkflow"
    assert result["workflow_shortcut"] is None
    assert result["overall_action"] == "compose_existing_tools"


def test_plan_digest_is_deterministic_and_serializable():
    registry = _Registry([_dynamic_tool()])
    first = plan_workflow(
        registry,
        goal="Build a reviewed rare disease registry evidence package",
        capabilities=_capabilities(),
    )["data"]
    second = plan_workflow(
        registry,
        goal="Build a reviewed rare disease registry evidence package",
        capabilities=_capabilities(),
    )["data"]
    assert first["plan_id"] == second["plan_id"]
    assert first["plan_sha256"] == second["plan_sha256"]
    json.dumps(first, allow_nan=False)


def test_plan_preserves_exact_endpoint_identity_after_normalization():
    result = plan_workflow(
        _Registry([_dynamic_tool()]),
        goal="Build a reviewed rare disease registry evidence package",
        capabilities=[
            {
                "step_id": "registry",
                "description": "call the reviewed registry operation",
                "method": "GET",
                "endpoint": "https://registry.example.org/v1/diseases",
                "required_inputs": ["disease"],
                "output_fields": ["registry_id"],
            }
        ],
    )["data"]

    step = result["steps"][0]
    assert step["classification"] == "existing_exact"
    assert step["selected_match"]["operation_match"] is True
    assert step["state"] == "ready_existing"


def test_agent_fulfillment_never_routes_reasoning_steps_to_api_discovery():
    result = plan_workflow(
        _Registry([_dynamic_tool()]),
        goal="Build a reviewed rare disease registry evidence package",
        capabilities=[
            {
                "step_id": "registry",
                "description": "retrieve disease registry records",
                "operation_id": "registry.search_diseases",
            },
            {
                "step_id": "synthesis",
                "description": "synthesize a concise evidence report",
                "fulfillment": "agent",
                "depends_on": ["registry"],
            },
        ],
    )["data"]

    synthesis = result["steps"][1]
    assert synthesis["classification"] == "agent_native"
    assert synthesis["state"] == "ready_agent"
    assert synthesis["finder_handoff"]["next_tool"] is None
    assert synthesis["matches"] == []
    assert result["required_gap_count"] == 0


def test_agent_fulfillment_is_blocked_by_unresolved_dependencies():
    result = plan_workflow(
        _Registry([]),
        goal="Build a reviewed rare disease registry evidence package",
        capabilities=[
            {
                "step_id": "missing_source",
                "description": "retrieve unavailable specialist registry records",
            },
            {
                "step_id": "synthesis",
                "description": "synthesize a concise evidence report",
                "fulfillment": "agent",
                "depends_on": ["missing_source"],
            },
        ],
    )["data"]

    synthesis = result["steps"][1]
    assert synthesis["state"] == "blocked_by_dependencies"
    assert synthesis["dependency_blockers"] == ["missing_source"]
    assert synthesis["finder_handoff"]["next_tool"] is None


@pytest.mark.parametrize(
    "capabilities, message",
    [
        (
            [
                {
                    "step_id": "one",
                    "description": "first valid capability",
                    "depends_on": ["missing"],
                }
            ],
            "unknown steps",
        ),
        (
            [
                {
                    "step_id": "one",
                    "description": "first valid capability",
                    "depends_on": ["two"],
                },
                {
                    "step_id": "two",
                    "description": "second valid capability",
                    "depends_on": ["one"],
                },
            ],
            "cycle",
        ),
        (
            [
                {"step_id": "same", "description": "first valid capability"},
                {"step_id": "same", "description": "second valid capability"},
            ],
            "unique stable",
        ),
        (
            [
                {
                    "step_id": "one",
                    "description": "first valid capability",
                    "fulfillment": "human",
                }
            ],
            "fulfillment",
        ),
    ],
)
def test_invalid_workflow_graphs_fail_closed(capabilities, message):
    with pytest.raises(VSDPlanningError, match=message):
        plan_workflow(
            _Registry([_dynamic_tool()]),
            goal="Build a valid workflow goal",
            capabilities=capabilities,
        )


def test_agent_facing_planner_uses_tooluniverse_reference():
    registry = _Registry([_dynamic_tool()])
    tool = VSDPlanWorkflow({}, tooluniverse=registry)
    result = tool.run(
        {
            "goal": "Build a reviewed disease registry package",
            "capabilities": [_capabilities()[0]],
        }
    )
    assert result["status"] == "success"
    assert result["data"]["steps"][0]["state"] == "ready_existing"


class _FinderUniverse(_Registry):
    def __init__(self):
        tools = [_dynamic_tool()]
        tools.extend(
            {
                "name": f"FillerTool{index}",
                "type": "ExampleTool",
                "category": "examples",
                "description": f"Unrelated filler capability {index}",
                "parameter": {"type": "object", "properties": {}},
            }
            for index in range(100)
        )
        super().__init__(tools)

    def return_all_loaded_tools(self):
        return self.all_tools

    def get_tool_specification_by_names(self, names):
        return [
            self.all_tool_dict[name] for name in names if name in self.all_tool_dict
        ]

    def prepare_tool_prompts(self, tools):
        return tools


def test_keyword_finder_can_return_vsd_coverage_without_changing_default_shape():
    universe = _FinderUniverse()
    finder = ToolFinderKeyword(
        {"name": "Tool_Finder_Keyword", "configs": {"exclude_tools": []}},
        tooluniverse=universe,
    )
    default = finder.run({"description": "disease registry records", "limit": 3})
    enriched = finder.run(
        {
            "description": "disease registry records",
            "limit": 3,
            "include_capability_coverage": True,
            "capability_request": {
                "provider": "registry.example.org",
                "operation_id": "registry.search_diseases",
                "required_inputs": ["disease"],
                "output_fields": ["registry_id"],
            },
        }
    )

    assert isinstance(default, list)
    assert isinstance(enriched, dict)
    assert enriched["tools"]
    assert enriched["capability_coverage"]["classification"] == "existing_exact"
    assert enriched["capability_coverage"]["recommended_action"] == "use_existing"


def test_finder_enrichment_does_not_mutate_original_result():
    finder_result = {"query": "registry", "tools": [{"name": "Existing"}]}
    enriched = attach_capability_coverage(
        _Registry([_dynamic_tool()]),
        finder_result,
        {"description": "retrieve disease registry records"},
    )
    assert "capability_coverage" not in finder_result
    assert enriched["capability_coverage"]["registry_tool_count"] == 1


def test_keyword_finder_auto_load_preserves_runtime_vsd_tool(tmp_path):
    """Finder's full-load fallback must retain a just-published runtime tool."""

    class RuntimeVSDTool(BaseTool):
        def run(self, arguments=None, **kwargs):
            return {"status": "success", "registry_id": "REG-1"}

    universe = ToolUniverse(workspace=tmp_path / "finder-workspace")
    try:
        universe.load_tools(include_tools=["Tool_Finder_Keyword"], quiet=True)
        config = _dynamic_tool("RuntimeRegistryRecords")
        universe.register_custom_tool(
            RuntimeVSDTool,
            tool_config=config,
            instantiate=True,
        )

        result = universe.run_one_function(
            {
                "name": "Tool_Finder_Keyword",
                "arguments": {
                    "description": "disease registry records",
                    "limit": 3,
                    "include_capability_coverage": True,
                    "capability_request": {
                        "provider": "registry.example.org",
                        "operation_id": "registry.search_diseases",
                        "required_inputs": ["disease"],
                        "output_fields": ["registry_id"],
                    },
                },
            },
            use_cache=False,
        )

        assert "RuntimeRegistryRecords" in universe.all_tool_dict
        assert result["capability_coverage"]["classification"] == "existing_exact"
        assert result["capability_coverage"]["matches"][0]["name"] == (
            "RuntimeRegistryRecords"
        )
        assert universe.run_one_function(
            {"name": "RuntimeRegistryRecords", "arguments": {"disease": "ALS"}},
            use_cache=False,
        ) == {"status": "success", "registry_id": "REG-1"}
    finally:
        universe.close()
