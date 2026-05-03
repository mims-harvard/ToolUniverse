"""
HarvestAutoRegistrar compose script.

Coordinates the GenericHarvestTool, HarvestCandidateTesterTool, and
VerifiedSourceRegisterTool to discover, validate, and register new
DynamicREST tools. Designed to keep all orchestration logic inside the
ComposeTool framework so agents can call a single tool to go from query
to a runnable verified-source entry.
"""

from __future__ import annotations

import json
import re
import uuid
from typing import Any, Dict, List, Optional, Tuple


class _ComposeError(Exception):
    """Internal marker so we can bubble failures cleanly."""


def _as_dict(result: Any) -> Dict[str, Any]:
    if isinstance(result, dict):
        return result
    if isinstance(result, str):
        try:
            decoded = json.loads(result)
            if isinstance(decoded, dict):
                return decoded
        except json.JSONDecodeError:
            pass
    return {"raw_result": result}


def _emit(emit_event, event_type: str, data: Dict[str, Any]) -> None:
    if emit_event:
        emit_event(event_type, data)


def _generate_tool_name(base: Optional[str], suffix: str | None = None) -> str:
    if base:
        slug = re.sub(r"[^a-zA-Z0-9]+", "_", base).strip("_").lower()
        if not slug:
            slug = "vsd_auto"
    else:
        slug = "vsd_auto"
    suffix = suffix or uuid.uuid4().hex[:6]
    return f"{slug}_{suffix}"


def _select_candidates(
    arguments: Dict[str, Any],
) -> Tuple[Optional[str], Dict[str, Any]]:
    # Backwards compatibility: allow top-level query/limit keys
    harvest_overrides = dict(arguments.get("harvest", {}) or {})
    query = (arguments.get("query") or harvest_overrides.get("query") or "").strip()

    if query:
        harvest_overrides.setdefault("query", query)

    limit = arguments.get("limit")
    if limit is None:
        limit = harvest_overrides.get("limit", 5)
    harvest_overrides["limit"] = max(1, min(int(limit or 5), 50))

    return query, harvest_overrides


def compose(
    arguments: Dict[str, Any],
    tooluniverse,
    call_tool,
    stream_callback=None,
    emit_event=None,
    memory_manager=None,
) -> Dict[str, Any]:
    """
    Discover, test, and register a new verified-source tool from harvest results.
    """

    args = dict(arguments or {})
    manual_candidates = args.get("candidates")

    # Prepare harvest step arguments (even if we skip calling the tool)
    _, harvest_args = _select_candidates(args)

    results: Dict[str, Any] = {
        "ok": False,
        "attempts": [],
        "registered_tool_name": None,
        "run_result": None,
    }

    # Step 1: gather candidates
    if manual_candidates:
        candidates = list(manual_candidates)
        harvest_summary = {
            "ok": True,
            "source": "manual",
            "count": len(candidates),
            "query": harvest_args.get("query", ""),
        }
    else:
        harvest_response = call_tool("GenericHarvestTool", harvest_args)
        harvest_summary = _as_dict(harvest_response)
        candidates = list(harvest_summary.get("candidates") or [])

    results["harvest"] = harvest_summary
    _emit(emit_event, "harvest_completed", harvest_summary)

    if not candidates:
        results["error"] = "No candidates returned from harvest."
        return results

    skip_tests = bool(args.get("skip_tests"))
    force_register = bool(args.get("force_register") or args.get("force"))
    tester_overrides = dict(args.get("tester", {}) or {})
    register_overrides = dict(args.get("register", {}) or {})
    desired_tool_name = args.get("tool_name")
    auto_run = bool(args.get("auto_run"))
    tool_arguments = args.get("tool_arguments") or {}

    for index, candidate in enumerate(candidates):
        attempt_record: Dict[str, Any] = {
            "candidate_index": index,
            "candidate": candidate,
        }
        tester_result = {"skipped": skip_tests}

        if not skip_tests:
            tester_payload = dict(tester_overrides)
            tester_payload.setdefault("candidate", candidate)
            tester_response = call_tool("HarvestCandidateTesterTool", tester_payload)
            tester_result = _as_dict(tester_response)
            attempt_record["tester"] = tester_result
            if not tester_result.get("ok") and not force_register:
                attempt_record["status"] = "tester_failed"
                results["attempts"].append(attempt_record)
                continue

        register_payload = dict(register_overrides)
        register_payload.setdefault("candidate", candidate)
        register_payload.setdefault("force", force_register)

        tool_name = register_payload.get("tool_name") or desired_tool_name
        if not tool_name:
            host = (candidate.get("host") or candidate.get("name") or "").strip()
            tool_name = _generate_tool_name(host, suffix=f"cand{index + 1}")
        register_payload["tool_name"] = tool_name

        register_response = call_tool("VerifiedSourceRegisterTool", register_payload)
        register_result = _as_dict(register_response)
        attempt_record["register"] = register_result

        if not register_result.get("registered"):
            attempt_record["status"] = "registration_failed"
            results["attempts"].append(attempt_record)
            continue

        # Registration succeeded
        registered_name = register_result.get("name") or tool_name
        results["ok"] = True
        results["registered_tool_name"] = registered_name
        results["registration"] = register_result
        attempt_record["status"] = "registered"
        results["attempts"].append(attempt_record)
        _emit(emit_event, "registration_success", register_result)

        if auto_run:
            try:
                run_payload = {
                    "name": registered_name,
                    "arguments": tool_arguments
                    if isinstance(tool_arguments, dict)
                    else {},
                }
                run_result = tooluniverse.run_one_function(run_payload)
                results["run_result"] = run_result
            except Exception as exc:  # pragma: no cover - defensive
                results["run_error"] = str(exc)
        return results

    results["error"] = "All candidates failed testing or registration."
    _emit(emit_event, "registration_failed", {"attempts": results["attempts"]})
    return results


__all__ = ["compose"]
