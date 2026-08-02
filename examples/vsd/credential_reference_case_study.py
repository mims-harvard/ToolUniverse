"""Exercise environment-backed credentials through the full VSD promotion flow."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from tooluniverse import ToolUniverse, vsd_dynamic_rest, vsd_promotion
from tooluniverse.vsd_openapi import inspect_openapi_document

HERE = Path(__file__).resolve().parent
ARTIFACTS = HERE / "artifacts"
DEFAULT_JSON = ARTIFACTS / "credential_reference_snapshot.json"
DEFAULT_MARKDOWN = ARTIFACTS / "credential_reference_snapshot.md"

ENV_VAR = "TOOLUNIVERSE_VSD_RARE_DISEASE_KEY"
TOOL_NAME = "VSDProtectedRareDiseaseEvidence"
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
    "approved_publication_is_hash_bound",
    "candidate_remains_inert_before_promotion",
    "credential_environment_is_restored",
    "credential_reference_is_the_only_persisted_auth_material",
    "fresh_tooluniverse_executes_published_tool",
    "header_is_not_exposed_in_result_or_provenance",
    "invalid_credential_fails_before_transport",
    "missing_credential_fails_before_transport",
    "openapi_header_auth_is_recognized",
    "provider_reflection_is_rejected",
    "secret_values_are_absent_from_artifacts",
    "secret_rotation_preserves_operation_identity",
    "three_authenticated_verification_cases_pass",
    "transport_receives_only_reviewed_header",
}


def _digest(value: Any) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _secret(label: str) -> str:
    return hashlib.sha256(f"vsd-case:{label}".encode()).hexdigest()


def _specification() -> dict[str, Any]:
    record_schema = {
        "type": "object",
        "properties": {
            "record_id": {"type": "string"},
            "disease": {"type": "string"},
            "genes": {"type": "array", "items": {"type": "string"}},
            "phenotypes": {"type": "array", "items": {"type": "string"}},
            "trials": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["record_id", "disease", "genes", "phenotypes", "trials"],
        "additionalProperties": False,
    }
    return {
        "openapi": "3.1.0",
        "info": {"title": "Protected Rare Disease Evidence API", "version": "1.2.0"},
        "servers": [{"url": "https://rare-registry.example.org/v1"}],
        "security": [{"registryKey": []}],
        "paths": {
            "/evidence/{recordId}": {
                "get": {
                    "operationId": "getRareDiseaseEvidence",
                    "summary": "Retrieve one protected rare-disease evidence record",
                    "parameters": [
                        {
                            "name": "recordId",
                            "in": "path",
                            "required": True,
                            "schema": {
                                "type": "string",
                                "pattern": "^RD-(?:ALS|DMD|SMA)$",
                            },
                        },
                        {
                            "name": "sections",
                            "in": "query",
                            "style": "pipeDelimited",
                            "explode": False,
                            "schema": {
                                "type": "array",
                                "minItems": 1,
                                "maxItems": 3,
                                "uniqueItems": True,
                                "items": {
                                    "type": "string",
                                    "enum": ["genes", "phenotypes", "trials"],
                                },
                            },
                        },
                    ],
                    "responses": {
                        "200": {
                            "description": "Rare-disease evidence record",
                            "content": {"application/json": {"schema": record_schema}},
                        }
                    },
                }
            }
        },
        "components": {
            "securitySchemes": {
                "registryKey": {
                    "type": "apiKey",
                    "in": "header",
                    "name": "X-Rare-Disease-Key",
                }
            }
        },
    }


def _cases() -> list[dict[str, Any]]:
    return [
        {
            "arguments": {
                "recordId": record_id,
                "sections": ["genes", "phenotypes", "trials"],
            },
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


def _artifact_hashes(workspace: Path, draft_id: str) -> dict[str, str]:
    paths = {
        "draft": workspace / "drafts" / f"{draft_id}.json",
        "evidence": workspace / "evidence" / f"{draft_id}.json",
        "approval": workspace / "approvals" / f"{draft_id}.json",
        "publication": workspace / "approved" / f"{TOOL_NAME}.json",
    }
    return {
        name: hashlib.sha256(path.read_bytes()).hexdigest()
        for name, path in paths.items()
    }


def run_case(workspace: Path) -> dict[str, Any]:
    workspace = Path(workspace)
    spec_path = workspace / "protected-rare-disease-openapi.json"
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.write_text(
        json.dumps(_specification(), indent=2, sort_keys=True), encoding="utf-8"
    )
    initial_secret = _secret("initial")
    rotated_secret = _secret("rotated")
    reflected_secret = _secret("reflected")
    secret_values = (initial_secret, rotated_secret, reflected_secret)
    previous = os.environ.get(ENV_VAR)
    transport_log: list[dict[str, Any]] = []
    original_transport = vsd_dynamic_rest._safe_get_json

    def fake_transport(url, params, *, timeout, headers):
        assert set(headers) == {"X-Rare-Disease-Key"}
        secret = headers["X-Rare-Disease-Key"]
        slot = {
            initial_secret: "initial",
            rotated_secret: "rotated",
            reflected_secret: "reflected",
        }.get(secret)
        if slot is None:
            raise AssertionError("transport received an unknown credential")
        record_id = url.rsplit("/", 1)[-1]
        transport_log.append(
            {
                "credential_slot": slot,
                "header_name": "X-Rare-Disease-Key",
                "record_id": record_id,
                "params": dict(params),
                "timeout": timeout,
            }
        )
        payload = dict(RECORDS[record_id])
        if slot == "reflected":
            payload["credential_echo"] = secret
        return payload, {
            "status_code": 200,
            "content_type": "application/json",
            "response_bytes": len(json.dumps(payload).encode()),
            "redirects": 0,
        }

    missing_error = ""
    invalid_error = ""
    reflection_error = ""
    calls_before_missing = 0
    calls_after_missing = 0
    calls_before_invalid = 0
    calls_after_invalid = 0
    try:
        report = inspect_openapi_document(spec_path)
        candidate = report["candidates"][0]
        os.environ[ENV_VAR] = initial_secret
        vsd_dynamic_rest._safe_get_json = fake_transport
        draft = vsd_promotion.create_openapi_draft(
            candidate,
            tool_name=TOOL_NAME,
            description=(
                "Retrieve one authenticated reviewed rare-disease evidence record."
            ),
            include_parameters=["recordId", "sections"],
            credential_env=ENV_VAR,
            workspace=workspace,
        )
        evidence = vsd_promotion.verify_draft(
            draft["draft_id"], _cases(), workspace=workspace
        )
        approval = vsd_promotion.approve_draft(
            draft["draft_id"],
            reviewed_by="Credential Case Study Reviewer",
            decision_note=(
                "Approved after three authenticated disease records passed all checks."
            ),
            workspace=workspace,
        )
        publication = vsd_promotion.publish_draft(
            draft["draft_id"], workspace=workspace
        )
        tooluniverse = ToolUniverse()
        try:
            loaded = vsd_promotion.load_published_tools(
                tooluniverse, workspace=workspace
            )
            first_result = tooluniverse.run_one_function(
                {
                    "name": TOOL_NAME,
                    "arguments": {
                        "recordId": "RD-ALS",
                        "sections": ["genes", "phenotypes", "trials"],
                    },
                },
                use_cache=False,
            )
            operation_sha256 = first_result["data"]["provenance"]["operation_sha256"]
            os.environ[ENV_VAR] = rotated_secret
            rotated_result = tooluniverse.run_one_function(
                {
                    "name": TOOL_NAME,
                    "arguments": {
                        "recordId": "RD-SMA",
                        "sections": ["genes", "phenotypes", "trials"],
                    },
                },
                use_cache=False,
            )
        finally:
            tooluniverse.close()

        direct_tool = vsd_dynamic_rest.VSDDynamicRESTTool(publication["config"])
        os.environ.pop(ENV_VAR, None)
        calls_before_missing = len(transport_log)
        try:
            direct_tool.run({"recordId": "RD-ALS"})
        except vsd_dynamic_rest.VSDDynamicRESTError as exc:
            missing_error = str(exc)
        calls_after_missing = len(transport_log)
        os.environ[ENV_VAR] = " invalid-credential-value"
        calls_before_invalid = len(transport_log)
        try:
            direct_tool.run({"recordId": "RD-ALS"})
        except vsd_dynamic_rest.VSDDynamicRESTError as exc:
            invalid_error = str(exc)
        calls_after_invalid = len(transport_log)
        os.environ[ENV_VAR] = reflected_secret
        try:
            direct_tool.run({"recordId": "RD-ALS"})
        except vsd_dynamic_rest.VSDDynamicRESTError as exc:
            reflection_error = str(exc)
    finally:
        vsd_dynamic_rest._safe_get_json = original_transport
        if previous is None:
            os.environ.pop(ENV_VAR, None)
        else:
            os.environ[ENV_VAR] = previous

    persisted_text = "\n".join(
        path.read_text(encoding="utf-8") for path in workspace.rglob("*.json")
    )
    result_text = json.dumps(
        {"first": first_result, "rotated": rotated_result}, sort_keys=True
    )
    provenance = first_result["data"]["provenance"]
    artifact_hashes = _artifact_hashes(workspace, draft["draft_id"])
    assertions = {
        "openapi_header_auth_is_recognized": (
            report["promotable_count"] == 1
            and candidate["auth"]
            == {
                "type": "api_key_header",
                "scheme_name": "registryKey",
                "header": "X-Rare-Disease-Key",
            }
        ),
        "candidate_remains_inert_before_promotion": (
            candidate["execution_allowed"] is False
            and candidate["approval_state"] == "unreviewed_candidate"
        ),
        "credential_reference_is_the_only_persisted_auth_material": (
            publication["config"]["vsd_operation"]["auth"]
            == {
                "type": "api_key_header_env",
                "env_var": ENV_VAR,
                "header": "X-Rare-Disease-Key",
            }
            and ENV_VAR in persisted_text
        ),
        "three_authenticated_verification_cases_pass": (
            evidence["all_cases_passed"] is True and evidence["case_count"] == 3
        ),
        "approved_publication_is_hash_bound": (
            approval["approval_sha256"] == publication["approval_sha256"]
            and publication["operation_sha256"] == draft["operation_sha256"]
            and all(len(value) == 64 for value in artifact_hashes.values())
        ),
        "fresh_tooluniverse_executes_published_tool": (
            loaded == [TOOL_NAME]
            and first_result["status"] == "success"
            and first_result["data"]["result"]["record_id"] == "RD-ALS"
        ),
        "secret_rotation_preserves_operation_identity": (
            rotated_result["data"]["result"]["record_id"] == "RD-SMA"
            and rotated_result["data"]["provenance"]["operation_sha256"]
            == operation_sha256
            and transport_log[-2]["credential_slot"] == "rotated"
        ),
        "missing_credential_fails_before_transport": (
            "not set" in missing_error and calls_after_missing == calls_before_missing
        ),
        "invalid_credential_fails_before_transport": (
            "bearer token" not in invalid_error
            and "not a valid bounded value" in invalid_error
            and calls_after_invalid == calls_before_invalid
        ),
        "provider_reflection_is_rejected": (
            reflection_error == "Provider response reflected credential material"
            and transport_log[-1]["credential_slot"] == "reflected"
        ),
        "secret_values_are_absent_from_artifacts": all(
            secret not in persisted_text and secret not in result_text
            for secret in secret_values
        ),
        "header_is_not_exposed_in_result_or_provenance": (
            "X-Rare-Disease-Key" not in result_text
            and ENV_VAR not in result_text
            and provenance["authentication"]
            == {
                "type": "api_key_header_env",
                "credential_source": "environment",
            }
        ),
        "transport_receives_only_reviewed_header": (
            len(transport_log) == 6
            and all(
                entry["header_name"] == "X-Rare-Disease-Key" for entry in transport_log
            )
        ),
        "credential_environment_is_restored": os.environ.get(ENV_VAR) == previous,
    }
    snapshot = {
        "title": "Environment-Backed Rare-Disease Credential Case Study",
        "question": (
            "Can a reviewed ToolUniverse operation use a protected API without "
            "persisting, returning, or fixing the credential into its contract?"
        ),
        "answer": (
            "Yes. The protected header was derived from a reviewed OpenAPI scheme, "
            "read only at execution, rotated without changing the operation digest, "
            "and rejected when missing, malformed, or reflected by the provider."
        ),
        "provider_fixture": (
            "A deterministic protected rare-disease API fixture is used because no "
            "real credential is bundled with the repository. The full ToolUniverse "
            "promotion and runtime paths are real; only network transport is replaced."
        ),
        "inspection": {
            "source_document_sha256": report["source_document_sha256"],
            "candidate_id": candidate["candidate_id"],
            "candidate_sha256": candidate["candidate_sha256"],
            "auth": candidate["auth"],
            "blockers": candidate["blockers"],
        },
        "promotion": {
            "draft_id": draft["draft_id"],
            "draft_sha256": draft["draft_sha256"],
            "operation_sha256": draft["operation_sha256"],
            "verification_sha256": evidence["verification_sha256"],
            "approval_sha256": approval["approval_sha256"],
            "publication_sha256": publication["publication_sha256"],
            "artifact_file_sha256": artifact_hashes,
            "verification_case_count": evidence["case_count"],
        },
        "runtime": {
            "loaded_tools": loaded,
            "initial_record_id": first_result["data"]["result"]["record_id"],
            "rotated_record_id": rotated_result["data"]["result"]["record_id"],
            "operation_sha256_before_rotation": operation_sha256,
            "operation_sha256_after_rotation": rotated_result["data"]["provenance"][
                "operation_sha256"
            ],
            "authentication_provenance": provenance["authentication"],
            "transport_log": transport_log,
            "missing_credential_error": missing_error,
            "invalid_credential_error": invalid_error,
            "reflection_error": reflection_error,
        },
        "secret_persistence": {
            "persisted_secret_count": sum(
                secret in persisted_text for secret in secret_values
            ),
            "result_secret_count": sum(
                secret in result_text for secret in secret_values
            ),
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
    runtime = snapshot["runtime"]
    promotion = snapshot["promotion"]
    lines = [
        "# Environment-Backed Rare-Disease Credential Case Study",
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
        "The OpenAPI inspector recognized one required `apiKey` header named "
        "`X-Rare-Disease-Key`. The inert candidate contains the header contract but "
        "no value. Promotion binds that contract to the environment reference "
        f"`{snapshot['secret_persistence']['persisted_reference']}`.",
        "",
        "## Promotion Evidence",
        "",
        "| Boundary | SHA-256 |",
        "| --- | --- |",
        f"| Draft | `{promotion['draft_sha256']}` |",
        f"| Operation | `{promotion['operation_sha256']}` |",
        f"| Verification | `{promotion['verification_sha256']}` |",
        f"| Approval | `{promotion['approval_sha256']}` |",
        f"| Publication | `{promotion['publication_sha256']}` |",
        "",
        "Three authenticated verification cases retrieved ALS, Duchenne muscular "
        "dystrophy, and spinal muscular atrophy records with genes, phenotypes, and "
        "trial identifiers before approval and publication.",
        "",
        "## Runtime And Rotation",
        "",
        f"A fresh ToolUniverse instance loaded `{runtime['loaded_tools'][0]}`, returned "
        f"`{runtime['initial_record_id']}`, then returned "
        f"`{runtime['rotated_record_id']}` after credential rotation. The operation "
        "SHA-256 was unchanged because the reviewed contract stores only the "
        "environment reference.",
        "",
        "Missing and malformed values failed before transport. A provider response "
        "that reflected the exact runtime credential was rejected before schema "
        "validation or result construction.",
        "",
        "## End-to-End Assertions",
        "",
        "| Assertion | Result |",
        "| --- | --- |",
    ]
    lines.extend(
        f"| `{name}` | {'PASS' if passed else 'FAIL'} |"
        for name, passed in sorted(snapshot["end_to_end_assertions"].items())
    )
    lines.extend(
        [
            "",
            "## Secret Boundary",
            "",
            "No credential value appears in the draft, verification evidence, "
            "approval, publication, ToolUniverse result, provenance, or checked case "
            "artifact. The environment variable name is not a secret and remains in "
            "the reviewed contract so operators know what to configure.",
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
    with tempfile.TemporaryDirectory(
        prefix="tooluniverse-vsd-credentials-"
    ) as directory:
        snapshot = run_case(Path(directory))
    write_artifacts(snapshot)
    print(json.dumps({"status": "passed", "audit_sha256": snapshot["audit_sha256"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
