"""Registry-first Tool Finder enrichment and workflow capability planning."""

from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from typing import Any

from .base_tool import BaseTool
from .tool_registry import register_tool
from .vsd_coverage import (
    VSDCoverageError,
    _match_tool,
    _registry_tools,
    _resolve_normalized_capability,
    normalize_capability_request,
    resolve_capability,
)

_STEP_ID_RE = re.compile(r"^[a-z][a-z0-9_]{1,63}$")
_MAX_STEPS = 20


class VSDPlanningError(VSDCoverageError):
    """Raised when a workflow preflight request is invalid."""


def _normalized_steps(capabilities: Any) -> list[dict[str, Any]]:
    if not isinstance(capabilities, list) or not 1 <= len(capabilities) <= _MAX_STEPS:
        raise VSDPlanningError("capabilities must contain 1-20 workflow steps")
    normalized: list[dict[str, Any]] = []
    known: set[str] = set()
    for index, raw_step in enumerate(capabilities):
        if not isinstance(raw_step, dict):
            raise VSDPlanningError(f"capability step {index} must be an object")
        step_id = raw_step.get("step_id")
        if (
            not isinstance(step_id, str)
            or not _STEP_ID_RE.fullmatch(step_id)
            or step_id in known
        ):
            raise VSDPlanningError("step_id values must be unique stable identifiers")
        depends_on = raw_step.get("depends_on", [])
        if (
            not isinstance(depends_on, list)
            or len(depends_on) > _MAX_STEPS
            or len(depends_on) != len(set(depends_on))
            or any(
                not isinstance(dependency, str) or not _STEP_ID_RE.fullmatch(dependency)
                for dependency in depends_on
            )
            or step_id in depends_on
        ):
            raise VSDPlanningError(
                f"depends_on for step {step_id!r} must contain unique step IDs"
            )
        optional = raw_step.get("optional", False)
        if type(optional) is not bool:
            raise VSDPlanningError(f"optional for step {step_id!r} must be boolean")
        fulfillment = raw_step.get("fulfillment", "tool")
        if fulfillment not in {"tool", "agent"}:
            raise VSDPlanningError(
                f"fulfillment for step {step_id!r} must be 'tool' or 'agent'"
            )
        capability = normalize_capability_request(
            {
                key: value
                for key, value in raw_step.items()
                if key not in {"step_id", "depends_on", "optional", "fulfillment"}
            }
        )
        normalized.append(
            {
                "step_id": step_id,
                "depends_on": list(depends_on),
                "optional": optional,
                "fulfillment": fulfillment,
                "capability": capability,
            }
        )
        known.add(step_id)
    unknown = {
        dependency
        for step in normalized
        for dependency in step["depends_on"]
        if dependency not in known
    }
    if unknown:
        raise VSDPlanningError(
            f"Workflow dependencies reference unknown steps: {sorted(unknown)!r}"
        )
    return normalized


