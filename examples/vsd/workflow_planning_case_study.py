"""Exercise registry-first Finder enrichment and workflow preflight offline."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tooluniverse import ToolUniverse

HERE = Path(__file__).resolve().parent
ARTIFACTS = HERE / "artifacts"
DEFAULT_JSON = ARTIFACTS / "workflow_planning_snapshot.json"
DEFAULT_MARKDOWN = ARTIFACTS / "workflow_planning_snapshot.md"

ALS_GOAL = (
    "Build an ALS evidence workflow from rare disease genes, phenotypes, "
    "literature, clinical trials, drug labels, and quantitative microscopy"
)
ALS_CAPABILITIES = [
    {
        "step_id": "genes",
        "description": "rare disease registry genes",
        "required_inputs": ["disease"],
    },
    {
        "step_id": "phenotypes",
        "description": "rare disease registry phenotypes",
        "required_inputs": ["disease"],
    },
    {
        "step_id": "literature",
        "description": "search biomedical literature articles by disease",
        "required_inputs": ["query"],
    },
    {
        "step_id": "trials",
        "description": "search clinical trials by disease condition",
        "required_inputs": ["condition"],
        "depends_on": ["genes", "phenotypes"],
    },
    {
        "step_id": "drug_label",
        "description": "retrieve FDA drug label by set identifier",
        "provider": "FDA",
        "required_inputs": ["set_id"],
    },
    {
        "step_id": "microscopy_calibration",
        "description": "quantum microscope calibration waveform optimizer",
        "depends_on": ["genes"],
    },
    {
        "step_id": "synthesis",
        "fulfillment": "agent",
        "description": (
            "combine ALS genes phenotypes literature clinical trials drug labels "
            "and quantitative microscopy evidence"
        ),
        "depends_on": [
            "genes",
            "phenotypes",
            "literature",
            "trials",
            "drug_label",
            "microscopy_calibration",
        ],
    },
]
DRUG_WORKFLOW_GOAL = "complete disease target compound ADMET literature workflow"
EXPECTED_ASSERTIONS = {
    "dependency_order_is_valid",
    "drug_label_reuses_exact_tools",
    "finder_and_planner_share_registry_digest",
    "finder_returns_coverage_with_ranked_tools",
    "known_steps_never_route_to_discovery",
    "missing_dependency_blocks_synthesis",
    "only_real_gap_routes_to_discovery",
    "planner_does_not_load_registry_tools",
    "planner_is_deterministic",
    "planner_is_local_non_executable",
    "required_gap_controls_overall_action",
    "whole_workflow_shortcut_has_complete_dependencies",
}


def _digest(value: Any) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _run(tooluniverse: ToolUniverse, name: str, arguments: dict[str, Any]) -> Any:
    result = tooluniverse.run_one_function(
        {"name": name, "arguments": arguments}, use_cache=False
    )
    if isinstance(result, dict) and result.get("status") == "error":
        raise RuntimeError(f"{name} failed: {result!r}")
    return result


def _step_map(plan: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {step["step_id"]: step for step in plan["steps"]}


def run_case() -> dict[str, Any]:
    tooluniverse = ToolUniverse()
    try:
        tooluniverse.load_tools(
            include_tools=["VSDPlanWorkflow", "Tool_Finder_Keyword"], quiet=True
        )
        initially_loaded = sorted(tooluniverse.all_tool_dict)
        als_response = _run(
            tooluniverse,
            "VSDPlanWorkflow",
            {"goal": ALS_GOAL, "capabilities": ALS_CAPABILITIES, "limit": 5},
        )
        als_plan = als_response["data"]
        loaded_after_planning = sorted(tooluniverse.all_tool_dict)
        repeated_plan = _run(
            tooluniverse,
            "VSDPlanWorkflow",
            {"goal": ALS_GOAL, "capabilities": ALS_CAPABILITIES, "limit": 5},
        )["data"]
        workflow_plan = _run(
            tooluniverse,
            "VSDPlanWorkflow",
            {
                "goal": DRUG_WORKFLOW_GOAL,
                "capabilities": [
                    {"step_id": "pipeline", "description": DRUG_WORKFLOW_GOAL}
                ],
                "limit": 5,
            },
        )["data"]
        finder = _run(
            tooluniverse,
            "Tool_Finder_Keyword",
            {
                "description": "FDA drug label by set identifier",
                "limit": 5,
                "include_capability_coverage": True,
                "capability_request": {
                    "provider": "FDA",
                    "required_inputs": ["set_id"],
                },
            },
        )
    finally:
        tooluniverse.close()

    steps = _step_map(als_plan)
    gap = steps["microscopy_calibration"]
    known_steps = [
        step for step in als_plan["steps"] if step["step_id"] != gap["step_id"]
    ]
    positions = {step["step_id"]: step["position"] for step in als_plan["steps"]}
    dependency_order_valid = all(
        positions[dependency] < step["position"]
        for step in als_plan["steps"]
        for dependency in step["depends_on"]
    )
    shortcut = workflow_plan["workflow_shortcut"]
    assertions = {
        "planner_is_local_non_executable": (
            als_plan["execution_allowed"] is False
            and "not persisted or reported" in als_plan["privacy"]
        ),
        "planner_does_not_load_registry_tools": (
            initially_loaded == loaded_after_planning
            and set(initially_loaded) == {"Tool_Finder_Keyword", "VSDPlanWorkflow"}
        ),
        "planner_is_deterministic": (
            als_plan["plan_id"] == repeated_plan["plan_id"]
            and als_plan["plan_sha256"] == repeated_plan["plan_sha256"]
        ),
        "dependency_order_is_valid": dependency_order_valid,
        "drug_label_reuses_exact_tools": (
            steps["drug_label"]["classification"] == "existing_exact"
            and steps["drug_label"]["state"] == "ready_existing"
            and steps["drug_label"]["selected_match"]["coverage"] == "exact"
        ),
        "only_real_gap_routes_to_discovery": (
            gap["classification"] == "missing"
            and gap["finder_handoff"]["next_tool"] == "VSDDiscoverAPICandidates"
            and gap["finder_handoff"]["execution_allowed"] is False
        ),
        "known_steps_never_route_to_discovery": all(
            step["finder_handoff"]["next_tool"] != "VSDDiscoverAPICandidates"
            for step in known_steps
        ),
        "missing_dependency_blocks_synthesis": (
            "microscopy_calibration" in steps["synthesis"]["dependency_blockers"]
        ),
        "required_gap_controls_overall_action": (
            als_plan["required_gap_count"] == 1
            and als_plan["overall_action"] == "discover_missing_capabilities"
        ),
        "whole_workflow_shortcut_has_complete_dependencies": (
            workflow_plan["overall_action"] == "use_existing_workflow"
            and shortcut["name"] == "ComprehensiveDrugDiscoveryPipeline"
            and shortcut["can_auto_load_from_registry"] is True
            and not shortcut["dependencies_missing_from_registry"]
        ),
        "finder_returns_coverage_with_ranked_tools": (
            isinstance(finder.get("tools"), list)
            and bool(finder["tools"])
            and finder["capability_coverage"]["classification"] == "existing_exact"
        ),
        "finder_and_planner_share_registry_digest": (
            finder["capability_coverage"]["registry_sha256"]
            == als_plan["registry_sha256"]
        ),
    }
    snapshot = {
        "title": "Registry-First ALS Workflow Planning Case Study",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "question": (
            "Can an agent preflight a complicated ALS research workflow, reuse "
            "existing tools and workflows, and isolate only the truly missing capability?"
        ),
        "answer": (
            "Yes. The planner retained exact and partial registry coverage for review, "
            "sent only the microscopy-calibration gap to non-executable discovery, and "
            "recognized an existing drug-discovery workflow with all dependencies present."
        ),
        "execution_boundary": (
            "This study plans and inspects only. It does not execute scientific tools, "
            "download data, persist demand, or create API candidates."
        ),
        "initially_loaded_tools": initially_loaded,
        "loaded_after_planning": loaded_after_planning,
        "als_plan": als_plan,
        "existing_workflow_plan": workflow_plan,
        "finder_integration": finder,
        "end_to_end_assertions": assertions,
    }
    snapshot["audit_sha256"] = _digest(
        {
            "initially_loaded_tools": snapshot["initially_loaded_tools"],
            "loaded_after_planning": snapshot["loaded_after_planning"],
            "als_plan": snapshot["als_plan"],
            "existing_workflow_plan": snapshot["existing_workflow_plan"],
            "finder_integration": snapshot["finder_integration"],
            "end_to_end_assertions": snapshot["end_to_end_assertions"],
        }
    )
    validate_snapshot(snapshot)
    return snapshot


def validate_snapshot(snapshot: dict[str, Any]) -> None:
    assertions = snapshot.get("end_to_end_assertions")
    if not isinstance(assertions, dict) or set(assertions) != EXPECTED_ASSERTIONS:
        raise ValueError("Snapshot does not contain the complete assertion set")
    if not all(assertions.values()):
        failed = sorted(name for name, passed in assertions.items() if not passed)
        raise ValueError(f"End-to-end assertions failed: {failed!r}")
    expected = _digest(
        {
            "initially_loaded_tools": snapshot["initially_loaded_tools"],
            "loaded_after_planning": snapshot["loaded_after_planning"],
            "als_plan": snapshot["als_plan"],
            "existing_workflow_plan": snapshot["existing_workflow_plan"],
            "finder_integration": snapshot["finder_integration"],
            "end_to_end_assertions": snapshot["end_to_end_assertions"],
        }
    )
    if snapshot.get("audit_sha256") != expected:
        raise ValueError("Snapshot audit digest does not match its content")


def _markdown(snapshot: dict[str, Any]) -> str:
    plan = snapshot["als_plan"]
    shortcut = snapshot["existing_workflow_plan"]["workflow_shortcut"]
    coverage = snapshot["finder_integration"]["capability_coverage"]
    lines = [
        "# Registry-First ALS Workflow Planning Case Study",
        "",
        f"**Generated:** {snapshot['generated_at']}",
        "",
        "## Decision Question",
        "",
        snapshot["question"],
        "",
        f"**Result:** {snapshot['answer']}",
        "",
        "## ALS Workflow Preflight",
        "",
        f"The planner scanned {plan['registry_tool_count']:,} registered specifications "
        "without loading those tools. It returned the following dependency-ordered plan:",
        "",
        "| # | Step | Coverage | State | Best existing match | Next interface |",
        "| ---: | --- | --- | --- | --- | --- |",
    ]
    for step in plan["steps"]:
        selected = step["selected_match"]
        selected_name = selected["name"] if selected else "None"
        lines.append(
            f"| {step['position']} | `{step['step_id']}` | "
            f"{step['classification']} | {step['state']} | `{selected_name}` | "
            f"`{step['finder_handoff']['next_tool']}` |"
        )
    lines.extend(
        [
            "",
            "The exact FDA-label capability is ready to reuse. Registry genes, "
            "phenotypes, literature, and trials have plausible existing coverage "
            "that must be inspected with `get_tool_info`. The agent-native synthesis "
            "waits for its dependencies and cannot enter API discovery. Only the "
            "intentionally absent microscopy-calibration "
            "step receives a `VSDDiscoverAPICandidates` handoff, and that handoff is "
            "still non-executable.",
            "",
            "## Existing Workflow Shortcut",
            "",
            f"A separate whole-goal preflight selected `{shortcut['name']}`. All "
            f"{len(shortcut['required_tools'])} named dependencies are present in the "
            "registry, so the planner recommends loading that workflow rather than "
            "rebuilding it.",
            "",
            "| Dependency | Registry state |",
            "| --- | --- |",
        ]
    )
    lines.extend(
        f"| `{dependency}` | present |" for dependency in shortcut["required_tools"]
    )
    lines.extend(
        [
            "",
            "## Tool Finder Integration",
            "",
            "The existing keyword finder was called with capability coverage enabled. "
            f"It returned {len(snapshot['finder_integration']['tools'])} ranked tools "
            f"and classified the FDA-label request as `{coverage['classification']}` "
            f"with action `{coverage['recommended_action']}`. The Finder and workflow "
            "planner reported the same registry SHA-256, proving they evaluated the "
            "same local registry snapshot.",
            "",
            "## End-to-End Assertions",
            "",
            "| Assertion | Result |",
            "| --- | --- |",
        ]
    )
    lines.extend(
        f"| `{name}` | {'PASS' if passed else 'FAIL'} |"
        for name, passed in sorted(snapshot["end_to_end_assertions"].items())
    )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            snapshot["execution_boundary"],
            "",
            f"**Audit SHA-256:** `{snapshot['audit_sha256']}`",
            "",
        ]
    )
    return "\n".join(lines)


def write_artifacts(snapshot: dict[str, Any]) -> None:
    validate_snapshot(snapshot)
    DEFAULT_JSON.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_JSON.write_text(
        json.dumps(snapshot, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    DEFAULT_MARKDOWN.write_text(_markdown(snapshot), encoding="utf-8")


def main() -> int:
    snapshot = run_case()
    write_artifacts(snapshot)
    print(json.dumps({"status": "passed", "audit_sha256": snapshot["audit_sha256"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
