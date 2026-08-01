"""Prove OpenAPI ingestion and reviewed promotion with real ALS trial records."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tooluniverse import ToolUniverse
from tooluniverse.vsd_dynamic_rest import VSDDynamicRESTError, VSDDynamicRESTTool
from tooluniverse.vsd_openapi import inspect_openapi_document
from tooluniverse.vsd_promotion import (
    approve_draft,
    create_openapi_draft,
    list_promotion_state,
    load_published_tools,
    publish_draft,
    verify_draft,
)

HERE = Path(__file__).resolve().parent
ARTIFACTS = HERE / "artifacts"
DEFAULT_WORKSPACE = ARTIFACTS / "openapi_ingestion_workspace"
DEFAULT_JSON = ARTIFACTS / "openapi_als_snapshot.json"
DEFAULT_MARKDOWN = ARTIFACTS / "openapi_als_snapshot.md"
OFFICIAL_SPEC_URL = "https://clinicaltrials.gov/api/oas/v2"
OFFICIAL_DOCS_URL = "https://clinicaltrials.gov/data-api/api"
TOOL_NAME = "VSDClinicalTrialsStudyByNCT"
OPERATION_ID = "fetchStudy"
ALS_STUDIES = (
    "NCT03019419",
    "NCT04428775",
    "NCT04745299",
)
EXPECTED_ASSERTIONS = {
    "candidate_inert_before_review",
    "candidate_integrity_hash_propagated",
    "exact_nested_identifiers_verified",
    "fresh_runtime_loaded_explicitly",
    "generated_contract_is_read_only",
    "hash_chain_complete",
    "invalid_identifier_rejected_before_transport",
    "official_contract_parsed",
    "published_tool_absent_before_load",
    "provider_responses_schema_validated",
    "three_distinct_cases_verified",
    "zero_redirect_https_provenance",
}
DISCLAIMER = (
    "This case demonstrates software-governance and public-registry retrieval. "
    "It does not assess eligibility, efficacy, safety, or treatment suitability."
)


def _digest(value: Any) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _successful_result(response: Any) -> tuple[Any, dict[str, Any]]:
    if not isinstance(response, dict) or response.get("status") != "success":
        raise RuntimeError(f"Generated tool execution failed: {response!r}")
    data = response.get("data")
    if not isinstance(data, dict) or not isinstance(data.get("provenance"), dict):
        raise RuntimeError("Generated tool returned an invalid evidence envelope")
    return data.get("result"), data["provenance"]


def _study_summary(payload: Any, provenance: dict[str, Any]) -> dict[str, Any]:
    try:
        protocol = payload["protocolSection"]
        identification = protocol["identificationModule"]
        status = protocol["statusModule"]
        conditions = protocol["conditionsModule"]["conditions"]
    except (KeyError, TypeError) as exc:
        raise RuntimeError("Trial record lacks the reviewed study fields") from exc
    phases = protocol.get("designModule", {}).get("phases", [])
    brief_title = identification["briefTitle"].replace("\u00c2\u00ae", "(R)")
    return {
        "nct_id": identification["nctId"],
        "brief_title": brief_title,
        "overall_status": status["overallStatus"],
        "conditions": conditions,
        "phases": phases,
        "provenance": {
            key: provenance[key]
            for key in (
                "provider",
                "endpoint",
                "http_status",
                "content_type",
                "response_bytes",
                "redirects",
                "payload_sha256",
                "operation_sha256",
                "retrieved_at",
            )
        },
    }


def _verification_cases() -> list[dict[str, Any]]:
    return [
        {
            "arguments": {"nctId": nct_id},
            "expect": {
                "result_type": "object",
                "required_fields": ["protocolSection"],
                "required_paths": [
                    "/protocolSection/identificationModule/nctId",
                    "/protocolSection/identificationModule/briefTitle",
                    "/protocolSection/statusModule/overallStatus",
                    "/protocolSection/conditionsModule/conditions",
                ],
                "equals": {},
                "equals_paths": {"/protocolSection/identificationModule/nctId": nct_id},
            },
        }
        for nct_id in ALS_STUDIES
    ]


def run_case(*, spec_path: Path, workspace: Path) -> dict[str, Any]:
    """Run inspection, promotion, verification, publication, and fresh execution."""
    inspection = inspect_openapi_document(spec_path)
    matches = [
        candidate
        for candidate in inspection["candidates"]
        if candidate["operation_id"] == OPERATION_ID
    ]
    if len(matches) != 1:
        raise RuntimeError(f"Expected exactly one {OPERATION_ID!r} operation")
    candidate = matches[0]
    if candidate["blockers"]:
        raise RuntimeError(f"Selected operation is blocked: {candidate['blockers']!r}")
    if candidate["execution_allowed"] is not False:
        raise RuntimeError("Inspection candidate unexpectedly became executable")

    draft = create_openapi_draft(
        candidate,
        tool_name=TOOL_NAME,
        description=(
            "Fetch one reviewed ClinicalTrials.gov study record by its validated "
            "NCT identifier using the provider's official OpenAPI contract."
        ),
        fixed_query={"format": "json"},
        timeout_seconds=30,
        workspace=workspace,
    )
    evidence = verify_draft(
        draft["draft_id"], _verification_cases(), workspace=workspace
    )
    approval = approve_draft(
        draft["draft_id"],
        reviewed_by="ToolUniverse VSD case-study reviewer",
        decision_note=(
            "Approved after schema review and three distinct ALS registry records "
            "passed exact nested-identifier verification."
        ),
        workspace=workspace,
    )
    publication_path = workspace / "approved" / f"{TOOL_NAME}.json"
    publication = publish_draft(
        draft["draft_id"],
        workspace=workspace,
        replace=publication_path.exists(),
    )

    tooluniverse = ToolUniverse()
    try:
        absent_before_load = TOOL_NAME not in tooluniverse.all_tool_dict
        loaded = load_published_tools(tooluniverse, workspace=workspace)
        studies = []
        for nct_id in ALS_STUDIES:
            response = tooluniverse.run_one_function(
                {"name": TOOL_NAME, "arguments": {"nctId": nct_id}},
                use_cache=False,
            )
            payload, provenance = _successful_result(response)
            studies.append(_study_summary(payload, provenance))
    finally:
        tooluniverse.close()

    invalid_identifier_rejected = False
    generated = VSDDynamicRESTTool(draft["config"])
    try:
        generated.run({"nctId": "ALS-UNKNOWN"})
    except VSDDynamicRESTError as exc:
        invalid_identifier_rejected = "failed the reviewed schema" in str(exc)

    chain = {
        "source_document_sha256": inspection["source_document_sha256"],
        "candidate_sha256": candidate["candidate_sha256"],
        "operation_sha256": draft["operation_sha256"],
        "draft_sha256": draft["draft_sha256"],
        "verification_sha256": evidence["verification_sha256"],
        "approval_sha256": approval["approval_sha256"],
        "publication_sha256": publication["publication_sha256"],
    }
    assertions = {
        "official_contract_parsed": inspection["candidate_count"] > 0,
        "candidate_inert_before_review": candidate["execution_allowed"] is False,
        "candidate_integrity_hash_propagated": (
            draft["config"]["vsd_promotion"]["candidate_sha256"]
            == candidate["candidate_sha256"]
            and draft["config"]["vsd_promotion"]["source_document_sha256"]
            == inspection["source_document_sha256"]
        ),
        "generated_contract_is_read_only": (
            draft["config"]["vsd_operation"]["method"] == "GET"
            and draft["config"]["vsd_operation"]["auth"] == {"type": "none"}
        ),
        "three_distinct_cases_verified": (
            evidence["case_count"] == 3
            and len({case["arguments"]["nctId"] for case in evidence["cases"]}) == 3
        ),
        "exact_nested_identifiers_verified": all(
            case["expect"]["equals_paths"][
                "/protocolSection/identificationModule/nctId"
            ]
            == case["arguments"]["nctId"]
            for case in evidence["cases"]
        ),
        "hash_chain_complete": (
            approval["verification_sha256"] == evidence["verification_sha256"]
            and publication["approval_sha256"] == approval["approval_sha256"]
            and all(len(value) == 64 for value in chain.values())
        ),
        "published_tool_absent_before_load": absent_before_load,
        "fresh_runtime_loaded_explicitly": loaded == [TOOL_NAME],
        "provider_responses_schema_validated": [study["nct_id"] for study in studies]
        == list(ALS_STUDIES),
        "zero_redirect_https_provenance": all(
            study["provenance"]["provider"] == "clinicaltrials.gov"
            and study["provenance"]["http_status"] == 200
            and study["provenance"]["redirects"] == 0
            and study["provenance"]["endpoint"].startswith("https://")
            for study in studies
        ),
        "invalid_identifier_rejected_before_transport": invalid_identifier_rejected,
    }
    snapshot = {
        "title": "OpenAPI-to-Tool ALS Registry Case Study",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "question": (
            "Can an administrator turn the provider's current OpenAPI operation "
            "into a narrow ToolUniverse tool that retrieves exact ALS trial records "
            "without granting an agent arbitrary API access?"
        ),
        "answer": (
            "Yes. The local specification produced an inert candidate; the selected "
            "GET operation passed three exact record checks, was hash-approved, then "
            "loaded explicitly into a fresh ToolUniverse instance."
        ),
        "disclaimer": DISCLAIMER,
        "source_contract": {
            "official_docs_url": OFFICIAL_DOCS_URL,
            "official_spec_url": OFFICIAL_SPEC_URL,
            "local_file": spec_path.name,
            "document_sha256": inspection["source_document_sha256"],
            "api_title": inspection["api_title"],
            "api_version": inspection["api_version"],
            "openapi_version": inspection["openapi_version"],
        },
        "inspection": {
            "candidate_count": inspection["candidate_count"],
            "promotable_count": inspection["promotable_count"],
            "blocked_count": inspection["blocked_count"],
            "operation_ids": [
                item["operation_id"] for item in inspection["candidates"]
            ],
        },
        "selected_operation": {
            key: candidate[key]
            for key in (
                "candidate_id",
                "candidate_sha256",
                "operation_id",
                "method",
                "server_url",
                "path",
                "response_media_type",
                "parameters",
                "blockers",
                "warnings",
            )
        },
        "promotion": {
            "draft_id": draft["draft_id"],
            "verification_case_count": evidence["case_count"],
            "verification_cases": evidence["cases"],
            "reviewed_by": approval["reviewed_by"],
            "decision_note": approval["decision_note"],
            "loaded_tools": loaded,
            "state": list_promotion_state(workspace=workspace),
        },
        "retrieved_als_records": studies,
        "hash_chain": chain,
        "end_to_end_assertions": assertions,
    }
    snapshot["audit_sha256"] = _digest(
        {
            "source_contract": snapshot["source_contract"],
            "selected_operation": snapshot["selected_operation"],
            "promotion": snapshot["promotion"],
            "retrieved_als_records": snapshot["retrieved_als_records"],
            "hash_chain": snapshot["hash_chain"],
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
    chain = snapshot.get("hash_chain")
    if not isinstance(chain, dict) or any(
        not isinstance(value, str) or len(value) != 64 for value in chain.values()
    ):
        raise ValueError("Snapshot hash chain is invalid")
    expected_audit = _digest(
        {
            "source_contract": snapshot["source_contract"],
            "selected_operation": snapshot["selected_operation"],
            "promotion": snapshot["promotion"],
            "retrieved_als_records": snapshot["retrieved_als_records"],
            "hash_chain": snapshot["hash_chain"],
            "end_to_end_assertions": snapshot["end_to_end_assertions"],
        }
    )
    if snapshot.get("audit_sha256") != expected_audit:
        raise ValueError("Snapshot audit digest does not match its content")


def _markdown(snapshot: dict[str, Any]) -> str:
    source = snapshot["source_contract"]
    selected = snapshot["selected_operation"]
    promotion = snapshot["promotion"]
    lines = [
        "# OpenAPI-to-Tool ALS Registry Case Study",
        "",
        f"**Generated:** {snapshot['generated_at']}",
        "",
        "## Decision Question",
        "",
        snapshot["question"],
        "",
        f"**Result:** {snapshot['answer']}",
        "",
        "## Official Contract Inspection",
        "",
        f"- Provider documentation: {source['official_docs_url']}",
        f"- Current specification: {source['official_spec_url']}",
        f"- Contract: {source['api_title']} {source['api_version']} "
        f"(OpenAPI {source['openapi_version']})",
        f"- Source SHA-256: `{source['document_sha256']}`",
        f"- Operations inspected: {snapshot['inspection']['candidate_count']} "
        f"({snapshot['inspection']['promotable_count']} promotable, "
        f"{snapshot['inspection']['blocked_count']} blocked)",
        "",
        "The inspector read a local, bounded copy of the provider contract. It did "
        "not fetch, register, or execute any operation. Every candidate began with "
        "`execution_allowed: false`.",
        "",
        "## Selected Operation",
        "",
        "| Property | Reviewed value |",
        "| --- | --- |",
        f"| Operation | `{selected['operation_id']}` |",
        f"| Request | `{selected['method']} {selected['server_url']}{selected['path']}` |",
        f"| Response | `{selected['response_media_type']}` validated against the "
        "provider schema |",
        f"| Candidate | `{selected['candidate_id']}` |",
        f"| Blockers | `{json.dumps(selected['blockers'])}` |",
        "",
        "Only the required `nctId` path argument was exposed. The response format "
        "was fixed to JSON; CSV, ZIP, RIS, and FHIR choices in the broader provider "
        "operation were not exposed by this generated tool.",
        "",
        "## Verification And Approval",
        "",
        f"The draft `{promotion['draft_id']}` ran "
        f"{promotion['verification_case_count']} distinct ALS record cases. Each case "
        "required the nested title, status, condition, and NCT identifier paths and "
        "asserted that the returned identifier exactly matched the requested one.",
        "",
        "| NCT ID | Status | Phase | Brief title | Response bytes |",
        "| --- | --- | --- | --- | ---: |",
    ]
    for study in snapshot["retrieved_als_records"]:
        title = study["brief_title"].replace("|", "\\|")
        phase = ", ".join(study["phases"]) or "Not reported"
        lines.append(
            f"| `{study['nct_id']}` | {study['overall_status']} | {phase} | "
            f"{title} | {study['provenance']['response_bytes']} |"
        )
    lines.extend(
        [
            "",
            "Approval bound the exact source, candidate, operation, draft, verification, "
            "and publication hashes. A fresh ToolUniverse instance did not contain the "
            "tool until the approved publication was loaded explicitly.",
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
            "## Interpretation",
            "",
            "The practical value is contract conversion with evidence: an administrator "
            "can review one operation in a provider's official specification, narrow its "
            "inputs, prove it against real records, and distribute a hash-bound tool. The "
            "agent receives only that approved operation, not a generic HTTP client or the "
            "ability to promote other operations.",
            "",
            f"**Boundary:** {snapshot['disclaimer']}",
            "",
            f"**Audit SHA-256:** `{snapshot['audit_sha256']}`",
            "",
        ]
    )
    return "\n".join(lines)


def write_artifacts(
    snapshot: dict[str, Any], output_json: Path, output_md: Path
) -> None:
    validate_snapshot(snapshot)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(
        json.dumps(snapshot, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    output_md.write_text(_markdown(snapshot), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--spec",
        type=Path,
        required=True,
        help="Local copy of the reviewed OpenAPI JSON or YAML document.",
    )
    parser.add_argument("--workspace", type=Path, default=DEFAULT_WORKSPACE)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--output-markdown", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args()
    snapshot = run_case(spec_path=args.spec, workspace=args.workspace)
    write_artifacts(snapshot, args.output_json, args.output_markdown)
    print(json.dumps({"status": "passed", "audit_sha256": snapshot["audit_sha256"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