def _topological_steps(steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id = {step["step_id"]: step for step in steps}
    order_index = {step["step_id"]: index for index, step in enumerate(steps)}
    remaining = {step["step_id"]: set(step["depends_on"]) for step in steps}
    ordered: list[dict[str, Any]] = []
    while remaining:
        ready = sorted(
            (
                step_id
                for step_id, dependencies in remaining.items()
                if not dependencies
            ),
            key=order_index.__getitem__,
        )
        if not ready:
            raise VSDPlanningError("Workflow dependencies contain a cycle")
        step_id = ready[0]
        ordered.append(by_id[step_id])
        remaining.pop(step_id)
        for dependencies in remaining.values():
            dependencies.discard(step_id)
    return ordered


def _workflow_dependency_report(
    tooluniverse: Any,
    matches: list[dict[str, Any]],
    registry: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    loaded = set(getattr(tooluniverse, "all_tool_dict", {}))
    reports: list[dict[str, Any]] = []
    for match in matches:
        if match.get("kind") != "workflow":
            continue
        config = registry.get(match["name"], {})
        required = config.get("required_tools", [])
        if not isinstance(required, list):
            required = []
        required = sorted(
            {
                name
                for name in required
                if isinstance(name, str) and 0 < len(name) <= 128
            },
            key=str.casefold,
        )[:100]
        reports.append(
            {
                "name": match["name"],
                "coverage": match["coverage"],
                "score": match["score"],
                "required_tools": required,
                "dependencies_in_registry": [
                    name for name in required if name in registry
                ],
                "dependencies_missing_from_registry": [
                    name for name in required if name not in registry
                ],
                "dependencies_loaded": [name for name in required if name in loaded],
                "can_auto_load_from_registry": all(
                    name in registry for name in required
                ),
            }
        )
    return reports


def _matching_workflows(
    request: dict[str, Any], registry: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Rank workflows separately so individual tools cannot hide a shortcut."""
    matches = [
        match
        for config in registry
        if (
            config.get("type") == "ComposeTool"
            or str(config.get("category") or "").casefold() == "compose_tools"
        )
        and (match := _match_tool(request, config)) is not None
    ]
    matches.sort(
        key=lambda match: (
            match["coverage"] != "exact",
            -match["score"],
            match["name"].casefold(),
        )
    )
    return matches


def attach_capability_coverage(
    tooluniverse: Any,
    finder_result: dict[str, Any],
    request: dict[str, Any],
    *,
    limit: int = 10,
) -> dict[str, Any]:
    """Add deterministic VSD coverage to one structured Tool Finder result."""
    if not isinstance(finder_result, dict):
        raise VSDPlanningError("finder_result must be an object")
    coverage = resolve_capability(tooluniverse, request, limit=limit)["data"]
    return {**deepcopy(finder_result), "capability_coverage": coverage}


def plan_workflow(
    tooluniverse: Any,
    *,
    goal: str,
    capabilities: list[dict[str, Any]],
    limit: int = 5,
) -> dict[str, Any]:
    """Preflight an agent-proposed workflow without executing or persisting it."""
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 20:
        raise VSDPlanningError("limit must be an integer between 1 and 20")
    normalized_goal = normalize_capability_request({"description": goal})
    ordered = _topological_steps(_normalized_steps(capabilities))
    registry_list = _registry_tools(tooluniverse)
    registry = {
        config["name"]: config
        for config in registry_list
        if isinstance(config.get("name"), str)
    }

    goal_coverage = _resolve_normalized_capability(
        normalized_goal, registry_list, limit=limit
    )["data"]
    workflow_candidates = _workflow_dependency_report(
        tooluniverse,
        _matching_workflows(normalized_goal, registry_list),
        registry,
    )
    exact_workflow_candidate = next(
        (
            workflow
            for workflow in workflow_candidates
            if workflow["coverage"] == "exact"
            and workflow["can_auto_load_from_registry"]
        ),
        None,
    )

    planned: list[dict[str, Any]] = []
    states: dict[str, str] = {}
    selected_tools: list[str] = []
    selected_matches: list[dict[str, Any]] = []
    for position, step in enumerate(ordered, start=1):
        dependency_blockers = [
            dependency
            for dependency in step["depends_on"]
            if states.get(dependency) not in {"ready_existing", "ready_agent"}
        ]
        if step["fulfillment"] == "agent":
            classification = "agent_native"
            recommended_action = "perform_after_dependencies"
            selected = None
            matches = []
            match_count = 0
            state = "blocked_by_dependencies" if dependency_blockers else "ready_agent"
            handoff = {
                "next_tool": None,
                "arguments": {},
                "execution_allowed": False,
                "reason": "Agent-native steps do not trigger external API discovery.",
            }
        else:
            coverage = _resolve_normalized_capability(
                step["capability"], registry_list, limit=limit
            )["data"]
            classification = coverage["classification"]
            recommended_action = coverage["recommended_action"]
            matches = coverage["matches"]
            match_count = coverage["match_count"]
            selected = matches[0] if matches else None
            if classification == "missing":
                state = "optional_gap" if step["optional"] else "missing"
            elif classification == "existing_partial":
                state = "needs_review"
            elif dependency_blockers:
                state = "blocked_by_dependencies"
            else:
                state = "ready_existing"
            if selected and selected["coverage"] == "exact":
                selected_tools.append(selected["name"])
                selected_matches.append(selected)
            if classification == "missing":
                handoff = {
                    "next_tool": "VSDDiscoverAPICandidates",
                    "arguments": {
                        "query": step["capability"]["description"],
                        "limit": limit,
                    },
                    "execution_allowed": False,
                }
            else:
                handoff = {
                    "next_tool": "get_tool_info",
                    "arguments": {
                        "tool_names": [match["name"] for match in matches[:limit]],
                        "detail_level": "full",
                    },
                    "execution_allowed": False,
                }
        states[step["step_id"]] = state
        planned.append(
            {
                "position": position,
                "step_id": step["step_id"],
                "depends_on": step["depends_on"],
                "optional": step["optional"],
                "fulfillment": step["fulfillment"],
                "request": deepcopy(step["capability"]),
                "state": state,
                "dependency_blockers": dependency_blockers,
                "classification": classification,
                "recommended_action": recommended_action,
                "selected_match": selected,
                "matches": matches,
                "match_count": match_count,
                "finder_handoff": handoff,
            }
        )

    required_steps = [step for step in planned if not step["optional"]]
    ready_required_steps = all(
        step["state"] in {"ready_existing", "ready_agent"} for step in required_steps
    )
    selected_are_workflow_dependencies = bool(exact_workflow_candidate) and all(
        match["kind"] == "workflow"
        or match["name"] in exact_workflow_candidate["required_tools"]
        for match in selected_matches
    )
    workflow_shortcut = (
        exact_workflow_candidate
        if ready_required_steps and selected_are_workflow_dependencies
        else None
    )
    if any(step["state"] == "missing" for step in required_steps):
        overall_action = "discover_missing_capabilities"
    elif any(
        step["state"] not in {"ready_existing", "ready_agent"}
        for step in required_steps
    ):
        overall_action = "review_partial_coverage"
    elif workflow_shortcut is not None:
        overall_action = "use_existing_workflow"
    else:
        overall_action = "compose_existing_tools"
    body = {
        "goal": normalized_goal["description"],
        "overall_action": overall_action,
        "workflow_shortcut": workflow_shortcut,
        "workflow_candidates": workflow_candidates[:limit],
        "workflow_candidate_count": len(workflow_candidates),
        "steps": planned,
        "selected_existing_tools": sorted(set(selected_tools), key=str.casefold),
        "required_gap_count": sum(
            step["state"] == "missing" for step in required_steps
        ),
        "optional_gap_count": sum(step["state"] == "optional_gap" for step in planned),
        "ready_step_count": sum(step["state"] == "ready_existing" for step in planned),
        "ready_agent_step_count": sum(
            step["state"] == "ready_agent" for step in planned
        ),
        "registry_tool_count": len(registry_list),
        "registry_sha256": goal_coverage["registry_sha256"],
        "execution_allowed": False,
        "privacy": (
            "Workflow planning is local, read-only, and not persisted or reported."
        ),
    }
    encoded = json.dumps(
        body, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    digest = hashlib.sha256(encoded).hexdigest()
    return {
        "status": "success",
        "data": {**body, "plan_id": digest[:16], "plan_sha256": digest},
    }


@register_tool("VSDPlanWorkflow")
class VSDPlanWorkflow(BaseTool):
    """Preflight an agent-proposed workflow against tools and workflows."""

    def __init__(self, tool_config, tooluniverse=None):
        super().__init__(tool_config)
        self.tooluniverse = tooluniverse

    def run(self, arguments=None, **_: Any):
        if self.tooluniverse is None:
            raise VSDPlanningError("ToolUniverse reference is required")
        if not isinstance(arguments, dict):
            raise VSDPlanningError("Tool arguments must be an object")
        return plan_workflow(
            self.tooluniverse,
            goal=arguments.get("goal"),
            capabilities=arguments.get("capabilities"),
            limit=arguments.get("limit", 5),
        )


__all__ = [
    "VSDPlanWorkflow",
    "VSDPlanningError",
    "attach_capability_coverage",
    "plan_workflow",
]
