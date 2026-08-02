"""Run parameterized biomedical evaluations of governed VSD registry growth."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import urlsplit

import tooluniverse.vsd_discovery as vsd_discovery
import tooluniverse.vsd_dynamic_rest as vsd_dynamic_rest
from tooluniverse import ToolUniverse
from tooluniverse.vsd_coverage import _registry_tools
from tooluniverse.vsd_dynamic_rest import _provider_request
from tooluniverse.vsd_openapi import inspect_openapi_document
from tooluniverse.vsd_planning import plan_workflow
from tooluniverse.vsd_promotion import (
    VSDPromotionError,
    approve_draft,
    create_catalog_openapi_draft,
    create_reviewed_catalog_openapi_draft,
    load_published_tools,
    publish_draft,
    verify_draft,
)
from tooluniverse.vsd_tool import _safe_get_json

HERE = Path(__file__).resolve().parent
STUDIES = HERE / "biomedical_studies"
SCENARIOS = STUDIES / "scenarios"
FIXTURES = STUDIES / "fixtures"
ARTIFACTS = HERE / "artifacts"
DEFAULT_JSON = ARTIFACTS / "biomedical_evaluation_portfolio.json"
DEFAULT_MARKDOWN = ARTIFACTS / "biomedical_evaluation_portfolio.md"

_CASE_ID_RE = re.compile(r"^[a-z][a-z0-9_]{2,63}$")
_TOOL_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{2,44}$")
_REQUIRED_SCENARIO_FIELDS = {
    "case_id",
    "title",
    "research_question",
    "decision_context",
    "catalog_query",
    "catalog_record_id",
    "service_endpoint",
    "specification_fixture",
    "response_fixture",
    "operation_id",
    "promotion_mode",
    "tool_name",
    "tool_description",
    "include_parameters",
    "fixed_query",
    "review_note",
    "response_schema",
    "workflow_capability",
    "verification_cases",
    "runtime_arguments",
    "observations",
    "reused_tools",
    "without_vsd",
    "with_vsd",
    "limitations",
    "references",
}


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _bounded_fixture(name: Any) -> Path:
    if not isinstance(name, str) or Path(name).name != name or not name.endswith(
        ".json"
    ):
        raise ValueError("Scenario fixture names must be local JSON filenames")
    path = (FIXTURES / name).resolve()
    if path.parent != FIXTURES.resolve() or not path.is_file():
        raise ValueError(f"Scenario fixture does not exist: {name!r}")
    return path


def validate_scenario(value: Any) -> dict[str, Any]:
    """Validate one data-only evaluation scenario before any network activity."""
    if not isinstance(value, dict) or set(value) != _REQUIRED_SCENARIO_FIELDS:
        raise ValueError("Scenario structure is invalid")
    case_id = value["case_id"]
    if not isinstance(case_id, str) or not _CASE_ID_RE.fullmatch(case_id):
        raise ValueError("Scenario case_id is invalid")
    if not isinstance(value["tool_name"], str) or not _TOOL_NAME_RE.fullmatch(
        value["tool_name"]
    ):
        raise ValueError("Scenario tool_name is invalid")
    for field in (
        "title",
        "research_question",
        "decision_context",
        "catalog_query",
        "catalog_record_id",
        "service_endpoint",
        "operation_id",
        "tool_description",
        "review_note",
    ):
        text = value[field]
        if not isinstance(text, str) or not text.strip() or len(text) > 2000:
            raise ValueError(f"Scenario {field} is invalid")
    endpoint = urlsplit(value["service_endpoint"])
    if (
        endpoint.scheme != "https"
        or not endpoint.hostname
        or endpoint.username
        or endpoint.password
        or endpoint.query
        or endpoint.fragment
    ):
        raise ValueError("Scenario service_endpoint must be canonical HTTPS")
    _bounded_fixture(value["specification_fixture"])
    _bounded_fixture(value["response_fixture"])
    if value["promotion_mode"] not in {"strict", "reviewed_response"}:
        raise ValueError("Scenario promotion_mode is invalid")
    if not isinstance(value["include_parameters"], list) or any(
        not isinstance(item, str) for item in value["include_parameters"]
    ):
        raise ValueError("Scenario include_parameters is invalid")
    if not isinstance(value["fixed_query"], dict):
        raise ValueError("Scenario fixed_query is invalid")
    response_schema = value["response_schema"]
    if value["promotion_mode"] == "strict" and response_schema is not None:
        raise ValueError("Strict scenarios obtain their response schema from OpenAPI")
    if value["promotion_mode"] == "reviewed_response" and not isinstance(
        response_schema, dict
    ):
        raise ValueError("Reviewed-response scenarios require a response schema")
    capability = value["workflow_capability"]
    if (
        not isinstance(capability, dict)
        or set(capability)
        != {"step_id", "description", "required_inputs", "output_fields"}
        or not _CASE_ID_RE.fullmatch(str(capability["step_id"]))
        or not isinstance(capability["description"], str)
        or not isinstance(capability["required_inputs"], list)
        or not isinstance(capability["output_fields"], list)
    ):
        raise ValueError("Scenario workflow_capability is invalid")
    cases = value["verification_cases"]
    if not isinstance(cases, list) or not 3 <= len(cases) <= 20:
        raise ValueError("Scenario requires 3-20 verification cases")
    if any(
        not isinstance(case, dict)
        or set(case) != {"arguments", "expect"}
        or not isinstance(case["arguments"], dict)
        or not isinstance(case["expect"], dict)
        for case in cases
    ):
        raise ValueError("Scenario verification cases are invalid")
    if not isinstance(value["runtime_arguments"], dict):
        raise ValueError("Scenario runtime_arguments is invalid")
    responses = _json(_bounded_fixture(value["response_fixture"]))
    if (
        not isinstance(responses, list)
        or len(responses) < len(cases)
        or any(
            not isinstance(item, dict)
            or set(item) != {"arguments", "payload"}
            or not isinstance(item["arguments"], dict)
            for item in responses
        )
    ):
        raise ValueError("Scenario replay responses are invalid")
    available = {_digest(item["arguments"]) for item in responses}
    required = {_digest(case["arguments"]) for case in cases}
    required.add(_digest(value["runtime_arguments"]))
    if not required <= available:
        raise ValueError("Scenario replay responses do not cover every execution")
    for field in (
        "observations",
        "reused_tools",
        "limitations",
        "references",
    ):
        if not isinstance(value[field], list) or not value[field]:
            raise ValueError(f"Scenario {field} must be a non-empty list")
    if any(
        not isinstance(item, dict)
        or set(item) != {"label", "pointer"}
        or not isinstance(item["label"], str)
        or not item["label"].strip()
        or not isinstance(item["pointer"], str)
        or (item["pointer"] and not item["pointer"].startswith("/"))
        for item in value["observations"]
    ):
        raise ValueError("Scenario observations are invalid")
    if any(
        not isinstance(item, dict)
        or set(item) != {"name", "role"}
        or not isinstance(item["name"], str)
        or not _TOOL_NAME_RE.fullmatch(item["name"])
        or not isinstance(item["role"], str)
        or not item["role"].strip()
        for item in value["reused_tools"]
    ):
        raise ValueError("Scenario reused_tools entries are invalid")
    if any(
        not isinstance(item, str) or not item.strip() or len(item) > 1000
        for item in value["limitations"]
    ):
        raise ValueError("Scenario limitations are invalid")
    if any(
        not isinstance(item, dict)
        or set(item) != {"title", "url"}
        or not isinstance(item["title"], str)
        or not item["title"].strip()
        or not isinstance(item["url"], str)
        or urlsplit(item["url"]).scheme != "https"
        or not urlsplit(item["url"]).hostname
        for item in value["references"]
    ):
        raise ValueError("Scenario references are invalid")
    for field in ("without_vsd", "with_vsd"):
        if (
            not isinstance(value[field], dict)
            or set(value[field]) != {"summary"}
            or not isinstance(value[field]["summary"], str)
            or not value[field]["summary"].strip()
        ):
            raise ValueError(f"Scenario {field} must contain one summary")
    return json.loads(json.dumps(value))


def load_scenarios() -> list[dict[str, Any]]:
    scenarios = [validate_scenario(_json(path)) for path in sorted(SCENARIOS.glob("*.json"))]
    if len(scenarios) != 5 or len({item["case_id"] for item in scenarios}) != 5:
        raise ValueError("The portfolio must contain five unique scenarios")
    return scenarios


def _tool_data(
    universe: ToolUniverse, tool_name: str, arguments: dict[str, Any]
) -> dict[str, Any]:
    result = universe.run_one_function(
        {"name": tool_name, "arguments": arguments}, use_cache=False
    )
    if not isinstance(result, dict) or result.get("status") != "success":
        raise RuntimeError(f"{tool_name} failed")
    data = result.get("data")
    if not isinstance(data, dict):
        raise RuntimeError(f"{tool_name} returned an invalid envelope")
    return data


def _request_metadata(url: str, payload: Any) -> dict[str, Any]:
    return {
        "url": url,
        "status_code": 200,
        "content_type": "application/json",
        "response_bytes": len(_canonical(payload)),
        "peer_ip": "93.184.216.34",
        "redirects": 0,
    }


def _same_service(left: str, right: str) -> bool:
    first = urlsplit(left)
    second = urlsplit(right)
    return (
        first.scheme,
        (first.hostname or "").casefold().rstrip("."),
        first.port,
        (first.path or "/").rstrip("/") or "/",
    ) == (
        second.scheme,
        (second.hostname or "").casefold().rstrip("."),
        second.port,
        (second.path or "/").rstrip("/") or "/",
    )


@contextmanager
def _replay_catalog(specification: dict[str, Any]) -> Iterator[None]:
    original = vsd_discovery._safe_get_json
    payload = {"total": 1, "hits": [specification]}

    def fetch(url, params=None, **kwargs):
        del params, kwargs
        return payload, _request_metadata(url, payload)

    vsd_discovery._safe_get_json = fetch
    try:
        yield
    finally:
        vsd_discovery._safe_get_json = original


@contextmanager
def _allowed_service_host(endpoint: str) -> Iterator[None]:
    host = (urlsplit(endpoint).hostname or "").casefold().rstrip(".")
    previous = os.environ.get("TOOLUNIVERSE_VSD_ALLOWED_HOSTS")
    configured = {item.strip() for item in (previous or "").split(",") if item.strip()}
    configured.add(host)
    os.environ["TOOLUNIVERSE_VSD_ALLOWED_HOSTS"] = ",".join(sorted(configured))
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop("TOOLUNIVERSE_VSD_ALLOWED_HOSTS", None)
        else:
            os.environ["TOOLUNIVERSE_VSD_ALLOWED_HOSTS"] = previous


def _discovery(
    universe: ToolUniverse,
    scenario: dict[str, Any],
    specification: dict[str, Any],
    *,
    mode: str,
) -> dict[str, Any]:
    arguments = {
        "query": scenario["catalog_query"],
        "providers": ["smartapi"],
        "exclude_registered": True,
        "limit": 10,
    }
    if mode == "replay":
        with _replay_catalog(specification):
            return _tool_data(universe, "VSDDiscoverAPICandidates", arguments)
    return _tool_data(universe, "VSDDiscoverAPICandidates", arguments)


def _select_catalog_candidate(
    discovery: dict[str, Any], scenario: dict[str, Any]
) -> dict[str, Any]:
    matches = [
        item
        for item in discovery.get("candidates", [])
        if item.get("catalog_record_id") == scenario["catalog_record_id"]
        and _same_service(item.get("api_endpoint", ""), scenario["service_endpoint"])
    ]
    if len(matches) != 1:
        raise RuntimeError("Discovery did not return the exact scenario catalog record")
    return matches[0]


def _inspect(
    catalog_candidate: dict[str, Any],
    scenario: dict[str, Any],
    workspace: Path,
    *,
    mode: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if mode == "replay":
        path = _bounded_fixture(scenario["specification_fixture"])
        transport = {
            "mode": "replay",
            "source": "checked provider-shaped OpenAPI fixture",
        }
    else:
        payload, request = _safe_get_json(
            catalog_candidate["specification_url"],
            max_response_bytes=10_000_000,
        )
        path = workspace / "inspected-openapi.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
            encoding="utf-8",
        )
        transport = {
            "mode": "live",
            "source": "SmartAPI metadata endpoint",
            "http_status": request["status_code"],
            "payload_sha256": hashlib.sha256(_canonical(payload)).hexdigest(),
        }
    report = inspect_openapi_document(path)
    matches = [
        item
        for item in report["candidates"]
        if item["operation_id"] == scenario["operation_id"]
    ]
    if len(matches) != 1:
        raise RuntimeError("OpenAPI inspection did not find the exact operation")
    return matches[0], {
        **transport,
        "source_document_sha256": report["source_document_sha256"],
        "candidate_count": report["candidate_count"],
        "promotable_count": report["promotable_count"],
    }


def _workflow(
    universe: ToolUniverse,
    scenario: dict[str, Any],
    operation: dict[str, Any],
) -> dict[str, Any]:
    capability = scenario["workflow_capability"]
    endpoint = operation["server_url"] + "/" + operation["path"].lstrip("/")
    return plan_workflow(
        universe,
        goal=scenario["research_question"],
        capabilities=[
            {
                **capability,
                "provider": urlsplit(endpoint).hostname,
                "method": "GET",
                "endpoint": endpoint,
                "operation_id": f"openapi.{operation['candidate_id']}",
            },
            {
                "step_id": "evidence_synthesis",
                "description": scenario["decision_context"],
                "fulfillment": "agent",
                "depends_on": [capability["step_id"]],
            },
        ],
        limit=5,
    )["data"]


def _step(plan: dict[str, Any], step_id: str) -> dict[str, Any]:
    return next(item for item in plan["steps"] if item["step_id"] == step_id)


def _registry_evidence(
    universe: ToolUniverse, scenario: dict[str, Any]
) -> list[dict[str, Any]]:
    registry = {
        item.get("name"): item
        for item in _registry_tools(universe)
        if isinstance(item, dict) and isinstance(item.get("name"), str)
    }
    evidence = []
    for requested in scenario["reused_tools"]:
        if not isinstance(requested, dict) or set(requested) != {"name", "role"}:
            raise ValueError("Scenario reused_tools entries are invalid")
        config = registry.get(requested["name"])
        if config is None:
            raise RuntimeError(f"Existing tool is absent: {requested['name']}")
        evidence.append(
            {
                "name": requested["name"],
                "role": requested["role"],
                "present": True,
                "config_sha256": _digest(config),
            }
        )
    return evidence


def _draft(
    scenario: dict[str, Any],
    catalog_candidate: dict[str, Any],
    operation: dict[str, Any],
    workspace: Path,
) -> dict[str, Any]:
    common = {
        "catalog_candidate": catalog_candidate,
        "operation_candidate": operation,
        "tool_name": scenario["tool_name"],
        "description": scenario["tool_description"],
        "review_note": scenario["review_note"],
        "include_parameters": scenario["include_parameters"],
        "fixed_query": scenario["fixed_query"],
        "workspace": workspace,
    }
    if scenario["promotion_mode"] == "strict":
        return create_catalog_openapi_draft(**common)
    return create_reviewed_catalog_openapi_draft(
        **common,
        response_schema=scenario["response_schema"],
        resolved_blockers=["json_response_missing"],
    )


def _replay_exchange(
    config: dict[str, Any], scenario: dict[str, Any]
):
    responses = _json(_bounded_fixture(scenario["response_fixture"]))
    requests: dict[tuple[str, str], Any] = {}
    for item in responses:
        endpoint, query = _provider_request(config, item["arguments"])
        requests[(endpoint, _digest(query))] = item["payload"]

    def fetch(url, params, *, timeout, **kwargs):
        del timeout, kwargs
        key = (url, _digest(params))
        if key not in requests:
            raise RuntimeError("Replay transport received an unreviewed request")
        payload = requests[key]
        return payload, _request_metadata(url, payload)

    return fetch


@contextmanager
def _runtime_transport(
    config: dict[str, Any], scenario: dict[str, Any], *, mode: str
) -> Iterator[None]:
    original = vsd_dynamic_rest._safe_get_json
    if mode == "replay":
        vsd_dynamic_rest._safe_get_json = _replay_exchange(config, scenario)
    try:
        yield
    finally:
        vsd_dynamic_rest._safe_get_json = original


def _pointer(value: Any, pointer: str) -> Any:
    if not isinstance(pointer, str) or (pointer and not pointer.startswith("/")):
        raise ValueError("Observation pointer is invalid")
    current = value
    for raw in pointer.split("/")[1:] if pointer else []:
        token = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(current, dict) and token in current:
            current = current[token]
        elif isinstance(current, list) and token.isdigit() and int(token) < len(current):
            current = current[int(token)]
        else:
            return None
    return current


def _runtime_summary(
    data: dict[str, Any], scenario: dict[str, Any]
) -> dict[str, Any]:
    result = data["result"]
    observations = []
    for observation in scenario["observations"]:
        if not isinstance(observation, dict) or set(observation) != {
            "label",
            "pointer",
        }:
            raise ValueError("Scenario observation is invalid")
        observations.append(
            {
                "label": observation["label"],
                "pointer": observation["pointer"],
                "value": _pointer(result, observation["pointer"]),
            }
        )
    return {
        "result_type": "array" if isinstance(result, list) else "object",
        "item_count": len(result) if isinstance(result, list) else None,
        "top_level_fields": sorted(result) if isinstance(result, dict) else [],
        "payload_sha256": data["provenance"]["payload_sha256"],
        "provider": data["provenance"]["provider"],
        "observations": observations,
    }


def _run_once(
    scenario: dict[str, Any], workspace: Path, *, mode: str
) -> dict[str, Any]:
    specification = _json(_bounded_fixture(scenario["specification_fixture"]))
    initial = ToolUniverse()
    try:
        initial.load_tools(include_tools=["VSDDiscoverAPICandidates"], quiet=True)
        reused = _registry_evidence(initial, scenario)
        discovery = _discovery(initial, scenario, specification, mode=mode)
        catalog_candidate = _select_catalog_candidate(discovery, scenario)
        operation, inspection = _inspect(
            catalog_candidate, scenario, workspace, mode=mode
        )
        initial_plan = _workflow(initial, scenario, operation)
    finally:
        initial.close()

    promotion_workspace = workspace / "promotion"
    draft = _draft(
        scenario,
        catalog_candidate,
        operation,
        promotion_workspace,
    )
    early_publication_blocked = False
    try:
        publish_draft(draft["draft_id"], workspace=promotion_workspace)
    except VSDPromotionError:
        early_publication_blocked = True

    with _allowed_service_host(scenario["service_endpoint"]), _runtime_transport(
        draft["config"], scenario, mode=mode
    ):
        evidence = verify_draft(
            draft["draft_id"],
            scenario["verification_cases"],
            workspace=promotion_workspace,
        )
        approval = approve_draft(
            draft["draft_id"],
            reviewed_by="Biomedical Evaluation Reviewer",
            decision_note=(
                "Approved after the exact catalog binding and all representative "
                "verification cases passed."
            ),
            workspace=promotion_workspace,
        )
        publication = publish_draft(
            draft["draft_id"], workspace=promotion_workspace
        )
        runtime = ToolUniverse()
        runtime.load_tools(include_tools=["VSDDiscoverAPICandidates"], quiet=True)
        try:
            absent_before_load = scenario["tool_name"] not in runtime.all_tool_dict
            loaded = load_published_tools(runtime, workspace=promotion_workspace)
            result = _tool_data(
                runtime, scenario["tool_name"], scenario["runtime_arguments"]
            )
            final_plan = _workflow(runtime, scenario, operation)
        finally:
            runtime.close()

    step_id = scenario["workflow_capability"]["step_id"]
    initial_step = _step(initial_plan, step_id)
    final_step = _step(final_plan, step_id)
    hash_chain = {
        "catalog_candidate_sha256": catalog_candidate["candidate_sha256"],
        "source_document_sha256": operation["source_document_sha256"],
        "operation_candidate_sha256": operation["candidate_sha256"],
        "draft_sha256": draft["draft_sha256"],
        "verification_sha256": evidence["verification_sha256"],
        "approval_sha256": approval["approval_sha256"],
        "publication_sha256": publication["publication_sha256"],
    }
    assertions = {
        "catalog_candidate_is_inert_and_hash_bound": (
            catalog_candidate["execution_allowed"] is False
            and len(catalog_candidate["candidate_sha256"]) == 64
        ),
        "catalog_and_openapi_service_roots_match": (
            _same_service(catalog_candidate["api_endpoint"], operation["server_url"])
        ),
        "existing_tool_roles_were_verified_in_the_registry": all(
            item["present"] for item in reused
        ),
        "initial_exact_operation_was_missing": (
            initial_step["classification"] != "existing_exact"
        ),
        "early_publication_was_blocked": early_publication_blocked,
        "three_or_more_verification_calls_passed": (
            evidence["all_cases_passed"] is True and evidence["case_count"] >= 3
        ),
        "publication_required_explicit_loading": (
            absent_before_load and loaded == [scenario["tool_name"]]
        ),
        "final_plan_resolved_the_exact_operation": (
            final_step["classification"] == "existing_exact"
        ),
        "complete_hash_chain_was_recorded": all(
            isinstance(value, str) and len(value) == 64
            for value in hash_chain.values()
        ),
    }
    if not all(assertions.values()):
        failed = sorted(name for name, passed in assertions.items() if not passed)
        raise RuntimeError(f"Scenario assertions failed: {failed!r}")
    return {
        "case_id": scenario["case_id"],
        "title": scenario["title"],
        "research_question": scenario["research_question"],
        "decision_context": scenario["decision_context"],
        "evidence_mode": mode,
        "source": {
            "catalog": "SmartAPI",
            "catalog_query": scenario["catalog_query"],
            "catalog_record_id": catalog_candidate["catalog_record_id"],
            "catalog_candidate_id": catalog_candidate["candidate_id"],
            "service_endpoint": catalog_candidate["api_endpoint"],
            "operation_id": operation["operation_id"],
            "operation_path": operation["path"],
            "operation_blockers": operation["blockers"],
            "promotion_mode": scenario["promotion_mode"],
            "inspection": inspection,
        },
        "existing_tooluniverse_coverage": reused,
        "without_vsd": {
            **scenario["without_vsd"],
            "planned_operation_classification": initial_step["classification"],
            "planned_operation_matches": [
                item["name"] for item in initial_step["matches"]
            ],
            "executable_new_operation": False,
        },
        "with_vsd": {
            **scenario["with_vsd"],
            "planned_operation_classification": final_step["classification"],
            "published_tool": scenario["tool_name"],
            "verification_case_count": evidence["case_count"],
            "executable_new_operation": True,
            "runtime": _runtime_summary(result, scenario),
        },
        "governance": {
            "early_publication_blocked": early_publication_blocked,
            "resolved_blockers": publication["config"]["vsd_promotion"].get(
                "resolved_blockers", []
            ),
            "loaded_into_fresh_universe": loaded,
            "hash_chain": hash_chain,
        },
        "limitations": scenario["limitations"],
        "references": scenario["references"],
        "assertions": assertions,
    }


def _safe_failure(exc: Exception) -> dict[str, str]:
    message = " ".join(str(exc).split())[:300]
    return {"type": type(exc).__name__, "message": message}


def run_portfolio(
    *,
    workspace: Path,
    mode: str = "replay",
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Run all five scenarios through one reusable evaluation pipeline."""
    if mode not in {"replay", "live", "network_backed"}:
        raise ValueError("mode must be replay, live, or network_backed")
    scenarios = load_scenarios()
    results = []
    for scenario in scenarios:
        case_workspace = workspace / scenario["case_id"]
        fallback = None
        if mode == "network_backed":
            try:
                result = _run_once(scenario, case_workspace / "live", mode="live")
            except Exception as exc:
                fallback = _safe_failure(exc)
                result = _run_once(
                    scenario, case_workspace / "replay", mode="replay"
                )
        else:
            result = _run_once(scenario, case_workspace, mode=mode)
        if fallback is not None:
            result["live_attempt"] = {
                "completed": False,
                "fallback": "checked replay",
                "failure": fallback,
            }
        elif mode in {"live", "network_backed"}:
            result["live_attempt"] = {"completed": True, "fallback": None}
        results.append(result)

    body = {
        "format": "vsd_biomedical_evaluation_portfolio_v1",
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
        "requested_mode": mode,
        "case_count": len(results),
        "live_case_count": sum(item["evidence_mode"] == "live" for item in results),
        "replay_case_count": sum(
            item["evidence_mode"] == "replay" for item in results
        ),
        "published_tool_count": len(results),
        "verification_execution_count": sum(
            item["with_vsd"]["verification_case_count"] for item in results
        ),
        "all_assertions_passed": all(
            all(item["assertions"].values()) for item in results
        ),
        "cases": results,
    }
    return {**body, "portfolio_sha256": _digest(body)}


