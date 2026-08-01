"""Exercise OpenAPI drift and publication lifecycle controls end to end."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from tooluniverse import ToolUniverse, vsd_dynamic_rest, vsd_promotion
from tooluniverse.vsd_lifecycle import (
    VSDLifecycleError,
    assess_openapi_drift,
    list_publication_states,
    set_publication_state,
)
from tooluniverse.vsd_openapi import inspect_openapi_document

HERE = Path(__file__).resolve().parent
ARTIFACTS = HERE / "artifacts"
DEFAULT_JSON = ARTIFACTS / "lifecycle_drift_snapshot.json"
DEFAULT_MARKDOWN = ARTIFACTS / "lifecycle_drift_snapshot.md"

ENV_VAR = "TOOLUNIVERSE_VSD_LIFECYCLE_CASE_KEY"
TOOL_NAME = "VSDLifecycleRareDiseaseEvidence"
RECORDS = {
    "RD-ALS": {
        "record_id": "RD-ALS",
        "disease": "Amyotrophic lateral sclerosis",
        "genes": ["C9orf72", "SOD1", "TARDBP"],
        "phenotypes": ["Muscle weakness", "Motor neuron degeneration"],
        "trials": ["NCT05163886", "NCT05619783"],
    },
    "RD-DMD": {
        "record_id": "RD-DMD",
        "disease": "Duchenne muscular dystrophy",
        "genes": ["DMD"],
        "phenotypes": ["Progressive muscle weakness", "Elevated creatine kinase"],
        "trials": ["NCT05096221", "NCT05429372"],
    },
    "RD-SMA": {
        "record_id": "RD-SMA",
        "disease": "Spinal muscular atrophy",
        "genes": ["SMN1", "SMN2"],
        "phenotypes": ["Hypotonia", "Proximal muscle weakness"],
        "trials": ["NCT05337553", "NCT05794139"],
    },
}
EXPECTED_ASSERTIONS = {
    "active_publication_executes_after_repair",
    "all_assessments_are_inert_and_hash_bound",
    "breaking_auth_drift_is_blocked",
    "breaking_endpoint_drift_recommends_suspension",
    "credential_environment_is_restored",
    "credential_rotation_preserves_operation_identity",
    "exact_contract_is_unchanged",
    "explicit_suspension_prevents_fresh_loading",
    "lifecycle_events_form_a_hash_chain",
    "metadata_drift_does_not_recommend_suspension",
    "publication_anchor_matches_current_history",
    "response_drift_requires_new_review",
    "retired_publication_cannot_be_loaded",
    "retirement_is_terminal",
    "secret_values_are_absent_from_artifacts",
    "state_does_not_change_during_assessment",
    "tampered_lifecycle_fails_before_registration",
    "three_protected_verification_cases_pass",
    "unchanged_repair_supports_explicit_activation",
}


def _digest(value: Any) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _secret(label: str) -> str:
    return hashlib.sha256(f"vsd-lifecycle:{label}".encode()).hexdigest()


def _specification(
    *,
    version: str = "1.0.0",
    summary: str = "Retrieve one protected rare-disease evidence record",
    server_url: str = "https://rare-registry.example.org/v1",
    auth_location: str = "header",
    require_evidence_level: bool = False,
) -> dict[str, Any]:
    properties: dict[str, Any] = {
        "record_id": {"type": "string"},
        "disease": {"type": "string"},
        "genes": {"type": "array", "items": {"type": "string"}},
        "phenotypes": {"type": "array", "items": {"type": "string"}},
        "trials": {"type": "array", "items": {"type": "string"}},
    }
    required = ["record_id", "disease", "genes", "phenotypes", "trials"]
    if require_evidence_level:
        properties["evidence_level"] = {"type": "string", "enum": ["reviewed"]}
        required.append("evidence_level")
    return {
        "openapi": "3.1.0",
        "info": {"title": "Protected Rare Disease Registry", "version": version},
        "servers": [{"url": server_url}],
        "security": [{"registryKey": []}],
        "paths": {
            "/evidence/{recordId}": {
                "get": {
                    "operationId": "getRareDiseaseEvidence",
                    "summary": summary,
                    "parameters": [
                        {
                            "name": "recordId",
                            "in": "path",
                            "required": True,
                            "schema": {
                                "type": "string",
                                "pattern": "^RD-(?:ALS|DMD|SMA)$",
                            },
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Rare-disease evidence record",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": properties,
                                        "required": required,
                                        "additionalProperties": False,
                                    }
                                }
                            },
                        }
                    },
                }
            }
        },
        "components": {
            "securitySchemes": {
                "registryKey": {
                    "type": "apiKey",
                    "in": auth_location,
                    "name": (
                        "X-Rare-Disease-Key"
                        if auth_location == "header"
                        else "registry_key"
                    ),
                }
            }
        },
    }


def _write_spec(workspace: Path, name: str, specification: dict[str, Any]) -> Path:
    path = workspace / "provider-contracts" / f"{name}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(specification, indent=2, sort_keys=True), encoding="utf-8"
    )
    return path


def _cases() -> list[dict[str, Any]]:
    return [
        {
            "arguments": {"recordId": record_id},
            "expect": {
                "result_type": "object",
                "required_fields": [
                    "record_id",
                    "disease",
                    "genes",
                    "phenotypes",
                    "trials",
                ],
                "equals": {"record_id": record_id},
                "required_paths": ["/genes/0", "/phenotypes/0", "/trials/0"],
                "equals_paths": {},
            },
        }
        for record_id in RECORDS
    ]


def run_case(workspace: Path) -> dict[str, Any]:
    workspace = Path(workspace)
    baseline_path = _write_spec(workspace, "baseline", _specification())
    metadata_path = _write_spec(
        workspace,
        "metadata-only",
        _specification(
            version="1.0.1", summary="Retrieve one curated rare-disease record"
        ),
    )
    response_path = _write_spec(
        workspace,
        "response-review",
        _specification(require_evidence_level=True),
    )
    endpoint_path = _write_spec(
        workspace,
        "breaking-endpoint",
        _specification(server_url="https://rare-registry.example.org/v2"),
    )
    auth_path = _write_spec(
        workspace,
        "blocked-query-auth",
        _specification(auth_location="query"),
    )
    initial_secret = _secret("initial")
    rotated_secret = _secret("rotated")
    secrets = (initial_secret, rotated_secret)
    previous_environment = os.environ.get(ENV_VAR)
    original_transport = vsd_dynamic_rest._safe_get_json
    transport_log: list[dict[str, Any]] = []

    def fake_transport(url, params, *, timeout, headers):
        secret = headers.get("X-Rare-Disease-Key")
        slot = {initial_secret: "initial", rotated_secret: "rotated"}.get(secret)
        if slot is None or set(headers) != {"X-Rare-Disease-Key"}:
            raise AssertionError("transport did not receive the reviewed credential")
        record_id = url.rsplit("/", 1)[-1]
        transport_log.append(
            {
                "credential_slot": slot,
                "record_id": record_id,
                "endpoint_version": url.split("/")[-3],
                "params": dict(params),
                "timeout": timeout,
            }
        )
        payload = copy.deepcopy(RECORDS[record_id])
        return payload, {
            "status_code": 200,
            "content_type": "application/json",
            "response_bytes": len(json.dumps(payload).encode()),
            "redirects": 0,
        }

    tamper_error = ""
    terminal_error = ""
    try:
        os.environ[ENV_VAR] = initial_secret
        vsd_dynamic_rest._safe_get_json = fake_transport
        report = inspect_openapi_document(baseline_path)
        candidate = report["candidates"][0]
        draft = vsd_promotion.create_openapi_draft(
            candidate,
            tool_name=TOOL_NAME,
            description="Retrieve one reviewed protected rare-disease evidence record.",
            include_parameters=["recordId"],
            credential_env=ENV_VAR,
            workspace=workspace,
        )
        evidence = vsd_promotion.verify_draft(
            draft["draft_id"], _cases(), workspace=workspace
        )
        approval = vsd_promotion.approve_draft(
            draft["draft_id"],
            reviewed_by="Lifecycle Case Study Reviewer",
            decision_note=(
                "Approved after three protected rare-disease records passed."
            ),
            workspace=workspace,
        )
        publication = vsd_promotion.publish_draft(
            draft["draft_id"], workspace=workspace
        )

        assessments = {
            "unchanged": assess_openapi_drift(
                TOOL_NAME, baseline_path, workspace=workspace
            ),
            "metadata_only": assess_openapi_drift(
                TOOL_NAME, metadata_path, workspace=workspace
            ),
            "review_required": assess_openapi_drift(
                TOOL_NAME, response_path, workspace=workspace
            ),
            "breaking_endpoint": assess_openapi_drift(
                TOOL_NAME, endpoint_path, workspace=workspace
            ),
            "breaking_auth": assess_openapi_drift(
                TOOL_NAME, auth_path, workspace=workspace
            ),
        }
        state_after_assessment = list_publication_states(
            TOOL_NAME, workspace=workspace
        )["tools"][0]
        suspended = set_publication_state(
            TOOL_NAME,
            "suspended",
            changed_by="Lifecycle Case Study Reviewer",
            reason="Suspended after the provider endpoint changed major versions.",
            assessment_sha256=assessments["breaking_endpoint"]["assessment_sha256"],
            workspace=workspace,
        )

        suspended_universe = ToolUniverse()
        try:
            suspended_loaded = vsd_promotion.load_published_tools(
                suspended_universe, workspace=workspace
            )
            suspended_present = TOOL_NAME in suspended_universe.all_tool_dict
        finally:
            suspended_universe.close()

        lifecycle_directory = (
            workspace / "lifecycle" / TOOL_NAME / publication["publication_sha256"]
        )
        event_path = lifecycle_directory / "events" / "000001.json"
        original_event = event_path.read_bytes()
        changed_event = json.loads(original_event)
        changed_event["reason"] = "tampered lifecycle reason"
        event_path.write_text(json.dumps(changed_event), encoding="utf-8")
        tampered_universe = ToolUniverse()
        try:
            try:
                vsd_promotion.load_published_tools(
                    tampered_universe, workspace=workspace
                )
            except VSDLifecycleError as exc:
                tamper_error = str(exc)
            tampered_present = TOOL_NAME in tampered_universe.all_tool_dict
        finally:
            tampered_universe.close()
            event_path.write_bytes(original_event)

        repaired = assess_openapi_drift(TOOL_NAME, baseline_path, workspace=workspace)
        activated = set_publication_state(
            TOOL_NAME,
            "active",
            changed_by="Lifecycle Case Study Reviewer",
            reason="Restored after the original reviewed provider contract was confirmed.",
            assessment_sha256=repaired["assessment_sha256"],
            workspace=workspace,
        )
        active_universe = ToolUniverse()
        try:
            active_loaded = vsd_promotion.load_published_tools(
                active_universe, workspace=workspace
            )
            initial_result = active_universe.run_one_function(
                {"name": TOOL_NAME, "arguments": {"recordId": "RD-DMD"}},
                use_cache=False,
            )
            operation_sha256 = initial_result["data"]["provenance"]["operation_sha256"]
            os.environ[ENV_VAR] = rotated_secret
            rotated_result = active_universe.run_one_function(
                {"name": TOOL_NAME, "arguments": {"recordId": "RD-SMA"}},
                use_cache=False,
            )
        finally:
            active_universe.close()

        retired = set_publication_state(
            TOOL_NAME,
            "retired",
            changed_by="Lifecycle Case Study Reviewer",
            reason="Retired after the protected registry integration was decommissioned.",
            workspace=workspace,
        )
        retired_universe = ToolUniverse()
        try:
            retired_loaded = vsd_promotion.load_published_tools(
                retired_universe, workspace=workspace
            )
            retired_present = TOOL_NAME in retired_universe.all_tool_dict
        finally:
            retired_universe.close()
        try:
            set_publication_state(
                TOOL_NAME,
                "active",
                changed_by="Lifecycle Case Study Reviewer",
                reason="A retired publication must not return to active service.",
                workspace=workspace,
            )
        except VSDLifecycleError as exc:
            terminal_error = str(exc)
    finally:
        vsd_dynamic_rest._safe_get_json = original_transport
        if previous_environment is None:
            os.environ.pop(ENV_VAR, None)
        else:
            os.environ[ENV_VAR] = previous_environment

    persisted_text = "\n".join(
        path.read_text(encoding="utf-8") for path in workspace.rglob("*.json")
    )
    result_text = json.dumps(
        {"initial": initial_result, "rotated": rotated_result}, sort_keys=True
    )
    events = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted((lifecycle_directory / "events").glob("*.json"))
    ]
    lifecycle_state = json.loads(
        (lifecycle_directory / "state.json").read_text(encoding="utf-8")
    )
    assertions = {
        "three_protected_verification_cases_pass": (
            evidence["all_cases_passed"] is True and evidence["case_count"] == 3
        ),
        "exact_contract_is_unchanged": (
            assessments["unchanged"]["classification"] == "unchanged"
            and assessments["unchanged"]["changes"] == []
        ),
        "metadata_drift_does_not_recommend_suspension": (
            assessments["metadata_only"]["classification"] == "metadata_only"
            and assessments["metadata_only"]["suspension_recommended"] is False
        ),
        "response_drift_requires_new_review": (
            assessments["review_required"]["classification"] == "review_required"
            and assessments["review_required"]["changes"] == ["response_validation"]
            and assessments["review_required"]["suspension_recommended"] is True
        ),
        "breaking_endpoint_drift_recommends_suspension": (
            assessments["breaking_endpoint"]["classification"] == "breaking"
            and assessments["breaking_endpoint"]["changes"] == ["endpoint"]
            and assessments["breaking_endpoint"]["suspension_recommended"] is True
        ),
        "breaking_auth_drift_is_blocked": (
            assessments["breaking_auth"]["classification"] == "breaking"
            and "authentication_required" in assessments["breaking_auth"]["blockers"]
        ),
        "all_assessments_are_inert_and_hash_bound": all(
            item["execution_allowed"] is False
            and len(item["assessment_sha256"]) == 64
            and item["assessment_id"] == item["assessment_sha256"][:16]
            for item in [*assessments.values(), repaired]
        ),
        "state_does_not_change_during_assessment": (
            state_after_assessment["state"] == "active"
            and state_after_assessment["revision"] == 0
        ),
        "explicit_suspension_prevents_fresh_loading": (
            suspended["state"] == "suspended"
            and suspended_loaded == []
            and suspended_present is False
        ),
        "tampered_lifecycle_fails_before_registration": (
            "modified" in tamper_error and tampered_present is False
        ),
        "unchanged_repair_supports_explicit_activation": (
            repaired["classification"] == "unchanged"
            and activated["state"] == "active"
            and activated["assessment_sha256"] == repaired["assessment_sha256"]
        ),
        "active_publication_executes_after_repair": (
            active_loaded == [TOOL_NAME]
            and initial_result["status"] == "success"
            and initial_result["data"]["result"]["record_id"] == "RD-DMD"
        ),
        "credential_rotation_preserves_operation_identity": (
            rotated_result["data"]["result"]["record_id"] == "RD-SMA"
            and rotated_result["data"]["provenance"]["operation_sha256"]
            == operation_sha256
            and transport_log[-1]["credential_slot"] == "rotated"
        ),
        "retired_publication_cannot_be_loaded": (
            retired["state"] == "retired"
            and retired_loaded == []
            and retired_present is False
        ),
        "retirement_is_terminal": (
            "Cannot transition publication from 'retired' to 'active'" in terminal_error
        ),
        "lifecycle_events_form_a_hash_chain": (
            len(events) == 3
            and events[0]["previous_event_sha256"] is None
            and events[1]["previous_event_sha256"] == events[0]["event_sha256"]
            and events[2]["previous_event_sha256"] == events[1]["event_sha256"]
            and [event["revision"] for event in events] == [1, 2, 3]
        ),
        "publication_anchor_matches_current_history": (
            publication["lifecycle"]["anchor_id"] == lifecycle_state["anchor_id"]
            and lifecycle_state["publication_sha256"]
            == publication["publication_sha256"]
            and lifecycle_state["revision"] == 3
            and lifecycle_state["state"] == "retired"
            and lifecycle_state["current_event_sha256"] == events[-1]["event_sha256"]
        ),
        "secret_values_are_absent_from_artifacts": all(
            secret not in persisted_text and secret not in result_text
            for secret in secrets
        ),
        "credential_environment_is_restored": (
            os.environ.get(ENV_VAR) == previous_environment
        ),
    }
    snapshot = {
        "title": "Protected Rare-Disease Provider Drift And Lifecycle Case Study",
        "question": (
            "Can ToolUniverse distinguish harmless provider documentation changes "
            "from contract drift and keep unsafe publications out of fresh runtimes?"
        ),
        "answer": (
            "Yes. Six inert assessments distinguished unchanged, metadata-only, "
            "review-required, and breaking contracts; explicit hash-bound state "
            "events controlled loading without modifying the approved publication."
        ),
        "provider_fixture": (
            "A deterministic protected rare-disease provider replaces network "
            "transport. Inspection, promotion, verification, credential handling, "
            "lifecycle validation, fresh loading, and execution use production paths."
        ),
        "promotion": {
            "draft_id": draft["draft_id"],
            "draft_sha256": draft["draft_sha256"],
            "verification_sha256": evidence["verification_sha256"],
            "approval_sha256": approval["approval_sha256"],
            "publication_sha256": publication["publication_sha256"],
            "operation_sha256": publication["operation_sha256"],
            "verification_case_count": evidence["case_count"],
        },
        "drift_assessments": {
            name: {
                "assessment_id": item["assessment_id"],
                "assessment_sha256": item["assessment_sha256"],
                "classification": item["classification"],
                "changes": item["changes"],
                "blockers": item["blockers"],
                "suspension_recommended": item["suspension_recommended"],
            }
            for name, item in {**assessments, "repaired": repaired}.items()
        },
        "lifecycle": {
            "anchor_id": lifecycle_state["anchor_id"],
            "state_sha256": lifecycle_state["state_sha256"],
            "states": [event["state"] for event in events],
            "event_sha256": [event["event_sha256"] for event in events],
            "assessment_sha256": [event["assessment_sha256"] for event in events],
            "suspended_loaded_tools": suspended_loaded,
            "active_loaded_tools": active_loaded,
            "retired_loaded_tools": retired_loaded,
            "tamper_error": tamper_error,
            "terminal_error": terminal_error,
        },
        "runtime": {
            "initial_record_id": initial_result["data"]["result"]["record_id"],
            "rotated_record_id": rotated_result["data"]["result"]["record_id"],
            "operation_sha256_before_rotation": operation_sha256,
            "operation_sha256_after_rotation": rotated_result["data"]["provenance"][
                "operation_sha256"
            ],
            "transport_log": transport_log,
        },
        "secret_boundary": {
            "persisted_secret_count": sum(
                secret in persisted_text for secret in secrets
            ),
            "result_secret_count": sum(secret in result_text for secret in secrets),
            "persisted_reference": ENV_VAR,
        },
        "end_to_end_assertions": assertions,
    }
    snapshot["audit_sha256"] = _digest(
        {
            key: value
            for key, value in snapshot.items()
            if key not in {"title", "question", "answer", "audit_sha256"}
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
            key: value
            for key, value in snapshot.items()
            if key not in {"title", "question", "answer", "audit_sha256"}
        }
    )
    if snapshot.get("audit_sha256") != expected:
        raise ValueError("Snapshot audit digest does not match its content")


def _markdown(snapshot: dict[str, Any]) -> str:
    promotion = snapshot["promotion"]
    assessments = snapshot["drift_assessments"]
    lifecycle = snapshot["lifecycle"]
    lines = [
        "# Protected Rare-Disease Provider Drift And Lifecycle Case Study",
        "",
        "## Decision Question",
        "",
        snapshot["question"],
        "",
        f"**Result:** {snapshot['answer']}",
        "",
        "## Provider Boundary",
        "",
        snapshot["provider_fixture"],
        "",
        "## Reviewed Publication",
        "",
        "The baseline protected operation passed three disease-specific cases before "
        "approval. The publication remains immutable throughout every lifecycle "
        "transition.",
        "",
        "| Evidence | SHA-256 |",
        "| --- | --- |",
        f"| Draft | `{promotion['draft_sha256']}` |",
        f"| Verification | `{promotion['verification_sha256']}` |",
        f"| Approval | `{promotion['approval_sha256']}` |",
        f"| Publication | `{promotion['publication_sha256']}` |",
        "",
        "## Drift Classification",
        "",
        "| Contract | Classification | Changes or blockers | Suspend? |",
        "| --- | --- | --- | --- |",
    ]
    for name, item in assessments.items():
        evidence = item["changes"] or item["blockers"] or ["none"]
        lines.append(
            f"| `{name}` | `{item['classification']}` | "
            f"`{', '.join(evidence)}` | "
            f"{'yes' if item['suspension_recommended'] else 'no'} |"
        )
    lines.extend(
        [
            "",
            "Assessments are local, inert evidence. A recommendation never changes "
            "runtime state on its own.",
            "",
            "## Explicit Lifecycle",
            "",
            "The administrator explicitly suspended the publication using the "
            "breaking endpoint assessment. A fresh ToolUniverse instance loaded no "
            "tool. After the baseline contract was confirmed again, an explicit "
            "activation restored loading and two authenticated executions passed, "
            "including a credential rotation. Retirement then excluded the tool and "
            "could not be reversed for that publication.",
            "",
            f"Lifecycle sequence: `{' -> '.join(lifecycle['states'])}`.",
            "",
            "A modified event failed validation before any registration. Each event "
            "links the previous event digest and the exact publication digest.",
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
            "## Operational Boundary",
            "",
            "The lifecycle command reads a local OpenAPI file; it does not crawl, "
            "fetch, execute, suspend, activate, retire, or republish automatically. "
            "State is local to one VSD workspace and affects newly loaded "
            "ToolUniverse instances. Already-running instances must be restarted or "
            "otherwise unloaded by their host application.",
            "",
            f"**Case audit SHA-256:** `{snapshot['audit_sha256']}`",
            "",
        ]
    )
    return "\n".join(lines)


def write_artifacts(
    snapshot: dict[str, Any],
    json_path: Path = DEFAULT_JSON,
    markdown_path: Path = DEFAULT_MARKDOWN,
) -> None:
    validate_snapshot(snapshot)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(snapshot, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(_markdown(snapshot), encoding="utf-8")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="tooluniverse-vsd-lifecycle-") as directory:
        snapshot = run_case(Path(directory))
    write_artifacts(snapshot)
    print(json.dumps({"status": "passed", "audit_sha256": snapshot["audit_sha256"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
