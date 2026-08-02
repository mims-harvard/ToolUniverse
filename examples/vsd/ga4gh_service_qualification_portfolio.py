"""Qualify standard GA4GH Service Info operations through the VSD lifecycle."""

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
import tooluniverse.vsd_reviewed_runtime as reviewed_runtime
from tooluniverse import ToolUniverse
from tooluniverse.vsd_promotion import (
    VSDPromotionError,
    approve_draft,
    create_ga4gh_service_info_draft,
    ga4gh_service_info_verification_cases,
    list_promotion_state,
    load_published_tools,
    publish_draft,
    verify_draft,
)
from tooluniverse.vsd_reviewed_runtime import VSDReviewedRuntimeError

HERE = Path(__file__).resolve().parent
SCENARIO_FILE = HERE / "ga4gh_service_qualification" / "scenarios.json"
ARTIFACTS = HERE / "artifacts"
DEFAULT_JSON = ARTIFACTS / "ga4gh_service_qualification_portfolio.json"
DEFAULT_MARKDOWN = ARTIFACTS / "ga4gh_service_qualification_portfolio.md"

_CASE_ID_RE = re.compile(r"^[a-z][a-z0-9_]{2,63}$")
_TOOL_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{2,44}$")
_REQUIRED_FIELDS = {
    "case_id",
    "catalog_query",
    "tool_name",
    "expected_qualification",
    "registry_record",
    "replay_transport",
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


def _safe_error(exc: Exception) -> dict[str, str]:
    message = " ".join(str(exc).split())[:500]
    lowered = message.casefold()
    if "case-insensitive json pointer" in lowered or "pointer equality" in lowered:
        category = "registered_metadata_mismatch"
    elif "content type" in lowered:
        category = "response_media_type_mismatch"
    elif "redirect" in lowered:
        category = "redirect_rejected"
    elif "http" in lowered and any(
        code in lowered for code in ("400", "401", "403", "404", "500", "502", "503")
    ):
        category = "http_status_failure"
    else:
        category = "execution_failure"
    return {"type": type(exc).__name__, "category": category, "message": message}


def _validate_registry_record(record: Any) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise ValueError("registry_record must be an object")
    required = {"id", "name", "type", "organization", "version", "url"}
    service_type = record.get("type")
    if (
        not required <= set(record)
        or any(
            not isinstance(record.get(field), str) or not record[field]
            for field in ("id", "name", "version", "url")
        )
        or not isinstance(service_type, dict)
        or set(service_type) != {"group", "artifact", "version"}
        or any(
            not isinstance(value, str) or not value for value in service_type.values()
        )
        or not isinstance(record.get("organization"), dict)
    ):
        raise ValueError("registry_record is incomplete")
    return json.loads(json.dumps(record))


def _validate_transport(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("replay_transport must be an object")
    status = value.get("status_code")
    content_type = value.get("content_type")
    if (
        isinstance(status, bool)
        or not isinstance(status, int)
        or not 100 <= status <= 599
        or not isinstance(content_type, str)
        or not isinstance(
            value.get("payload", value.get("body", "")), (dict, list, str)
        )
    ):
        raise ValueError("replay_transport is invalid")
    if ("payload" in value) == ("body" in value):
        raise ValueError("replay_transport must contain exactly one response body")
    return json.loads(json.dumps(value))


def load_scenarios() -> list[dict[str, Any]]:
    values = json.loads(SCENARIO_FILE.read_text(encoding="utf-8"))
    if not isinstance(values, list) or len(values) != 15:
        raise ValueError("The portfolio requires 15 service scenarios")
    scenarios = []
    for value in values:
        if not isinstance(value, dict) or set(value) != _REQUIRED_FIELDS:
            raise ValueError("Scenario structure is invalid")
        case_id = value["case_id"]
        tool_name = value["tool_name"]
        query = value["catalog_query"]
        expected = value["expected_qualification"]
        if (
            not isinstance(case_id, str)
            or not _CASE_ID_RE.fullmatch(case_id)
            or not isinstance(tool_name, str)
            or not _TOOL_NAME_RE.fullmatch(tool_name)
            or not isinstance(query, str)
            or not 2 <= len(query) <= 200
            or expected not in {"accepted", "rejected"}
        ):
            raise ValueError("Scenario identity is invalid")
        scenarios.append(
            {
                **value,
                "registry_record": _validate_registry_record(value["registry_record"]),
                "replay_transport": _validate_transport(value["replay_transport"]),
            }
        )
    if len({item["case_id"] for item in scenarios}) != len(scenarios):
        raise ValueError("Scenario case IDs must be unique")
    if len({item["tool_name"].casefold() for item in scenarios}) != len(scenarios):
        raise ValueError("Scenario tool names must be unique")
    return scenarios


def _request_metadata(url: str, payload: Any, content_type: str) -> dict[str, Any]:
    encoded = _canonical(payload)
    return {
        "url": url,
        "status_code": 200,
        "content_type": content_type,
        "response_bytes": len(encoded),
        "peer_ip": "93.184.216.34",
        "redirects": 0,
    }


@contextmanager
def _catalog_transport(scenarios: list[dict[str, Any]], *, mode: str) -> Iterator[None]:
    if mode == "live":
        yield
        return
    original = vsd_discovery._safe_get_json
    payload = [item["registry_record"] for item in scenarios]

    def fetch(url, params=None, **kwargs):
        del params, kwargs
        return payload, _request_metadata(url, payload, "application/json")

    vsd_discovery._safe_get_json = fetch
    try:
        yield
    finally:
        vsd_discovery._safe_get_json = original


@contextmanager
def _service_transport(scenario: dict[str, Any], *, mode: str) -> Iterator[None]:
    if mode == "live":
        yield
        return
    original = reviewed_runtime._http_exchange
    transport = scenario["replay_transport"]

    def exchange(**kwargs):
        status = transport["status_code"]
        if 300 <= status < 400:
            raise VSDReviewedRuntimeError("Provider redirect is prohibited")
        if status != 200:
            raise VSDReviewedRuntimeError(f"Provider returned HTTP status {status}")
        value = transport.get("payload", transport.get("body", ""))
        raw = _canonical(value) if "payload" in transport else value.encode("utf-8")
        return raw, {
            "url": kwargs["url"],
            "status_code": status,
            "content_type": transport["content_type"],
            "response_bytes": len(raw),
            "headers": {},
            "peer_ip": "93.184.216.34",
            "redirects": 0,
        }

    reviewed_runtime._http_exchange = exchange
    try:
        yield
    finally:
        reviewed_runtime._http_exchange = original


@contextmanager
def _allowed_service_host(endpoint: str) -> Iterator[None]:
    host = (urlsplit(endpoint).hostname or "").casefold().rstrip(".")
    previous = os.environ.get("TOOLUNIVERSE_VSD_ALLOWED_HOSTS")
    allowed = {item.strip() for item in (previous or "").split(",") if item.strip()}
    allowed.add(host)
    os.environ["TOOLUNIVERSE_VSD_ALLOWED_HOSTS"] = ",".join(sorted(allowed))
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop("TOOLUNIVERSE_VSD_ALLOWED_HOSTS", None)
        else:
            os.environ["TOOLUNIVERSE_VSD_ALLOWED_HOSTS"] = previous


def _tool_data(
    universe: ToolUniverse, name: str, arguments: dict[str, Any]
) -> dict[str, Any]:
    response = universe.run_one_function(
        {"name": name, "arguments": arguments}, use_cache=False
    )
    if not isinstance(response, dict) or response.get("status") != "success":
        raise RuntimeError(f"Tool {name!r} did not complete successfully")
    data = response.get("data")
    if not isinstance(data, dict):
        raise RuntimeError(f"Tool {name!r} returned an invalid result envelope")
    return data


def _discover(
    universe: ToolUniverse,
    scenario: dict[str, Any],
    scenarios: list[dict[str, Any]],
    *,
    mode: str,
) -> dict[str, Any]:
    with _catalog_transport(scenarios, mode=mode):
        return _tool_data(
            universe,
            "VSDDiscoverAPICandidates",
            {
                "query": scenario["catalog_query"],
                "providers": ["ga4gh_registry"],
                "exclude_registered": True,
                "limit": 20,
            },
        )


def _select_candidate(discovery: dict[str, Any], registry_id: str) -> dict[str, Any]:
    matches = []
    for candidate in discovery.get("candidates", []):
        source_ids = {
            item.get("record_id")
            for item in candidate.get("catalog_sources", [])
            if isinstance(item, dict)
        }
        if registry_id in source_ids:
            matches.append(candidate)
    if len(matches) != 1:
        raise RuntimeError(
            f"Discovery did not return one candidate for registry record {registry_id!r}"
        )
    return matches[0]


def _catalog_provenance(discovery: dict[str, Any]) -> dict[str, Any]:
    providers = discovery.get("provider_results")
    if not isinstance(providers, list) or len(providers) != 1:
        raise RuntimeError("Discovery did not record one catalog provider")
    provenance = providers[0].get("provenance")
    required = {
        "endpoint",
        "retrieved_at",
        "http_status",
        "response_bytes",
        "payload_sha256",
    }
    if not isinstance(provenance, dict) or not required <= set(provenance):
        raise RuntimeError("Discovery catalog provenance is incomplete")
    return {field: provenance[field] for field in sorted(required)}


def _blocked_before_verification(draft_id: str, workspace: Path) -> bool:
    try:
        publish_draft(draft_id, workspace=workspace)
    except VSDPromotionError:
        return True
    return False


def _run_rejected_case(
    scenario: dict[str, Any],
    candidate: dict[str, Any],
    draft: dict[str, Any],
    workspace: Path,
    *,
    mode: str,
    early_publication_blocked: bool,
) -> dict[str, Any]:
    verification_error: dict[str, str] | None = None
    with (
        _allowed_service_host(candidate["api_endpoint"]),
        _service_transport(scenario, mode=mode),
    ):
        try:
            verify_draft(
                draft["draft_id"],
                ga4gh_service_info_verification_cases(candidate),
                workspace=workspace,
            )
        except Exception as exc:
            verification_error = _safe_error(exc)
    if verification_error is None:
        raise RuntimeError(
            "Qualification outcome changed; the scenario requires review before approval"
        )
    approval_blocked = False
    try:
        approve_draft(
            draft["draft_id"],
            reviewed_by="GA4GH Qualification Reviewer",
            decision_note="This operation must not be approved without conforming evidence.",
            workspace=workspace,
        )
    except VSDPromotionError:
        approval_blocked = True
    state = list_promotion_state(workspace=workspace)
    assertions = {
        "candidate_remained_inert": candidate["execution_allowed"] is False,
        "candidate_binding_was_hash_sealed": len(candidate["candidate_sha256"]) == 64,
        "early_publication_was_blocked": early_publication_blocked,
        "qualification_failed_closed": verification_error is not None,
        "approval_without_evidence_was_blocked": approval_blocked,
        "no_approval_was_recorded": state["approvals"] == [],
        "no_publication_was_recorded": state["approved"] == [],
    }
    if not all(assertions.values()):
        raise RuntimeError("Rejected qualification case did not fail closed")
    return {
        "qualification": "rejected",
        "verification_execution_count": 0,
        "final_execution_count": 0,
        "published_tool": None,
        "failure": verification_error,
        "governance": {
            "early_publication_blocked": early_publication_blocked,
            "approval_blocked": approval_blocked,
            "promotion_state": state,
        },
        "assertions": assertions,
    }


def _run_accepted_case(
    scenario: dict[str, Any],
    candidate: dict[str, Any],
    draft: dict[str, Any],
    workspace: Path,
    scenarios: list[dict[str, Any]],
    *,
    mode: str,
    early_publication_blocked: bool,
) -> dict[str, Any]:
    with (
        _allowed_service_host(candidate["api_endpoint"]),
        _service_transport(scenario, mode=mode),
    ):
        evidence = verify_draft(
            draft["draft_id"],
            ga4gh_service_info_verification_cases(candidate),
            workspace=workspace,
        )
        approval = approve_draft(
            draft["draft_id"],
            reviewed_by="GA4GH Qualification Reviewer",
            decision_note=(
                "Approved after three executions matched the registered service name "
                "and standard type."
            ),
            workspace=workspace,
        )
        publication = publish_draft(draft["draft_id"], workspace=workspace)
        runtime = ToolUniverse()
        runtime.load_tools(include_tools=["VSDDiscoverAPICandidates"], quiet=True)
        try:
            absent_before_load = scenario["tool_name"] not in runtime.all_tool_dict
            loaded = load_published_tools(runtime, workspace=workspace)
            final = _tool_data(runtime, scenario["tool_name"], {})
            post_discovery = _discover(runtime, scenario, scenarios, mode=mode)
        finally:
            runtime.close()

    requested_id = scenario["registry_record"]["id"]
    requested_candidates = [
        item
        for item in post_discovery.get("candidates", [])
        if requested_id
        in {
            source.get("record_id")
            for source in item.get("catalog_sources", [])
            if isinstance(source, dict)
        }
    ]
    result = final["result"]
    hash_chain = {
        "catalog_candidate_sha256": candidate["candidate_sha256"],
        "draft_sha256": draft["draft_sha256"],
        "verification_sha256": evidence["verification_sha256"],
        "approval_sha256": approval["approval_sha256"],
        "publication_sha256": publication["publication_sha256"],
    }
    assertions = {
        "candidate_remained_inert_until_review": candidate["execution_allowed"]
        is False,
        "candidate_binding_was_hash_sealed": len(candidate["candidate_sha256"]) == 64,
        "early_publication_was_blocked": early_publication_blocked,
        "three_conformance_executions_passed": evidence["case_count"] == 3,
        "publication_required_explicit_loading": (
            absent_before_load and loaded == [scenario["tool_name"]]
        ),
        "fresh_runtime_execution_succeeded": isinstance(result, dict),
        "post_load_discovery_suppressed_the_exact_operation": (
            requested_candidates == []
            and post_discovery["registered_duplicate_count"] >= 1
        ),
        "complete_hash_chain_was_recorded": all(
            isinstance(value, str) and len(value) == 64 for value in hash_chain.values()
        ),
    }
    if not all(assertions.values()):
        failed = sorted(name for name, passed in assertions.items() if not passed)
        raise RuntimeError(f"Accepted qualification assertions failed: {failed!r}")
    return {
        "qualification": "accepted",
        "verification_execution_count": evidence["case_count"],
        "final_execution_count": 1,
        "published_tool": scenario["tool_name"],
        "failure": None,
        "observed_service": {
            "id": result.get("id"),
            "name": result.get("name"),
            "type": result.get("type"),
            "payload_sha256": final["provenance"]["payload_sha256"],
        },
        "governance": {
            "early_publication_blocked": early_publication_blocked,
            "loaded_into_fresh_universe": loaded,
            "registered_duplicate_count": post_discovery["registered_duplicate_count"],
            "hash_chain": hash_chain,
        },
        "assertions": assertions,
    }


def _run_once(
    scenario: dict[str, Any],
    scenarios: list[dict[str, Any]],
    workspace: Path,
    *,
    mode: str,
) -> dict[str, Any]:
    initial = ToolUniverse()
    initial.load_tools(include_tools=["VSDDiscoverAPICandidates"], quiet=True)
    try:
        discovery = _discover(initial, scenario, scenarios, mode=mode)
        candidate = _select_candidate(discovery, scenario["registry_record"]["id"])
        catalog_provenance = _catalog_provenance(discovery)
    finally:
        initial.close()

    promotion_workspace = workspace / "promotion"
    draft = create_ga4gh_service_info_draft(
        candidate,
        tool_name=scenario["tool_name"],
        description=(
            "Return the reviewed standard service metadata for this registered "
            "GA4GH implementation."
        ),
        review_note=(
            "Reviewed the registry identity, derived Service Info path, response "
            "boundary, and required service-type assertions."
        ),
        workspace=promotion_workspace,
    )
    early_blocked = _blocked_before_verification(draft["draft_id"], promotion_workspace)
    if scenario["expected_qualification"] == "accepted":
        try:
            qualification = _run_accepted_case(
                scenario,
                candidate,
                draft,
                promotion_workspace,
                scenarios,
                mode=mode,
                early_publication_blocked=early_blocked,
            )
        except Exception as exc:
            state = list_promotion_state(workspace=promotion_workspace)
            if state["approved"]:
                raise
            raise RuntimeError(
                f"Expected conforming service failed qualification: {_safe_error(exc)}"
            ) from exc
    else:
        qualification = _run_rejected_case(
            scenario,
            candidate,
            draft,
            promotion_workspace,
            mode=mode,
            early_publication_blocked=early_blocked,
        )
    return {
        "case_id": scenario["case_id"],
        "evidence_mode": mode,
        "catalog_query": scenario["catalog_query"],
        "registry_record_id": scenario["registry_record"]["id"],
        "registered_name": candidate["service_binding"]["registered_name"],
        "registered_type": candidate["service_binding"]["registered_type"],
        "service_root": candidate["service_binding"]["service_root"],
        "service_info_endpoint": candidate["api_endpoint"],
        "candidate_id": candidate["candidate_id"],
        "catalog_provenance": catalog_provenance,
        "without_vsd": {
            "catalog_record_discovered": True,
            "executable_service_info_tool": False,
            "qualification_evidence": False,
        },
        "with_vsd": qualification,
    }


def run_portfolio(
    *,
    workspace: Path,
    mode: str = "replay",
    generated_at: str | None = None,
) -> dict[str, Any]:
    if mode not in {"replay", "live", "network_backed"}:
        raise ValueError("mode must be replay, live, or network_backed")
    scenarios = load_scenarios()
    results = []
    for scenario in scenarios:
        case_workspace = workspace / scenario["case_id"]
        fallback = None
        if mode == "network_backed":
            try:
                result = _run_once(
                    scenario, scenarios, case_workspace / "live", mode="live"
                )
            except Exception as exc:
                fallback = _safe_error(exc)
                result = _run_once(
                    scenario, scenarios, case_workspace / "replay", mode="replay"
                )
        else:
            result = _run_once(scenario, scenarios, case_workspace, mode=mode)
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
        "format": "vsd_ga4gh_service_qualification_portfolio_v1",
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
        "requested_mode": mode,
        "case_count": len(results),
        "live_case_count": sum(item["evidence_mode"] == "live" for item in results),
        "replay_case_count": sum(item["evidence_mode"] == "replay" for item in results),
        "accepted_count": sum(
            item["with_vsd"]["qualification"] == "accepted" for item in results
        ),
        "rejected_count": sum(
            item["with_vsd"]["qualification"] == "rejected" for item in results
        ),
        "published_tool_count": sum(
            item["with_vsd"]["published_tool"] is not None for item in results
        ),
        "verification_execution_count": sum(
            item["with_vsd"]["verification_execution_count"] for item in results
        ),
        "final_execution_count": sum(
            item["with_vsd"]["final_execution_count"] for item in results
        ),
        "all_assertions_passed": all(
            all(item["with_vsd"]["assertions"].values()) for item in results
        ),
        "cases": results,
    }
    return {**body, "portfolio_sha256": _digest(body)}


def validate_portfolio(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("format") != (
        "vsd_ga4gh_service_qualification_portfolio_v1"
    ):
        raise ValueError("Portfolio artifact format is invalid")
    body = {key: item for key, item in value.items() if key != "portfolio_sha256"}
    if value.get("portfolio_sha256") != _digest(body):
        raise ValueError("Portfolio artifact digest does not match its content")
    if (
        value.get("case_count") != 15
        or value.get("accepted_count") != 3
        or value.get("rejected_count") != 12
        or value.get("published_tool_count") != 3
        or value.get("verification_execution_count") != 9
        or value.get("final_execution_count") != 3
        or value.get("all_assertions_passed") is not True
    ):
        raise ValueError("Portfolio artifact is incomplete")
    return json.loads(json.dumps(value))


def render_markdown(value: dict[str, Any]) -> str:
    artifact = validate_portfolio(value)
    lines = [
        "# GA4GH Service Qualification Portfolio",
        "",
        "## Scope",
        "",
        (
            "This evaluation asked whether an official registry entry was sufficient "
            "to create a usable ToolUniverse operation. VSD derived only the standard "
            "Service Info path, then required live response structure and registered "
            "service-type agreement before approval."
        ),
        "",
        "The same parameterized runner evaluated every service; organization names, "
        "URLs, expected outcomes, and replay responses are scenario data.",
        "",
        "## Results",
        "",
        f"- Evaluated services: `{artifact['case_count']}`",
        f"- Accepted and published: `{artifact['accepted_count']}`",
        f"- Rejected before approval: `{artifact['rejected_count']}`",
        f"- Verification executions: `{artifact['verification_execution_count']}`",
        f"- Fresh-universe executions: `{artifact['final_execution_count']}`",
        f"- Live cases: `{artifact['live_case_count']}`",
        f"- Checked-replay cases: `{artifact['replay_case_count']}`",
        f"- Portfolio SHA-256: `{artifact['portfolio_sha256']}`",
        "",
        "| Registry record | Standard | Endpoint | Result | Evidence |",
        "| --- | --- | --- | --- | --- |",
    ]
    for case in artifact["cases"]:
        service_type = case["registered_type"]
        outcome = case["with_vsd"]["qualification"]
        failure = case["with_vsd"].get("failure")
        evidence = (
            "3 conformance calls, publication, fresh load, and final execution"
            if outcome == "accepted"
            else failure["category"].replace("_", " ")
        )
        lines.append(
            "| "
            + " | ".join(
                (
                    case["registry_record_id"],
                    f"{service_type['artifact']} {service_type['version']}",
                    case["service_info_endpoint"],
                    outcome,
                    evidence,
                )
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Lifecycle Evidence",
            "",
            (
                "Every discovered candidate was non-executable and content-addressed. "
                "All 15 drafts were blocked from publication before verification. The "
                "three conforming services passed registry-bound assertions three "
                "times, were explicitly approved and published, remained absent from "
                "a fresh ToolUniverse until loaded, executed successfully after loading, "
                "and were suppressed from the next discovery result as exact duplicates."
            ),
            "",
            (
                "The other 12 candidates produced no approval or publication artifact. "
                "They included valid JSON with service-type drift, unavailable standard "
                "paths, HTML responses at API-looking URLs, and a redirect."
            ),
            "",
            "## Interpretation",
            "",
            (
                "Without VSD, the registry supplies useful leads but does not establish "
                "that their standard metadata operation is reachable or still agrees "
                "with the registered contract. With VSD, conforming leads become narrow, "
                "auditable ToolUniverse operations while stale or inconsistent records "
                "fail before approval. In this snapshot, indiscriminate registration "
                "would have treated all 15 records as usable; qualification admitted "
                "three and prevented 12 unsupported additions."
            ),
            "",
            "## Reproduction",
            "",
            "```console",
            "PYTHONPATH=src python examples/vsd/ga4gh_service_qualification_portfolio.py --mode replay",
            "PYTHONPATH=src python examples/vsd/ga4gh_service_qualification_portfolio.py --mode network_backed",
            "```",
            "",
            (
                "Replay uses checked provider-shaped responses. Network-backed mode "
                "labels each service independently as live or checked replay and records "
                "the bounded reason for any fallback."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def write_artifacts(
    artifact: dict[str, Any], json_path: Path, markdown_path: Path
) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(artifact, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(render_markdown(artifact), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate GA4GH Service Info candidates through the VSD lifecycle."
    )
    parser.add_argument(
        "--mode", choices=("replay", "live", "network_backed"), default="replay"
    )
    parser.add_argument("--workspace", type=Path)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--output-markdown", type=Path, default=DEFAULT_MARKDOWN)
    arguments = parser.parse_args()
    if arguments.workspace is None:
        with tempfile.TemporaryDirectory(prefix="vsd-ga4gh-qualification-") as root:
            artifact = run_portfolio(workspace=Path(root), mode=arguments.mode)
    else:
        artifact = run_portfolio(
            workspace=arguments.workspace.resolve(), mode=arguments.mode
        )
    write_artifacts(
        artifact, arguments.output_json.resolve(), arguments.output_markdown.resolve()
    )
    print(json.dumps(artifact, indent=2, sort_keys=True, ensure_ascii=True))


if __name__ == "__main__":
    main()
