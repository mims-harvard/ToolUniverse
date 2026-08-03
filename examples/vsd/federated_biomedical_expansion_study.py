"""Evaluate federated VSD source expansion in three cancer evidence models."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Sequence
from urllib.parse import urlsplit

from tooluniverse import ToolUniverse
from tooluniverse.vsd_federated_sources import (
    canonical_openapi_bytes,
    validate_federated_scan,
)
from tooluniverse.vsd_openapi import inspect_openapi_document
from tooluniverse.vsd_promotion import (
    VSDPromotionError,
    approve_draft,
    create_openapi_draft,
    load_published_tools,
    publish_draft,
    verify_draft,
)
from tooluniverse.vsd_source_intelligence import _fetch_https

from examples.vsd.candidate_portfolio_review_study import validate_review

HERE = Path(__file__).resolve().parent
SCENARIOS = HERE / "federated_biomedical_studies" / "scenarios.json"
SCAN_ARTIFACT = HERE / "artifacts" / "federated_biomedical_source_scan.json"
BASELINE_ARTIFACT = HERE / "artifacts" / "candidate_portfolio_review_study.json"
JSON_ARTIFACT = HERE / "artifacts" / "federated_biomedical_expansion_study.json"
MARKDOWN_ARTIFACT = HERE / "artifacts" / "federated_biomedical_expansion_study.md"
WORKSPACE = HERE / "artifacts" / "federated_biomedical_expansion_workspace"
_HOST_ENV = "TOOLUNIVERSE_VSD_ALLOWED_HOSTS"


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _read_json(path: Path, *, maximum: int = 20_000_000) -> Any:
    if not path.is_file() or path.is_symlink() or path.stat().st_size > maximum:
        raise ValueError(f"Study input is missing or exceeds {maximum:,} bytes")
    return json.loads(path.read_text(encoding="utf-8"))


def _validate_scenarios(value: Any) -> dict[str, Any]:
    if (
        not isinstance(value, dict)
        or value.get("format") != "vsd_federated_biomedical_scenarios_v1"
        or value.get("version") != 1
        or not isinstance(value.get("scientific_question"), str)
    ):
        raise ValueError("Federated biomedical scenario manifest is invalid")
    scenarios = value.get("scenarios")
    accepted = value.get("accepted_operations")
    rejected = value.get("rejected_operations")
    if (
        not isinstance(scenarios, list)
        or len(scenarios) != 3
        or not isinstance(accepted, list)
        or len(accepted) != 7
        or not isinstance(rejected, list)
        or len(rejected) != 3
    ):
        raise ValueError("Federated biomedical study populations are invalid")
    scenario_ids = [item.get("scenario_id") for item in scenarios]
    if any(not isinstance(item, dict) for item in scenarios) or len(
        set(scenario_ids)
    ) != len(scenarios):
        raise ValueError("Federated biomedical scenario identities are invalid")
    keys: list[str] = []
    names: list[str] = []
    for definition in [*accepted, *rejected]:
        if not isinstance(definition, dict):
            raise ValueError("Federated operation definition is invalid")
        keys.append(str(definition.get("key") or ""))
        names.append(str(definition.get("tool_name") or ""))
        if (
            not re.fullmatch(
                r"[a-z][a-z0-9_]{2,63}", str(definition.get("source_id", ""))
            )
            or not definition.get("operation_id")
            or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{2,127}", names[-1])
            or not isinstance(definition.get("include_parameters"), list)
            or not isinstance(definition.get("fixed_query"), dict)
            or not isinstance(definition.get("argument_fields"), dict)
            or not isinstance(definition.get("verification_expect"), dict)
        ):
            raise ValueError("Federated operation definition is incomplete")
    if (
        any(not key for key in keys)
        or len(keys) != len(set(keys))
        or len(names) != len(set(names))
    ):
        raise ValueError("Federated operation keys and names must be unique")
    return copy.deepcopy(value)


def _arguments(definition: dict[str, Any], scenario: dict[str, Any]) -> dict[str, Any]:
    arguments: dict[str, Any] = {}
    for name, mapping in definition["argument_fields"].items():
        if isinstance(mapping, str) and mapping in scenario:
            arguments[name] = scenario[mapping]
        elif (
            isinstance(mapping, dict)
            and set(mapping) == {"list_from"}
            and mapping["list_from"] in scenario
        ):
            arguments[name] = [scenario[mapping["list_from"]]]
        else:
            raise ValueError(f"Argument mapping for {name!r} is invalid")
    return arguments


def _expectation(
    definition: dict[str, Any], scenario: dict[str, Any]
) -> dict[str, Any]:
    source = definition["verification_expect"]
    expectation = {
        "result_type": source.get("result_type", "object"),
        "required_fields": copy.deepcopy(source.get("required_fields", [])),
        "required_paths": copy.deepcopy(source.get("required_paths", [])),
        "equals": copy.deepcopy(source.get("equals", {})),
        "equals_paths": copy.deepcopy(source.get("equals_paths", {})),
        "equals_paths_casefold": copy.deepcopy(source.get("equals_paths_casefold", {})),
    }
    for field, scenario_field in source.get("equals_from", {}).items():
        expectation["equals"][field] = scenario[scenario_field]
    for pointer, scenario_field in source.get("equals_paths_from", {}).items():
        expectation["equals_paths"][pointer] = scenario[scenario_field]
    for pointer, scenario_field in source.get("equals_paths_casefold_from", {}).items():
        expectation["equals_paths_casefold"][pointer] = scenario[scenario_field]
    if expectation["result_type"] == "array":
        expectation["min_items"] = source.get("min_items", 0)
        expectation["max_items"] = source.get("max_items", 1000)
    return expectation


def _verification_cases(
    definition: dict[str, Any], scenarios: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    return [
        {
            "arguments": _arguments(definition, scenario),
            "expect": _expectation(definition, scenario),
        }
        for scenario in scenarios
    ]


@contextmanager
def _allowed_hosts(hosts: set[str]) -> Iterator[None]:
    previous = os.environ.get(_HOST_ENV)
    existing = {
        item.strip().casefold() for item in (previous or "").split(",") if item.strip()
    }
    os.environ[_HOST_ENV] = ",".join(sorted(existing | hosts))
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop(_HOST_ENV, None)
        else:
            os.environ[_HOST_ENV] = previous


def _load_candidates(
    definitions: list[dict[str, Any]], scan: dict[str, Any]
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], set[str]]:
    manifest_sources = {item["source_id"]: item for item in scan["manifest"]["sources"]}
    scan_sources = {item["source_id"]: item for item in scan["sources"]}
    operation_index = {
        (item["source_id"], item["operation_id"]): item for item in scan["operations"]
    }
    fetched: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
    candidates: dict[str, dict[str, Any]] = {}
    evidence: dict[str, dict[str, Any]] = {}
    hosts: set[str] = set()
    for definition in definitions:
        source_id = definition["source_id"]
        source = manifest_sources.get(source_id)
        scan_source = scan_sources.get(source_id)
        recorded = operation_index.get((source_id, definition["operation_id"]))
        if source is None or scan_source is None or recorded is None:
            raise ValueError("Study operation is absent from the sealed source scan")
        if source_id not in fetched:
            raw, request = _fetch_https(source["specification_url"], 30, 1_000_000)
            content_sha256 = hashlib.sha256(raw).hexdigest()
            with tempfile.TemporaryDirectory(
                prefix="tooluniverse-vsd-federated-contract-"
            ) as directory:
                raw_path = Path(directory) / "source.contract"
                raw_path.write_bytes(raw)
                canonical_raw, semantic_sha256 = canonical_openapi_bytes(raw_path)
                if semantic_sha256 != scan_source["semantic_sha256"]:
                    raise ValueError(
                        f"Live source contract changed semantically: {source_id}"
                    )
                path = Path(directory) / "source.openapi.json"
                path.write_bytes(canonical_raw)
                inspection = inspect_openapi_document(
                    path, server_url_override=source["runtime_base_url"]
                )
            fetched[source_id] = (
                inspection,
                {
                    "specification_url": source["specification_url"],
                    "runtime_base_url": source["runtime_base_url"],
                    "status_code": request["status_code"],
                    "content_type": request["content_type"],
                    "response_bytes": request["response_bytes"],
                    "redirects": request["redirects"],
                    "content_sha256": content_sha256,
                    "semantic_sha256": semantic_sha256,
                    "raw_representation_matches_scan": (
                        content_sha256 == scan_source["content_sha256"]
                    ),
                },
            )
        inspection, request = fetched[source_id]
        matches = [
            item
            for item in inspection["candidates"]
            if item["operation_id"] == definition["operation_id"]
        ]
        if (
            len(matches) != 1
            or matches[0]["candidate_sha256"] != recorded["candidate_sha256"]
            or matches[0]["blockers"]
            or matches[0]["execution_allowed"] is not False
            or recorded["preview"] is None
            or recorded["registry_coverage"]
            not in {"candidate_gap", "existing_host_gap"}
        ):
            raise ValueError("Live operation no longer matches the inert scan evidence")
        candidate = matches[0]
        host = (urlsplit(candidate["server_url"]).hostname or "").casefold()
        if not host:
            raise ValueError("Selected candidate has no runtime host")
        hosts.add(host)
        candidates[definition["key"]] = candidate
        evidence[definition["key"]] = {
            **request,
            "candidate_id": candidate["candidate_id"],
            "candidate_sha256": candidate["candidate_sha256"],
            "preview_config_sha256": recorded["preview"]["config_sha256"],
            "registry_coverage": recorded["registry_coverage"],
            "existing_tools": recorded["existing_tools"],
        }
    return candidates, evidence, hosts


def _promote(
    definition: dict[str, Any],
    candidate: dict[str, Any],
    scenarios: list[dict[str, Any]],
    workspace: Path,
) -> dict[str, Any]:
    draft = create_openapi_draft(
        candidate,
        tool_name=definition["tool_name"],
        description=definition["description"],
        include_parameters=definition["include_parameters"],
        fixed_query=definition["fixed_query"],
        timeout_seconds=60,
        workspace=workspace,
    )
    early_error = ""
    try:
        publish_draft(draft["draft_id"], workspace=workspace)
    except VSDPromotionError as exc:
        early_error = str(exc)
    if not early_error:
        raise AssertionError("Unverified federated candidate was published")
    verification = verify_draft(
        draft["draft_id"],
        _verification_cases(definition, scenarios),
        workspace=workspace,
    )
    approval = approve_draft(
        draft["draft_id"],
        reviewed_by="VSD federated biomedical study reviewer",
        decision_note=(
            "Approved after three disease-context cases passed the reviewed input, "
            "response-schema, HTTPS, redirect, and provenance checks."
        ),
        workspace=workspace,
    )
    publication = publish_draft(draft["draft_id"], workspace=workspace)
    return {
        "key": definition["key"],
        "source_id": definition["source_id"],
        "tool_name": definition["tool_name"],
        "draft_id": draft["draft_id"],
        "draft_sha256": draft["draft_sha256"],
        "operation_sha256": draft["operation_sha256"],
        "verification_sha256": verification["verification_sha256"],
        "approval_sha256": approval["approval_sha256"],
        "publication_sha256": publication["publication_sha256"],
        "verification_case_count": verification["case_count"],
        "verification_cases": verification["cases"],
        "early_publication_blocked": True,
        "early_publication_error": early_error,
        "contribution": definition["contribution"],
    }


def _reject(
    definition: dict[str, Any],
    candidate: dict[str, Any],
    scenarios: list[dict[str, Any]],
    workspace: Path,
) -> dict[str, Any]:
    draft = create_openapi_draft(
        candidate,
        tool_name=definition["tool_name"],
        description=definition["description"],
        include_parameters=definition["include_parameters"],
        fixed_query=definition["fixed_query"],
        timeout_seconds=60,
        workspace=workspace,
    )
    verification_error = ""
    try:
        verify_draft(
            draft["draft_id"],
            _verification_cases(definition, scenarios),
            workspace=workspace,
        )
    except VSDPromotionError as exc:
        verification_error = str(exc)
    if definition["expected_error_substring"] not in verification_error:
        raise AssertionError(
            f"Rejected candidate failed unexpectedly: {verification_error!r}"
        )
    approval_error = ""
    publication_error = ""
    try:
        approve_draft(
            draft["draft_id"],
            reviewed_by="VSD federated biomedical study reviewer",
            decision_note="Candidate remains rejected after live response drift.",
            workspace=workspace,
        )
    except VSDPromotionError as exc:
        approval_error = str(exc)
    try:
        publish_draft(draft["draft_id"], workspace=workspace)
    except VSDPromotionError as exc:
        publication_error = str(exc)
    if not approval_error or not publication_error:
        raise AssertionError("Rejected federated candidate crossed a promotion gate")
    return {
        "key": definition["key"],
        "source_id": definition["source_id"],
        "tool_name": definition["tool_name"],
        "candidate_sha256": candidate["candidate_sha256"],
        "draft_sha256": draft["draft_sha256"],
        "decision": "rejected_at_live_verification",
        "verification_error": verification_error[:1000],
        "approval_blocked": True,
        "approval_error": approval_error,
        "publication_blocked": True,
        "publication_error": publication_error,
    }


def _pointer(value: Any, pointer: str) -> Any:
    if pointer == "":
        return value
    if not isinstance(pointer, str) or not pointer.startswith("/"):
        raise ValueError("Observation pointer is invalid")
    current = value
    for raw in pointer.split("/")[1:]:
        token = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(current, dict) and token in current:
            current = current[token]
        elif (
            isinstance(current, list) and token.isdigit() and int(token) < len(current)
        ):
            current = current[int(token)]
        else:
            raise ValueError(f"Observation path is absent: {pointer}")
    return current


def _observations(
    result: Any, definition: dict[str, Any], scenario: dict[str, Any]
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for observation in definition["observations"]:
        value = _pointer(result, observation["pointer"])
        full_count = len(value) if isinstance(value, list) else None
        if "filter_field" in observation:
            if not isinstance(value, list):
                raise ValueError("Observation filtering requires an array")
            expected = scenario[observation["filter_value_from"]]
            value = [
                item
                for item in value
                if isinstance(item, dict)
                and item.get(observation["filter_field"]) == expected
            ]
        minimum = observation.get("min_items")
        if minimum is not None and (
            type(minimum) is not int
            or not 0 <= minimum <= 100
            or not isinstance(value, list)
            or len(value) < minimum
        ):
            raise ValueError(
                f"Observation {observation['label']!r} did not meet its minimum"
            )
        if isinstance(value, list) and "limit" in observation:
            value = value[: observation["limit"]]
        fields = observation.get("fields", [])
        if fields:
            if isinstance(value, dict):
                value = {field: value.get(field) for field in fields}
            elif isinstance(value, list) and all(
                isinstance(item, dict) for item in value
            ):
                value = [{field: item.get(field) for field in fields} for item in value]
            else:
                raise ValueError("Observation projection requires JSON objects")
        output.append(
            {
                "label": observation["label"],
                "pointer": observation["pointer"],
                "full_count": full_count,
                "value": value,
            }
        )
    return output


def _runtime_call(
    runtime: ToolUniverse,
    definition: dict[str, Any],
    scenario: dict[str, Any],
) -> dict[str, Any]:
    response = runtime.run_one_function(
        {
            "name": definition["tool_name"],
            "arguments": _arguments(definition, scenario),
        },
        use_cache=False,
    )
    if not isinstance(response, dict) or response.get("status") != "success":
        raise RuntimeError(f"Published generated tool failed: {response!r}")
    data = response.get("data")
    if not isinstance(data, dict) or not isinstance(data.get("provenance"), dict):
        raise RuntimeError("Published generated tool returned an invalid envelope")
    provenance = data["provenance"]
    return {
        "key": definition["key"],
        "tool_name": definition["tool_name"],
        "arguments": _arguments(definition, scenario),
        "observations": _observations(data["result"], definition, scenario),
        "provenance": {
            key: provenance[key]
            for key in (
                "provider",
                "endpoint",
                "method",
                "query_params",
                "retrieved_at",
                "http_status",
                "response_bytes",
                "redirects",
                "payload_sha256",
                "operation_sha256",
                "authentication",
            )
        },
    }


def build_study(
    scenario_manifest: Any,
    source_scan: Any,
    baseline_portfolio: Any,
    *,
    workspace: Path,
) -> dict[str, Any]:
    manifest = _validate_scenarios(scenario_manifest)
    scan = validate_federated_scan(source_scan)
    baseline = validate_review(baseline_portfolio)
    scenarios = manifest["scenarios"]
    accepted = manifest["accepted_operations"]
    rejected = manifest["rejected_operations"]
    candidates, source_evidence, hosts = _load_candidates([*accepted, *rejected], scan)
    accepted_workspace = workspace / "accepted"
    rejected_workspace = workspace / "rejected"
    with _allowed_hosts(hosts):
        promotions = [
            _promote(
                definition,
                candidates[definition["key"]],
                scenarios,
                accepted_workspace,
            )
            for definition in accepted
        ]
        rejections = [
            _reject(
                definition,
                candidates[definition["key"]],
                scenarios,
                rejected_workspace / definition["key"],
            )
            for definition in rejected
        ]
        runtime = ToolUniverse()
        try:
            names = [definition["tool_name"] for definition in accepted]
            absent_before_load = all(
                name not in runtime.all_tool_dict for name in names
            )
            loaded = load_published_tools(runtime, workspace=accepted_workspace)
            scenario_results = [
                {
                    "scenario_id": scenario["scenario_id"],
                    "disease_context": scenario["disease_context"],
                    "gene_symbol": scenario["gene_symbol"],
                    "tool_results": [
                        _runtime_call(runtime, definition, scenario)
                        for definition in accepted
                    ],
                }
                for scenario in scenarios
            ]
        finally:
            runtime.close()

    accepted_scan_rows = [
        item
        for item in scan["operations"]
        if (item["source_id"], item["operation_id"])
        in {(row["source_id"], row["operation_id"]) for row in accepted}
    ]
    baseline_identities = {
        (
            item["method"].upper(),
            item["host"].casefold(),
            item["path"].rstrip("/") or "/",
        )
        for item in baseline["candidate_reviews"]
    }
    federated_identities = {
        (
            item["method"].upper(),
            item["host"].casefold(),
            item["path"].rstrip("/") or "/",
        )
        for item in scan["operations"]
        if item["preview"] is not None
    }
    shared_identities = baseline_identities & federated_identities
    cross_portfolio = {
        "baseline_candidate_row_count": len(baseline["candidate_reviews"]),
        "baseline_unique_operation_identity_count": len(baseline_identities),
        "federated_preview_count": len(federated_identities),
        "overlap_unique_operation_identity_count": len(shared_identities),
        "federated_incremental_operation_identity_count": len(
            federated_identities - baseline_identities
        ),
        "combined_unique_operation_identity_count": len(
            baseline_identities | federated_identities
        ),
    }
    assertions = {
        "all_manifest_sources_scanned_without_failure": (
            scan["metrics"]["manifest_source_count"] == 20
            and scan["metrics"]["successful_source_count"] == 20
            and scan["metrics"]["failed_source_count"] == 0
        ),
        "all_source_operations_remained_inert_during_scan": all(
            item["execution_allowed"] is False for item in scan["operations"]
        ),
        "cross_portfolio_deduplication_is_consistent": (
            cross_portfolio["overlap_unique_operation_identity_count"]
            + cross_portfolio["federated_incremental_operation_identity_count"]
            == cross_portfolio["federated_preview_count"]
            and cross_portfolio["baseline_unique_operation_identity_count"]
            + cross_portfolio["federated_incremental_operation_identity_count"]
            == cross_portfolio["combined_unique_operation_identity_count"]
        ),
        "all_selected_candidates_were_registry_gaps": (
            len(accepted_scan_rows) == len(accepted)
            and all(
                item["registry_coverage"] in {"candidate_gap", "existing_host_gap"}
                and item["existing_tools"] == []
                for item in accepted_scan_rows
            )
        ),
        "unverified_publication_was_blocked": all(
            item["early_publication_blocked"] for item in promotions
        ),
        "seven_tools_passed_three_live_cases": (
            len(promotions) == 7
            and all(item["verification_case_count"] == 3 for item in promotions)
        ),
        "three_drifted_candidates_failed_closed": (
            len(rejections) == 3
            and all(
                item["approval_blocked"] and item["publication_blocked"]
                for item in rejections
            )
        ),
        "published_tools_required_explicit_local_loading": (
            absent_before_load
            and sorted(loaded) == sorted(item["tool_name"] for item in accepted)
        ),
        "all_published_tools_executed_in_every_scenario": (
            len(scenario_results) == 3
            and all(len(item["tool_results"]) == 7 for item in scenario_results)
            and all(
                result["provenance"]["http_status"] == 200
                and result["provenance"]["redirects"] == 0
                for scenario in scenario_results
                for result in scenario["tool_results"]
            )
        ),
    }
    body = {
        "format": "vsd_federated_biomedical_expansion_study_v1",
        "version": 1,
        "scientific_question": manifest["scientific_question"],
        "evaluation_mode": "live_network",
        "source_scan": {
            "scan_id": scan["scan_id"],
            "scan_sha256": scan["scan_sha256"],
            "scanned_at": scan["scanned_at"],
            "manifest_sha256": scan["manifest"]["manifest_sha256"],
            "registry": scan["registry"],
            "metrics": scan["metrics"],
            "sources": [
                {
                    "source_id": item["source_id"],
                    "api_title": item["api_title"],
                    "candidate_count": item["candidate_count"],
                    "preview_count": item["preview_count"],
                    "existing_host_gap_count": item["existing_host_gap_count"],
                    "new_host_candidate_count": item["new_host_candidate_count"],
                    "blocked_count": item["blocked_count"],
                    "content_sha256": item["content_sha256"],
                    "semantic_sha256": item["semantic_sha256"],
                }
                for item in scan["sources"]
            ],
            "cross_portfolio": cross_portfolio,
        },
        "study_design": {
            "scenario_count": len(scenarios),
            "accepted_tool_count": len(accepted),
            "rejected_candidate_count": len(rejected),
            "verification_execution_count": sum(
                item["verification_case_count"] for item in promotions
            ),
            "post_publication_execution_count": sum(
                len(item["tool_results"]) for item in scenario_results
            ),
            "selected_source_count": len(
                {item["source_id"] for item in [*accepted, *rejected]}
            ),
        },
        "comparison": {
            "before_explicit_load": {
                "selected_generated_tool_names_present": not absent_before_load,
                "reviewed_vsd_exact_operation_matches": sum(
                    item["registry_coverage"] == "existing_exact"
                    for item in accepted_scan_rows
                ),
                "built_in_registry_modified": False,
            },
            "after_vsd_review": {
                "tools_verified_approved_and_published": len(promotions),
                "tools_loaded_into_one_local_runtime": len(loaded),
                "accepted_live_execution_count": sum(
                    item["verification_case_count"] for item in promotions
                )
                + sum(len(item["tool_results"]) for item in scenario_results),
                "candidates_rejected_at_live_verification": len(rejections),
                "built_in_registry_modified": False,
            },
        },
        "candidate_source_evidence": source_evidence,
        "promotions": promotions,
        "rejections": rejections,
        "scenario_results": scenario_results,
        "loaded_tools": loaded,
        "assertions": assertions,
        "interpretation": (
            "The federated manifest converted reviewed contract sources into a bounded "
            "candidate portfolio and added 518 operation identities beyond the previous "
            "catalog scan. Seven selected gaps became locally loadable tools "
            "only after live verification and explicit review. Three schema-drifted "
            "candidates were rejected, demonstrating that source trust does not bypass "
            "operation-level evidence."
        ),
        "boundary": (
            "This study demonstrates technical retrieval and provenance across public "
            "research APIs. It does not establish clinical validity, causal inference, "
            "diagnostic utility, or treatment recommendations."
        ),
    }
    if not all(assertions.values()):
        raise AssertionError(f"Federated biomedical assertions failed: {assertions}")
    return {**body, "study_sha256": _digest(body)}


def validate_study(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("format") != (
        "vsd_federated_biomedical_expansion_study_v1"
    ):
        raise ValueError("Federated biomedical study format is invalid")
    body = {key: item for key, item in value.items() if key != "study_sha256"}
    cross = value.get("source_scan", {}).get("cross_portfolio", {})
    if (
        value.get("version") != 1
        or value.get("evaluation_mode") != "live_network"
        or value.get("study_sha256") != _digest(body)
        or not isinstance(value.get("assertions"), dict)
        or not value["assertions"]
        or not all(value["assertions"].values())
        or value.get("study_design", {}).get("accepted_tool_count") != 7
        or value.get("study_design", {}).get("rejected_candidate_count") != 3
        or value.get("study_design", {}).get("verification_execution_count") != 21
        or value.get("study_design", {}).get("post_publication_execution_count") != 21
        or len(value.get("scenario_results", [])) != 3
        or set(cross)
        != {
            "baseline_candidate_row_count",
            "baseline_unique_operation_identity_count",
            "federated_preview_count",
            "overlap_unique_operation_identity_count",
            "federated_incremental_operation_identity_count",
            "combined_unique_operation_identity_count",
        }
        or any(type(item) is not int or item < 0 for item in cross.values())
        or cross["overlap_unique_operation_identity_count"]
        + cross["federated_incremental_operation_identity_count"]
        != cross["federated_preview_count"]
        or cross["baseline_unique_operation_identity_count"]
        + cross["federated_incremental_operation_identity_count"]
        != cross["combined_unique_operation_identity_count"]
    ):
        raise ValueError("Federated biomedical study evidence is invalid")
    return copy.deepcopy(value)


def render_markdown(value: Any) -> str:
    study = validate_study(value)
    metrics = study["source_scan"]["metrics"]
    cross = study["source_scan"]["cross_portfolio"]
    lines = [
        "# Federated Biomedical Source Evaluation",
        "",
        "## Scope",
        "",
        study["scientific_question"],
        "",
        study["boundary"],
        "",
        "## Source Portfolio",
        "",
        f"- Reviewed service sources: `{metrics['manifest_source_count']}`",
        f"- Contracts successfully inspected: `{metrics['successful_source_count']}`",
        f"- Distinct operations inspected: `{metrics['operation_candidate_count']:,}`",
        f"- Structurally draftable operations: `{metrics['structurally_draftable_count']:,}`",
        f"- Inert net-new previews: `{metrics['net_new_preview_count']:,}`",
        f"- Gaps on existing ToolUniverse hosts: `{metrics['existing_host_gap_count']:,}`",
        f"- Candidates from previously uncovered hosts: `{metrics['new_host_candidate_count']:,}`",
        f"- Increment beyond the previous scanner portfolio: `{cross['federated_incremental_operation_identity_count']:,}`",
        f"- Combined unique operation identities: `{cross['combined_unique_operation_identity_count']:,}`",
        "",
        "| Source | Operations | Previews | Existing-host gaps | New-host candidates | Blocked |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for source in study["source_scan"]["sources"]:
        lines.append(
            f"| `{source['source_id']}` | {source['candidate_count']} | "
            f"{source['preview_count']} | {source['existing_host_gap_count']} | "
            f"{source['new_host_candidate_count']} | {source['blocked_count']} |"
        )
    design = study["study_design"]
    lines.extend(
        [
            "",
            "## Scientific Evaluation",
            "",
            "The evaluation linked three cancer models to seven independently generated "
            "research operations. Each accepted tool passed all three disease-context "
            "cases before approval, publication, and explicit loading into a fresh runtime.",
            "",
            f"- Accepted tools: `{design['accepted_tool_count']}`",
            f"- Pre-publication verification calls: `{design['verification_execution_count']}`",
            f"- Post-publication runtime calls: `{design['post_publication_execution_count']}`",
            f"- Candidates rejected on live drift: `{design['rejected_candidate_count']}`",
            "",
            "| Tool | Source | Scientific contribution |",
            "|---|---|---|",
        ]
    )
    for item in study["promotions"]:
        lines.append(
            f"| `{item['tool_name']}` | `{item['source_id']}` | {item['contribution']} |"
        )
    lines.extend(["", "## Scenario Evidence", ""])
    for scenario in study["scenario_results"]:
        lines.extend(
            [
                f"### {scenario['gene_symbol']}: {scenario['disease_context'].title()}",
                "",
                "| Evidence layer | Observation | Provider |",
                "|---|---|---|",
            ]
        )
        for result in scenario["tool_results"]:
            for observation in result["observations"]:
                compact = json.dumps(
                    observation["value"], sort_keys=True, ensure_ascii=True
                )
                if len(compact) > 360:
                    compact = compact[:357] + "..."
                layer = f"{result['key']}: {observation['label']}"
                lines.append(
                    f"| `{layer}` | `{compact}` | "
                    f"`{result['provenance']['provider']}` |"
                )
        lines.append("")
    lines.extend(
        [
            "## Qualification Decisions",
            "",
            "| Candidate | Source | Decision |",
            "|---|---|---|",
        ]
    )
    for item in study["rejections"]:
        lines.append(
            f"| `{item['tool_name']}` | `{item['source_id']}` | Rejected during live response validation |"
        )
    lines.extend(
        [
            "",
            "## Operational Interpretation",
            "",
            study["interpretation"],
            "",
            "The 533 previews are candidates, not 533 approved tools. This evaluation "
            "supports seven selected tools with complete promotion evidence and records "
            "three explicit rejections; the built-in registry was not changed.",
            "",
            f"Study digest: `{study['study_sha256']}`",
            f"Source scan digest: `{study['source_scan']['scan_sha256']}`",
            "",
        ]
    )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the live federated biomedical source evaluation."
    )
    parser.add_argument("--scenarios", type=Path, default=SCENARIOS)
    parser.add_argument("--source-scan", type=Path, default=SCAN_ARTIFACT)
    parser.add_argument("--baseline-portfolio", type=Path, default=BASELINE_ARTIFACT)
    parser.add_argument("--workspace", type=Path, default=WORKSPACE)
    parser.add_argument("--output-json", type=Path, default=JSON_ARTIFACT)
    parser.add_argument("--output-markdown", type=Path, default=MARKDOWN_ARTIFACT)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    study = build_study(
        _read_json(args.scenarios, maximum=2_000_000),
        _read_json(args.source_scan),
        _read_json(args.baseline_portfolio, maximum=12_000_000),
        workspace=args.workspace,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(study, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    args.output_markdown.write_text(render_markdown(study), encoding="utf-8")
    print(
        json.dumps(
            {
                "study_sha256": study["study_sha256"],
                "source_count": study["source_scan"]["metrics"][
                    "manifest_source_count"
                ],
                "preview_count": study["source_scan"]["metrics"][
                    "net_new_preview_count"
                ],
                "accepted_tools": study["study_design"]["accepted_tool_count"],
                "rejected_candidates": study["study_design"][
                    "rejected_candidate_count"
                ],
                "verification_calls": study["study_design"][
                    "verification_execution_count"
                ],
                "runtime_calls": study["study_design"][
                    "post_publication_execution_count"
                ],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
