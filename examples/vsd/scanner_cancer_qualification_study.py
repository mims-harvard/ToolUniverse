"""Qualify scanner-discovered operations in five live cancer evidence workflows."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Sequence
from urllib.parse import urlsplit

from tooluniverse import ToolUniverse
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

from examples.vsd.continuous_catalog_expansion_study import validate_portfolio

HERE = Path(__file__).resolve().parent
SCENARIOS = HERE / "scanner_cancer_studies" / "scenarios.json"
EXPANSION_ARTIFACT = HERE / "artifacts" / "continuous_catalog_expansion_study.json"
JSON_ARTIFACT = HERE / "artifacts" / "scanner_cancer_qualification_study.json"
MARKDOWN_ARTIFACT = HERE / "artifacts" / "scanner_cancer_qualification_study.md"
_RECORD_RE = re.compile(r"^smartapi:([0-9a-f]{32})$")
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


def _read_json(path: Path, *, maximum: int = 2_000_000) -> Any:
    if not path.is_file() or path.is_symlink() or path.stat().st_size > maximum:
        raise ValueError(f"Study input is missing or exceeds {maximum:,} bytes")
    return json.loads(path.read_text(encoding="utf-8"))


def _validated_manifest(value: Any) -> dict[str, Any]:
    if (
        not isinstance(value, dict)
        or value.get("format") != "vsd_scanner_cancer_scenarios_v1"
        or value.get("version") != 1
        or not isinstance(value.get("scientific_boundary"), str)
    ):
        raise ValueError("Cancer qualification manifest is invalid")
    scenarios = value.get("scenarios")
    accepted = value.get("accepted_operations")
    rejected = value.get("rejected_operations")
    if (
        not isinstance(scenarios, list)
        or len(scenarios) != 5
        or not isinstance(accepted, list)
        or len(accepted) < 3
        or not isinstance(rejected, list)
        or len(rejected) < 3
    ):
        raise ValueError("Cancer qualification populations are invalid")
    scenario_ids = [
        item.get("scenario_id") for item in scenarios if isinstance(item, dict)
    ]
    if len(scenario_ids) != 5 or len(set(scenario_ids)) != 5:
        raise ValueError("Cancer scenario identifiers are invalid")
    operation_keys: list[str] = []
    tool_names: list[str] = []
    for item in [*accepted, *rejected]:
        if not isinstance(item, dict) or not _RECORD_RE.fullmatch(
            str(item.get("record_id", ""))
        ):
            raise ValueError("Cancer operation record identity is invalid")
        operation_keys.append(str(item.get("key", "")))
        tool_names.append(str(item.get("tool_name", "")))
        if (
            not item.get("operation_id")
            or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{2,63}", item["tool_name"])
            or not isinstance(item.get("include_parameters"), list)
            or not isinstance(item.get("fixed_query"), dict)
        ):
            raise ValueError("Cancer operation definition is invalid")
    if (
        any(not key for key in operation_keys)
        or len(operation_keys) != len(set(operation_keys))
        or len(tool_names) != len(set(tool_names))
    ):
        raise ValueError("Cancer operation keys and names must be unique")
    return copy.deepcopy(value)


def _pointer(value: Any, pointer: str) -> Any:
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


def _arguments(definition: dict[str, Any], scenario: dict[str, Any]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    fields = definition.get("argument_fields")
    if not isinstance(fields, dict):
        raise ValueError("Accepted operation argument mapping is invalid")
    for argument, source in fields.items():
        if isinstance(source, str) and source in scenario:
            output[argument] = scenario[source]
        elif isinstance(source, dict) and set(source) == {"constant"}:
            output[argument] = source["constant"]
        else:
            raise ValueError(f"Argument mapping for {argument!r} is invalid")
    return output


def _expectation(
    definition: dict[str, Any], scenario: dict[str, Any]
) -> dict[str, Any]:
    source = definition.get("verification_expect")
    if not isinstance(source, dict):
        raise ValueError("Verification expectation is invalid")
    expectation = {
        "result_type": source.get("result_type", "object"),
        "required_fields": copy.deepcopy(source.get("required_fields", [])),
        "required_paths": copy.deepcopy(source.get("required_paths", [])),
        "equals": copy.deepcopy(source.get("equals", {})),
        "equals_paths": copy.deepcopy(source.get("equals_paths", {})),
        "equals_paths_casefold": copy.deepcopy(source.get("equals_paths_casefold", {})),
    }
    for pointer, field in source.get("equals_paths_from", {}).items():
        if field not in scenario:
            raise ValueError("Dynamic verification field is absent")
        expectation["equals_paths"][pointer] = scenario[field]
    if expectation["result_type"] == "array":
        expectation["min_items"] = source.get("min_items", 0)
        expectation["max_items"] = source.get("max_items", 100)
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


def _successful_data(response: Any, name: str) -> dict[str, Any]:
    if not isinstance(response, dict) or response.get("status") != "success":
        raise RuntimeError(f"Generated tool {name!r} failed: {response!r}")
    data = response.get("data")
    if (
        not isinstance(data, dict)
        or "result" not in data
        or not isinstance(data.get("provenance"), dict)
    ):
        raise RuntimeError(f"Generated tool {name!r} returned an invalid envelope")
    return data


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


def _candidate_inventory(
    expansion: dict[str, Any],
) -> dict[tuple[str, str], dict[str, Any]]:
    records = expansion.get("scientific_candidate_inventory")
    if not isinstance(records, list):
        raise ValueError("Expansion artifact lacks its scientific inventory")
    output: dict[tuple[str, str], dict[str, Any]] = {}
    for item in records:
        if not isinstance(item, dict):
            raise ValueError("Expansion scientific inventory is invalid")
        key = (item.get("record_id"), item.get("operation_id"))
        if key in output:
            raise ValueError("Expansion scientific inventory is ambiguous")
        output[key] = item
    return output


def _load_candidates(
    definitions: list[dict[str, Any]], expansion: dict[str, Any]
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], set[str]]:
    inventory = _candidate_inventory(expansion)
    fetched: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
    candidates: dict[str, dict[str, Any]] = {}
    provenance: dict[str, dict[str, Any]] = {}
    hosts: set[str] = set()
    for definition in definitions:
        record_id = definition["record_id"]
        operation_id = definition["operation_id"]
        recorded = inventory.get((record_id, operation_id))
        if recorded is None:
            raise ValueError(
                f"Scanner inventory lacks {record_id} operation {operation_id!r}"
            )
        if record_id not in fetched:
            registry_id = _RECORD_RE.fullmatch(record_id).group(1)
            specification_url = f"https://smart-api.info/api/metadata/{registry_id}"
            raw, request = _fetch_https(specification_url, 30, 10_000_000)
            with tempfile.TemporaryDirectory(
                prefix="tooluniverse-vsd-cancer-spec-"
            ) as directory:
                path = Path(directory) / "specification.json"
                path.write_bytes(raw)
                inspection = inspect_openapi_document(path)
            fetched[record_id] = (
                inspection,
                {
                    "specification_url": specification_url,
                    "status_code": request["status_code"],
                    "content_type": request["content_type"],
                    "response_bytes": request["response_bytes"],
                    "redirects": request["redirects"],
                    "source_document_sha256": inspection["source_document_sha256"],
                },
            )
        inspection, request = fetched[record_id]
        matches = [
            item
            for item in inspection["candidates"]
            if item["operation_id"] == operation_id
        ]
        if len(matches) != 1:
            raise ValueError("Live specification operation identity is ambiguous")
        candidate = matches[0]
        if (
            candidate["candidate_sha256"] != recorded["candidate_sha256"]
            or candidate["blockers"]
            or candidate["execution_allowed"] is not False
            or recorded.get("registry_coverage")
            not in {"candidate_gap", "existing_host_gap"}
            or recorded.get("existing_tools") != []
        ):
            raise ValueError("Live candidate no longer matches the scanner evidence")
        host = (urlsplit(candidate["server_url"]).hostname or "").casefold()
        if not host:
            raise ValueError("Live candidate server has no host")
        hosts.add(host)
        candidates[definition["key"]] = candidate
        provenance[definition["key"]] = {
            **request,
            "candidate_id": candidate["candidate_id"],
            "candidate_sha256": candidate["candidate_sha256"],
            "preview_config_sha256": recorded["preview_config_sha256"],
            "registry_coverage": recorded["registry_coverage"],
            "existing_tools": recorded["existing_tools"],
        }
    return candidates, provenance, hosts


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
    early_publication_error = ""
    try:
        publish_draft(draft["draft_id"], workspace=workspace)
    except VSDPromotionError as exc:
        early_publication_error = str(exc)
    if not early_publication_error:
        raise AssertionError("Unverified scanner candidate was published")
    evidence = verify_draft(
        draft["draft_id"],
        _verification_cases(definition, scenarios),
        workspace=workspace,
    )
    approval = approve_draft(
        draft["draft_id"],
        reviewed_by="VSD scanner cancer portfolio reviewer",
        decision_note=(
            "Approved after all five cancer scenarios passed the reviewed input, "
            "response, HTTPS, redirect, and provenance checks."
        ),
        workspace=workspace,
    )
    publication = publish_draft(draft["draft_id"], workspace=workspace)
    return {
        "key": definition["key"],
        "tool_name": definition["tool_name"],
        "draft_id": draft["draft_id"],
        "operation_sha256": draft["operation_sha256"],
        "draft_sha256": draft["draft_sha256"],
        "verification_sha256": evidence["verification_sha256"],
        "approval_sha256": approval["approval_sha256"],
        "publication_sha256": publication["publication_sha256"],
        "verification_case_count": evidence["case_count"],
        "verified_at": evidence["verified_at"],
        "verification_cases": evidence["cases"],
        "early_publication_blocked": True,
        "early_publication_error": early_publication_error,
        "interpretation": definition["interpretation"],
    }


def _qualify_rejection(
    definition: dict[str, Any], candidate: dict[str, Any], workspace: Path
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
    case = {
        "arguments": definition["arguments"],
        "expect": _expectation(definition, {}),
    }
    verification_error = ""
    try:
        verify_draft(draft["draft_id"], [case, case, case], workspace=workspace)
    except VSDPromotionError as exc:
        verification_error = str(exc)
    expected = definition["expected_error_substring"]
    if expected not in verification_error:
        raise AssertionError(
            f"Rejected operation {definition['key']!r} failed unexpectedly: "
            f"{verification_error!r}"
        )
    approval_error = ""
    try:
        approve_draft(
            draft["draft_id"],
            reviewed_by="VSD scanner cancer portfolio reviewer",
            decision_note="This candidate should remain blocked after failed verification.",
            workspace=workspace,
        )
    except VSDPromotionError as exc:
        approval_error = str(exc)
    publication_error = ""
    try:
        publish_draft(draft["draft_id"], workspace=workspace)
    except VSDPromotionError as exc:
        publication_error = str(exc)
    if not approval_error or not publication_error:
        raise AssertionError("Rejected scanner candidate crossed a promotion gate")
    return {
        "key": definition["key"],
        "tool_name": definition["tool_name"],
        "candidate_sha256": candidate["candidate_sha256"],
        "draft_sha256": draft["draft_sha256"],
        "decision": "rejected_at_live_verification",
        "failure_summary": definition["failure_summary"],
        "verification_error": verification_error[:1000],
        "approval_blocked": True,
        "approval_error": approval_error,
        "publication_blocked": True,
        "publication_error": publication_error,
    }


def _observations(result: Any, definition: dict[str, Any]) -> list[dict[str, Any]]:
    output = []
    for item in definition.get("observations", []):
        value = _pointer(result, item["pointer"])
        full_count = len(value) if isinstance(value, list) else None
        if isinstance(value, list) and "limit" in item:
            value = value[: item["limit"]]
        fields = item.get("fields")
        if isinstance(fields, list):
            if not isinstance(value, list) or any(
                not isinstance(row, dict) for row in value
            ):
                raise ValueError("Field projection requires an array of objects")
            value = [{field: row.get(field) for field in fields} for row in value]
        output.append(
            {
                "label": item["label"],
                "pointer": item["pointer"],
                "full_count": full_count,
                "display_fields": fields or [],
                "value": value,
            }
        )
    return output


def _runtime_call(
    runtime: ToolUniverse,
    definition: dict[str, Any],
    scenario: dict[str, Any],
) -> dict[str, Any]:
    arguments = _arguments(definition, scenario)
    data = _successful_data(
        runtime.run_one_function(
            {"name": definition["tool_name"], "arguments": arguments},
            use_cache=False,
        ),
        definition["tool_name"],
    )
    provenance = data["provenance"]
    return {
        "key": definition["key"],
        "tool_name": definition["tool_name"],
        "arguments": arguments,
        "observations": _observations(data["result"], definition),
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
    manifest: Any,
    expansion_artifact: Any,
    *,
    workspace: Path,
) -> dict[str, Any]:
    scenarios_manifest = _validated_manifest(manifest)
    expansion = validate_portfolio(expansion_artifact)
    scenarios = scenarios_manifest["scenarios"]
    accepted = scenarios_manifest["accepted_operations"]
    rejected = scenarios_manifest["rejected_operations"]
    candidates, source_evidence, hosts = _load_candidates(
        [*accepted, *rejected], expansion
    )
    accepted_workspace = workspace / "accepted"
    rejected_workspace = workspace / "rejected"
    promotions = []
    rejection_results = []
    with _allowed_hosts(hosts):
        for definition in accepted:
            promotions.append(
                _promote(
                    definition,
                    candidates[definition["key"]],
                    scenarios,
                    accepted_workspace,
                )
            )
        for definition in rejected:
            rejection_results.append(
                _qualify_rejection(
                    definition,
                    candidates[definition["key"]],
                    rejected_workspace / definition["key"],
                )
            )

        runtime = ToolUniverse()
        try:
            names = [item["tool_name"] for item in accepted]
            absent_before_load = all(
                name not in runtime.all_tool_dict for name in names
            )
            loaded = load_published_tools(runtime, workspace=accepted_workspace)
            studies = [
                {
                    **scenario,
                    "calls": [
                        _runtime_call(runtime, definition, scenario)
                        for definition in accepted
                    ],
                }
                for scenario in scenarios
            ]
        finally:
            runtime.close()

    call_count = sum(len(item["calls"]) for item in studies)
    payload_hashes: dict[str, set[str]] = {item["key"]: set() for item in accepted}
    for study in studies:
        for call in study["calls"]:
            payload_hashes[call["key"]].add(call["provenance"]["payload_sha256"])
    assertions = {
        "exhaustive_source_scan_passed": all(expansion["assertions"].values()),
        "all_selected_operations_were_exact_registry_gaps": all(
            value["registry_coverage"] in {"candidate_gap", "existing_host_gap"}
            and value["existing_tools"] == []
            for value in source_evidence.values()
        ),
        "four_operations_passed_five_case_verification": len(promotions) == 4
        and all(item["verification_case_count"] == 5 for item in promotions),
        "unverified_publication_was_blocked": all(
            item["early_publication_blocked"] for item in promotions
        ),
        "accepted_hash_chains_are_complete": all(
            all(
                re.fullmatch(r"[0-9a-f]{64}", item[field])
                for field in (
                    "operation_sha256",
                    "draft_sha256",
                    "verification_sha256",
                    "approval_sha256",
                    "publication_sha256",
                )
            )
            for item in promotions
        ),
        "published_tools_were_absent_then_loaded_into_a_fresh_runtime": (
            absent_before_load
            and set(loaded) == {item["tool_name"] for item in accepted}
        ),
        "twenty_live_runtime_calls_succeeded": call_count == 20,
        "all_runtime_calls_have_zero_redirect_https_provenance": all(
            call["provenance"]["endpoint"].startswith("https://")
            and call["provenance"]["http_status"] == 200
            and call["provenance"]["redirects"] == 0
            and call["provenance"]["method"] == "GET"
            for study in studies
            for call in study["calls"]
        ),
        "each_tool_returned_five_distinct_payloads": all(
            len(values) == 5 for values in payload_hashes.values()
        ),
        "four_static_candidates_were_rejected_by_live_gates": len(rejection_results)
        == 4
        and all(
            item["decision"] == "rejected_at_live_verification"
            and item["approval_blocked"]
            and item["publication_blocked"]
            for item in rejection_results
        ),
    }
    body = {
        "format": "vsd_scanner_cancer_qualification_study_v1",
        "version": 1,
        "evaluation_mode": "live_network",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "objective": (
            "Test whether an exhaustive VSD catalog scan can identify exact missing "
            "operations, promote only candidates that pass representative live "
            "verification, and use the resulting tools in five cancer evidence workflows."
        ),
        "method": (
            "The data-driven manifest selected eight inert scanner candidates. Four "
            "passed five-case verification, explicit approval, publication, fresh-runtime "
            "loading, and twenty post-publication calls. Four other statically draft-ready "
            "candidates were withheld when live provider responses violated their "
            "published schemas."
        ),
        "scientific_boundary": scenarios_manifest["scientific_boundary"],
        "expansion_evidence": {
            "portfolio_sha256": expansion["portfolio_sha256"],
            **{
                key: expansion["combined_results"][key]
                for key in (
                    "catalog_record_count",
                    "processed_record_count",
                    "unique_operation_count",
                    "unique_draft_ready_count",
                    "scientific_draft_ready_count",
                    "blocked_operation_count",
                )
            },
        },
        "source_evidence": source_evidence,
        "promotions": promotions,
        "rejections": rejection_results,
        "studies": studies,
        "comparison": {
            "without_vsd": (
                "The exact eight catalog operations were absent from the audited "
                "ToolUniverse registry. Using them would require separate HTTP integration, "
                "schema handling, provenance capture, and maintenance, and static contract "
                "inspection alone would not reveal the four live response failures."
            ),
            "with_vsd": (
                "The scanner supplied a hashed candidate inventory; promotion gates "
                "accepted four operations, rejected four, loaded the accepted tools "
                "explicitly, and retained operation and payload hashes for every call."
            ),
            "measured_value": (
                "VSD closed four exact capability gaps for five reproducible workflows "
                "without weakening ToolUniverse's registry, verification, approval, or "
                "runtime boundaries. The result is broader governed access, not a claim of "
                "improved clinical truth."
            ),
        },
        "assertions": assertions,
    }
    if not all(assertions.values()):
        failed = sorted(key for key, result in assertions.items() if not result)
        raise AssertionError(f"Cancer qualification assertions failed: {failed!r}")
    return {**body, "study_sha256": _digest(body)}


def validate_study(value: Any) -> dict[str, Any]:
    if (
        not isinstance(value, dict)
        or value.get("format") != "vsd_scanner_cancer_qualification_study_v1"
    ):
        raise ValueError("Scanner cancer qualification artifact is invalid")
    body = {key: item for key, item in value.items() if key != "study_sha256"}
    if value.get("study_sha256") != _digest(body):
        raise ValueError("Scanner cancer qualification digest does not match")
    assertions = value.get("assertions")
    if not isinstance(assertions, dict) or not all(assertions.values()):
        raise ValueError("Scanner cancer qualification assertions did not pass")
    return copy.deepcopy(value)


def _display(value: Any, fields: list[str] | None = None) -> str:
    if isinstance(value, list):
        if not value:
            return "No values returned"
        rendered = []
        for item in value:
            if isinstance(item, dict):
                keys = fields or sorted(item)
                rendered.append(
                    ", ".join(f"{key}={item[key]}" for key in keys if key in item)
                )
            else:
                rendered.append(str(item))
        return "; ".join(rendered)
    if isinstance(value, dict):
        keys = fields or sorted(value)
        return ", ".join(f"{key}={value[key]}" for key in keys if key in value)
    return str(value)


def render_markdown(value: Any) -> str:
    study = validate_study(value)
    scale = study["expansion_evidence"]
    lines = [
        "# Scanner-Discovered Cancer Evidence Qualification",
        "",
        "## Objective",
        "",
        study["objective"],
        "",
        "## Catalog scale",
        "",
        "| Measure | Result |",
        "| --- | ---: |",
        f"| Catalog records | {scale['catalog_record_count']:,} |",
        f"| Compatible records processed | {scale['processed_record_count']:,} |",
        f"| Unique operations inventoried | {scale['unique_operation_count']:,} |",
        f"| Unique draft-ready candidates | {scale['unique_draft_ready_count']:,} |",
        f"| Scientific draft-ready candidates | {scale['scientific_draft_ready_count']:,} |",
        f"| Blocked operations | {scale['blocked_operation_count']:,} |",
        "",
        "## Qualification results",
        "",
        "Four exact registry gaps passed five representative calls each before "
        "approval and publication. Four other candidates were withheld after live "
        "response-schema verification failed.",
        "",
        "| Decision | Operation | Evidence |",
        "| --- | --- | --- |",
    ]
    for item in study["promotions"]:
        lines.append(
            f"| Accepted | `{item['tool_name']}` | "
            f"{item['verification_case_count']} verification cases; "
            f"publication `{item['publication_sha256'][:12]}` |"
        )
    for item in study["rejections"]:
        reason = item["failure_summary"].replace("|", "\\|")
        lines.append(f"| Rejected | `{item['tool_name']}` | {reason} |")
    lines.extend(["", "## Five evidence workflows", ""])
    for case in study["studies"]:
        lines.extend(
            [
                f"### {case['disease_name']}: {case['gene_symbol']}",
                "",
                case["question"],
                "",
                f"Controlled disease identifier: `{case['mesh_id']}` "
                f"([NLM MeSH record]({case['mesh_reference']})).",
                "",
                "| Evidence role | Observation | Provider evidence |",
                "| --- | --- | --- |",
            ]
        )
        for call in case["calls"]:
            observation = "<br>".join(
                f"{item['label']}: "
                f"{_display(item['value'], item.get('display_fields'))}"
                for item in call["observations"]
            ).replace("|", "\\|")
            provenance = call["provenance"]
            lines.append(
                f"| `{call['key']}` | {observation} | "
                f"`{provenance['provider']}`; payload "
                f"`{provenance['payload_sha256'][:12]}` |"
            )
        lines.append("")
    lines.extend(
        [
            "## Comparison",
            "",
            f"**Without VSD.** {study['comparison']['without_vsd']}",
            "",
            f"**With VSD.** {study['comparison']['with_vsd']}",
            "",
            f"**Measured contribution.** {study['comparison']['measured_value']}",
            "",
            "## Scientific interpretation",
            "",
            study["scientific_boundary"],
            "",
            "COHD results are terminology matches from deidentified aggregate data, "
            "HuBMAP relationships support symbol normalization, CFDE values are linked-record "
            "counts, and OpenPredict outputs are computational hypotheses. These sources are "
            "not interchangeable and are not combined into a clinical score.",
            "",
            f"Study SHA-256: `{study['study_sha256']}`.",
            "",
        ]
    )
    return "\n".join(lines)


def write_artifacts(
    study: Any,
    *,
    json_path: Path = JSON_ARTIFACT,
    markdown_path: Path = MARKDOWN_ARTIFACT,
) -> tuple[Path, Path]:
    checked = validate_study(study)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(checked, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(render_markdown(checked), encoding="utf-8")
    return json_path, markdown_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Qualify scanner-discovered tools in five live cancer workflows."
    )
    parser.add_argument("--scenarios", type=Path, default=SCENARIOS)
    parser.add_argument("--expansion-artifact", type=Path, default=EXPANSION_ARTIFACT)
    parser.add_argument("--workspace", type=Path)
    parser.add_argument("--json-output", type=Path, default=JSON_ARTIFACT)
    parser.add_argument("--markdown-output", type=Path, default=MARKDOWN_ARTIFACT)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    manifest = _read_json(arguments.scenarios)
    expansion = _read_json(arguments.expansion_artifact)
    if arguments.workspace is None:
        with tempfile.TemporaryDirectory(
            prefix="tooluniverse-vsd-scanner-cancer-"
        ) as directory:
            study = build_study(manifest, expansion, workspace=Path(directory))
    else:
        study = build_study(manifest, expansion, workspace=arguments.workspace)
    json_path, markdown_path = write_artifacts(
        study,
        json_path=arguments.json_output,
        markdown_path=arguments.markdown_output,
    )
    print(
        json.dumps(
            {
                "json_artifact": str(json_path),
                "markdown_artifact": str(markdown_path),
                "study_sha256": study["study_sha256"],
                "accepted_operation_count": len(study["promotions"]),
                "rejected_operation_count": len(study["rejections"]),
                "runtime_call_count": sum(
                    len(item["calls"]) for item in study["studies"]
                ),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