def validate_portfolio(artifact: Any) -> dict[str, Any]:
    if not isinstance(artifact, dict) or artifact.get("format") != (
        "vsd_biomedical_evaluation_portfolio_v1"
    ):
        raise ValueError("Portfolio artifact format is invalid")
    body = {key: value for key, value in artifact.items() if key != "portfolio_sha256"}
    if artifact.get("portfolio_sha256") != _digest(body):
        raise ValueError("Portfolio artifact digest does not match its content")
    if (
        artifact.get("case_count") != 5
        or artifact.get("published_tool_count") != 5
        or artifact.get("verification_execution_count", 0) < 15
        or artifact.get("all_assertions_passed") is not True
    ):
        raise ValueError("Portfolio artifact is incomplete")
    return json.loads(json.dumps(artifact))


def render_markdown(artifact: dict[str, Any]) -> str:
    validate_portfolio(artifact)
    lines = [
        "# Biomedical VSD Evaluation Portfolio",
        "",
        "## Evaluation Summary",
        "",
        (
            f"Five research workflows were evaluated through the same registry-first "
            f"pipeline. The run published {artifact['published_tool_count']} narrowly "
            f"scoped tools after {artifact['verification_execution_count']} verification "
            f"executions; all recorded assertions passed."
        ),
        "",
        f"- Requested evidence mode: `{artifact['requested_mode']}`",
        f"- Live cases: `{artifact['live_case_count']}`",
        f"- Checked-replay cases: `{artifact['replay_case_count']}`",
        f"- Portfolio SHA-256: `{artifact['portfolio_sha256']}`",
        "",
    ]
    for index, case in enumerate(artifact["cases"], start=1):
        lines.extend(
            [
                f"## {index}. {case['title']}",
                "",
                f"**Question.** {case['research_question']}",
                "",
                f"**Decision context.** {case['decision_context']}",
                "",
                (
                    f"**Evidence qualification.** This case completed in "
                    f"`{case['evidence_mode']}` mode."
                    + (
                        f" The live attempt stopped at a governed boundary "
                        f"(`{case['live_attempt']['failure']['type']}`), so the "
                        f"checked replay is reported and no live result is claimed."
                        if case.get("live_attempt", {}).get("completed") is False
                        else ""
                    )
                ),
                "",
                "### Existing ToolUniverse Coverage",
                "",
            ]
        )
        for item in case["existing_tooluniverse_coverage"]:
            lines.append(f"- `{item['name']}`: {item['role']}")
        lines.extend(
            [
                "",
                "### Gap And Source Qualification",
                "",
                (
                    f"The baseline planner classified the required operation as "
                    f"`{case['without_vsd']['planned_operation_classification']}`. "
                    f"SmartAPI query `{case['source']['catalog_query']}` selected "
                    f"record `{case['source']['catalog_record_id']}`, and inspection "
                    f"selected `{case['source']['operation_id']}` at "
                    f"`{case['source']['operation_path']}`."
                ),
                "",
                (
                    f"Promotion mode was `{case['source']['promotion_mode']}`. The "
                    f"candidate, source document, operation, draft, verification, "
                    f"approval, and publication identities are retained in the JSON "
                    f"artifact."
                ),
                "",
                "### Comparison",
                "",
                f"**Without VSD.** {case['without_vsd']['summary']}",
                "",
                f"**With VSD.** {case['with_vsd']['summary']}",
                "",
                (
                    f"The final planner classified the exact operation as "
                    f"`{case['with_vsd']['planned_operation_classification']}` after "
                    f"`{case['with_vsd']['verification_case_count']}` verification calls "
                    f"and explicit loading of `{case['with_vsd']['published_tool']}`."
                ),
                "",
                "### Observed Result",
                "",
            ]
        )
        for observation in case["with_vsd"]["runtime"]["observations"]:
            value = json.dumps(observation["value"], sort_keys=True, ensure_ascii=True)
            lines.append(f"- {observation['label']}: `{value}`")
        lines.extend(["", "### Limitations", ""])
        lines.extend(f"- {item}" for item in case["limitations"])
        lines.extend(["", "### References", ""])
        lines.extend(
            f"- [{item['title']}]({item['url']})" for item in case["references"]
        )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_artifacts(
    artifact: dict[str, Any], output_json: Path, output_markdown: Path
) -> tuple[Path, Path]:
    validate_portfolio(artifact)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_markdown.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(
        json.dumps(artifact, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    output_markdown.write_text(render_markdown(artifact), encoding="utf-8")
    return output_json, output_markdown


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode", choices=("replay", "live", "network_backed"), default="replay"
    )
    parser.add_argument("--workspace", type=Path)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--output-markdown", type=Path, default=DEFAULT_MARKDOWN)
    arguments = parser.parse_args()
    if arguments.workspace is None:
        with tempfile.TemporaryDirectory(prefix="vsd-biomedical-portfolio-") as root:
            artifact = run_portfolio(workspace=Path(root), mode=arguments.mode)
    else:
        artifact = run_portfolio(
            workspace=arguments.workspace, mode=arguments.mode
        )
    write_artifacts(artifact, arguments.output_json, arguments.output_markdown)
    print(json.dumps({"portfolio_sha256": artifact["portfolio_sha256"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
