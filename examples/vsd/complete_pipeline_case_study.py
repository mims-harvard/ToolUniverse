"""Exercise the complete VSD governance path in one oncology case study."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
from collections import Counter
from collections.abc import Iterator
from contextlib import contextmanager, redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tooluniverse import ToolUniverse
from tooluniverse.vsd_admin_cli import main as vsd_admin_main
from tooluniverse.vsd_dynamic_rest import (
    operation_digest,
    register_reviewed_rest_tool,
)
from tooluniverse.vsd_promotion import (
    approve_draft,
    create_draft,
    list_promotion_state,
    load_published_tools,
    publish_draft,
    verify_draft,
)

HERE = Path(__file__).resolve().parent
ARTIFACTS = HERE / "artifacts"
DEFAULT_WORKSPACE = ARTIFACTS / "complete_pipeline_workspace"
DEFAULT_JSON = ARTIFACTS / "complete_pipeline_snapshot.json"
DEFAULT_MARKDOWN = ARTIFACTS / "complete_pipeline_snapshot.md"

ADMIN_SOURCE_ID = "openfda_tamoxifen_review"
OPENFDA_ENDPOINT = "https://api.fda.gov/drug/label.json"
OPENFDA_DEFAULT_PARAMS = {
    "search": 'openfda.generic_name:"tamoxifen"',
    "limit": 1,
}
DISCOVERY_QUERY = "active cancer clinical trials primary site phase protocol"
EXPECTED_DATASET_ID = "2ig8-yxf8"
EXPECTED_CATALOG_DOMAIN = "data.ny.gov"
REQUIRED_DISCOVERY_FIELDS = {
    "date_opened",
    "principal_investigator",
    "primary_site",
    "protocol",
    "study_phase",
    "title",
}
RETURN_FIELDS = [
    "date_opened",
    "protocol",
    "primary_site",
    "study_phase",
    "title",
    "date_closed",
    "principal_investigator",
]
ADMIN_TOOL_NAMES = {
    "VSDRegisterSource",
    "VSDListSources",
    "VSDQuerySource",
    "VSDRemoveSource",
}
EXPECTED_ASSERTIONS = {
    "administrative_catalog_restored",
    "administrative_tools_not_agent_facing",
    "discovery_candidate_has_required_fields",
    "discovery_candidate_remained_non_executable",
    "dynamic_search_detail_identifier_match",
    "fixed_adapter_matches_admin_record",
    "promoted_tools_absent_before_explicit_load",
    "promotion_hash_chain_complete",
    "published_runtime_filters_exact",
    "published_tools_loaded_explicitly",
    "reviewed_source_discovered_offline",
    "six_live_promotion_cases_passed",
}
ACTIVE_STATUSES = (
    "RECRUITING|NOT_YET_RECRUITING|ACTIVE_NOT_RECRUITING|ENROLLING_BY_INVITATION"
)
DISCLAIMER = (
    "This is a software-governance and public-record retrieval demonstration. "
    "It does not match patients to trials, establish eligibility, compare "
    "treatments, or provide medical advice. The state and national registries "
    "are independent and are not joined at record level."
)

SEARCH_TOOL = {
    "name": "VSDTotalClinicalTrialsSearch",
    "type": "VSDDynamicRESTTool",
    "description": (
        "Search the reviewed ClinicalTrials.gov contract for active or upcoming "
        "studies by condition and location expression."
    ),
    "category": "special_tools",
    "cacheable": False,
    "mcp_annotations": {"readOnlyHint": True, "destructiveHint": False},
    "parameter": {
        "type": "object",
        "properties": {
            "condition": {"type": "string", "minLength": 2, "maxLength": 200},
            "location_query": {
                "type": "string",
                "minLength": 2,
                "maxLength": 500,
            },
            "page_size": {"type": "integer", "minimum": 1, "maximum": 20},
        },
        "required": ["condition", "location_query", "page_size"],
        "additionalProperties": False,
    },
    "vsd_operation": {
        "version": 1,
        "method": "GET",
        "endpoint": "https://clinicaltrials.gov/api/v2/studies",
        "path_arguments": {},
        "query_arguments": {
            "condition": "query.cond",
            "location_query": "query.locn",
            "page_size": "pageSize",
        },
        "fixed_query": {
            "format": "json",
            "countTotal": "true",
            "filter.overallStatus": ACTIVE_STATUSES,
            "fields": (
                "NCTId,BriefTitle,OverallStatus,Phase,Condition,LocationFacility,"
                "LocationCity,LocationState,LocationCountry,LocationStatus"
            ),
        },
        "timeout_seconds": 30,
        "auth": {"type": "none"},
        "response_schema": {
            "type": "object",
            "properties": {
                "studies": {"type": "array", "maxItems": 20},
                "totalCount": {"type": "integer", "minimum": 0},
                "nextPageToken": {"type": "string"},
            },
            "required": ["studies"],
            "additionalProperties": True,
        },
    },
}

DETAIL_TOOL = {
    "name": "VSDTotalClinicalTrialDetails",
    "type": "VSDDynamicRESTTool",
    "description": (
        "Retrieve one record through the reviewed ClinicalTrials.gov contract "
        "using a validated NCT identifier."
    ),
    "category": "special_tools",
    "cacheable": False,
    "mcp_annotations": {"readOnlyHint": True, "destructiveHint": False},
    "parameter": {
        "type": "object",
        "properties": {"nct_id": {"type": "string", "pattern": "^NCT[0-9]{8}$"}},
        "required": ["nct_id"],
        "additionalProperties": False,
    },
    "vsd_operation": {
        "version": 1,
        "method": "GET",
        "endpoint": "https://clinicaltrials.gov/api/v2/studies/{nctId}",
        "path_arguments": {"nct_id": "nctId"},
        "query_arguments": {},
        "fixed_query": {"format": "json"},
        "timeout_seconds": 30,
        "auth": {"type": "none"},
        "response_schema": {
            "type": "object",
            "properties": {"protocolSection": {"type": "object"}},
            "required": ["protocolSection"],
            "additionalProperties": True,
        },
    },
}

PROMOTION_SPECS = (
    {
        "tool_name": "VSDTotalCancerTrialsBySite",
        "description": (
            "Query the reviewed Roswell Park active cancer-trial dataset by an "
            "exact primary cancer site."
        ),
        "filter_field": "primary_site",
        "verification_values": (
            "Brain and Nervous System",
            "Breast",
            "Prostate",
        ),
        "runtime_value": "Breast",
    },
    {
        "tool_name": "VSDTotalCancerTrialsByPhase",
        "description": (
            "Query the reviewed Roswell Park active cancer-trial dataset by an "
            "exact study phase."
        ),
        "filter_field": "study_phase",
        "verification_values": ("I", "II", "III"),
        "runtime_value": "III",
    },
)


def _digest(value: Any) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _successful_data(result: Any, tool_name: str) -> dict[str, Any]:
    if not isinstance(result, dict) or result.get("status") != "success":
        raise RuntimeError(f"{tool_name} did not succeed: {result!r}")
    data = result.get("data")
    if not isinstance(data, dict):
        raise RuntimeError(f"{tool_name} returned an invalid data envelope")
    return data


@contextmanager
def _catalog_environment(catalog_dir: Path) -> Iterator[None]:
    key = "TOOLUNIVERSE_VSD_DIR"
    previous = os.environ.get(key)
    os.environ[key] = str(catalog_dir)
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = previous


def _run_admin(arguments: list[str], catalog_dir: Path) -> dict[str, Any]:
    output = io.StringIO()
    with _catalog_environment(catalog_dir):
        with redirect_stdout(output):
            return_code = vsd_admin_main(arguments)
    if return_code != 0:
        raise RuntimeError(f"VSD administration command failed: {arguments!r}")
    try:
        result = json.loads(output.getvalue())
    except json.JSONDecodeError as exc:
        raise RuntimeError("VSD administration command returned invalid JSON") from exc
    return _successful_data(result, f"tooluniverse-vsd-admin {arguments[0]}")


def _admin_source_lifecycle(workspace: Path) -> tuple[dict[str, Any], str]:
    catalog_dir = workspace / "catalog"
    initial = _run_admin(["list"], catalog_dir)["sources"]
    initial_ids = sorted(source["source_id"] for source in initial)
    precleaned = False
    if ADMIN_SOURCE_ID in initial_ids:
        precleaned = _run_admin(["remove", ADMIN_SOURCE_ID], catalog_dir)["removed"]
    baseline_ids = [item for item in initial_ids if item != ADMIN_SOURCE_ID]

    registered = False
    registration: dict[str, Any] | None = None
    listed: dict[str, Any] | None = None
    query: dict[str, Any] | None = None
    removal: dict[str, Any] | None = None
    try:
        registration = _run_admin(
            [
                "register",
                ADMIN_SOURCE_ID,
                OPENFDA_ENDPOINT,
                "--name",
                "openFDA tamoxifen label review",
                "--description",
                (
                    "Temporary administrative inspection of one public tamoxifen "
                    "label before using the fixed reviewed adapter."
                ),
                "--default-params",
                json.dumps(OPENFDA_DEFAULT_PARAMS, sort_keys=True),
            ],
            catalog_dir,
        )
        registered = True
        listed = _run_admin(["list"], catalog_dir)
        query = _run_admin(["query", ADMIN_SOURCE_ID], catalog_dir)
    finally:
        if registered:
            removal = _run_admin(["remove", ADMIN_SOURCE_ID], catalog_dir)

    if registration is None or listed is None or query is None or removal is None:
        raise RuntimeError("Administrative source lifecycle was incomplete")
    final_sources = _run_admin(["list"], catalog_dir)["sources"]
    final_ids = sorted(source["source_id"] for source in final_sources)
    payload = query["result"]
    rows = payload.get("results") if isinstance(payload, dict) else None
    if not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict):
        raise RuntimeError("Administrative openFDA query did not return one label")
    row = rows[0]
    set_id = str(row.get("set_id") or "").lower()
    generic_names = (row.get("openfda") or {}).get("generic_name") or []
    if not re.fullmatch(
        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
        set_id,
    ) or not any("tamoxifen" in str(name).casefold() for name in generic_names):
        raise RuntimeError("Administrative openFDA result was not a tamoxifen label")

    request = query["request"]
    return (
        {
            "source_id": ADMIN_SOURCE_ID,
            "endpoint": OPENFDA_ENDPOINT,
            "preexisting_source_removed": precleaned,
            "initial_source_ids": initial_ids,
            "listed_source_ids": sorted(
                source["source_id"] for source in listed["sources"]
            ),
            "registered": registration["registered"],
            "registration_probe": registration["source"]["last_probe"],
            "query": {
                "default_params": OPENFDA_DEFAULT_PARAMS,
                "returned_records": len(rows),
                "provider_total_records": (payload.get("meta") or {})
                .get("results", {})
                .get("total"),
                "selected_set_id": set_id,
                "normalized_payload_sha256": _digest(payload),
                "http_status": request["status_code"],
                "content_type": request["content_type"],
                "response_bytes": request["response_bytes"],
                "redirects": request["redirects"],
            },
            "removed": removal["removed"],
            "final_source_ids": final_ids,
            "catalog_restored": final_ids == baseline_ids,
            "boundary": (
                "Registration and generic querying occurred only through the "
                "administrator CLI. They did not publish an agent-facing tool."
            ),
        },
        set_id,
    )


def _tool_call(
    tooluniverse: ToolUniverse, name: str, arguments: dict[str, Any]
) -> dict[str, Any]:
    return _successful_data(
        tooluniverse.run_one_function(
            {"name": name, "arguments": arguments}, use_cache=False
        ),
        name,
    )


def _module(study: dict[str, Any], name: str) -> dict[str, Any]:
    protocol = study.get("protocolSection") or {}
    value = protocol.get(name) or {}
    return value if isinstance(value, dict) else {}


def _study_summary(study: dict[str, Any]) -> dict[str, Any]:
    identification = _module(study, "identificationModule")
    status = _module(study, "statusModule")
    design = _module(study, "designModule")
    contacts = _module(study, "contactsLocationsModule")
    conditions = _module(study, "conditionsModule")
    locations = contacts.get("locations") or []
    return {
        "nct_id": identification.get("nctId"),
        "title": re.sub(r"\s+", " ", str(identification.get("briefTitle") or "")),
        "overall_status": status.get("overallStatus"),
        "phases": design.get("phases") or [],
        "conditions": conditions.get("conditions") or [],
        "new_york_locations": [
            {
                "facility": location.get("facility"),
                "city": location.get("city"),
                "status": location.get("status"),
            }
            for location in locations
            if isinstance(location, dict) and location.get("state") == "New York"
        ],
    }


def _review_discovery(
    discovery: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    candidates = discovery.get("candidates")
    if not isinstance(candidates, list):
        raise RuntimeError("API discovery returned no candidate list")
    reviewed = []
    selectable = []
    for candidate in candidates:
        if not isinstance(candidate, dict):
            raise RuntimeError("API discovery returned a malformed candidate")
        field_names = {
            str(field.get("field"))
            for field in candidate.get("fields") or []
            if isinstance(field, dict)
        }
        score = candidate.get("score") or {}
        missing = sorted(REQUIRED_DISCOVERY_FIELDS - field_names)
        ready = (
            candidate.get("execution_allowed") is False
            and candidate.get("approval_state") == "unreviewed_candidate"
            and score.get("api_ready") == 1.0
            and score.get("official_catalog_label") == 1.0
            and score.get("government_domain") == 1.0
            and not missing
        )
        summary = {
            "candidate_id": candidate.get("candidate_id"),
            "name": candidate.get("name"),
            "catalog_domain": candidate.get("catalog_domain"),
            "dataset_id": candidate.get("dataset_id"),
            "score": score.get("total"),
            "field_count": len(field_names),
            "matched_required_fields": sorted(REQUIRED_DISCOVERY_FIELDS & field_names),
            "missing_required_fields": missing,
            "execution_allowed": candidate.get("execution_allowed"),
            "approval_state": candidate.get("approval_state"),
            "selected_for_contract_review": ready,
        }
        reviewed.append(summary)
        if ready:
            selectable.append(candidate)
    if not selectable:
        raise RuntimeError("No discovered API passed the explicit review screen")
    selected = sorted(
        selectable,
        key=lambda candidate: (
            -float((candidate.get("score") or {}).get("total", 0)),
            str(candidate.get("candidate_id")),
        ),
    )[0]
    if (
        selected.get("catalog_domain") != EXPECTED_CATALOG_DOMAIN
        or selected.get("dataset_id") != EXPECTED_DATASET_ID
    ):
        raise RuntimeError(
            "The highest-ranked candidate changed; human contract review is required"
        )
    return selected, reviewed


def _run_agent_review(
    set_id: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    tooluniverse = ToolUniverse()
    requested_tools = [
        "VSDDiscoverSources",
        "VSDOpenFDALabelBySetId",
        "VSDDiscoverAPICandidates",
        *sorted(ADMIN_TOOL_NAMES),
    ]
    tooluniverse.load_tools(include_tools=requested_tools, quiet=True)
    try:
        loaded_before_dynamic = sorted(tool["name"] for tool in tooluniverse.all_tools)
        source_discovery = _tool_call(
            tooluniverse, "VSDDiscoverSources", {"query": "drug label"}
        )
        sources = source_discovery.get("sources")
        if not isinstance(sources, list):
            raise RuntimeError("Reviewed source discovery returned invalid data")
        openfda_sources = [
            source for source in sources if source.get("source_id") == "openfda_labels"
        ]
        if len(openfda_sources) != 1:
            raise RuntimeError("Reviewed openFDA source was not uniquely discoverable")

        label_data = _tool_call(
            tooluniverse, "VSDOpenFDALabelBySetId", {"set_id": set_id}
        )
        label = label_data.get("label")
        if not isinstance(label, dict) or label.get("set_id") != set_id:
            raise RuntimeError("Reviewed label adapter returned a different record")
        if "tamoxifen" not in str(label.get("generic_name") or "").casefold():
            raise RuntimeError("Reviewed label adapter did not return tamoxifen")

        for config in (SEARCH_TOOL, DETAIL_TOOL):
            register_reviewed_rest_tool(tooluniverse, config)
        search_data = _tool_call(
            tooluniverse,
            SEARCH_TOOL["name"],
            {
                "condition": "Breast Cancer",
                "location_query": "AREA[LocationState]New York",
                "page_size": 20,
            },
        )
        search_result = search_data.get("result")
        studies = (
            search_result.get("studies") if isinstance(search_result, dict) else None
        )
        if not isinstance(studies, list) or not studies:
            raise RuntimeError("Reviewed national trial search returned no studies")
        summaries = [_study_summary(study) for study in studies]
        summaries = [summary for summary in summaries if summary["nct_id"]]
        if not summaries:
            raise RuntimeError("Reviewed national trial search returned no NCT IDs")
        selected_nct_id = sorted(summary["nct_id"] for summary in summaries)[0]
        detail_data = _tool_call(
            tooluniverse, DETAIL_TOOL["name"], {"nct_id": selected_nct_id}
        )
        detail = _study_summary(detail_data["result"])
        if detail["nct_id"] != selected_nct_id:
            raise RuntimeError("Reviewed search and detail operations disagreed")

        discovery_data = _tool_call(
            tooluniverse,
            "VSDDiscoverAPICandidates",
            {"query": DISCOVERY_QUERY, "limit": 10},
        )
        candidate, candidate_summaries = _review_discovery(discovery_data)
        loaded_after_dynamic = sorted(tool["name"] for tool in tooluniverse.all_tools)
    finally:
        tooluniverse.close()

    reviewed_source = {
        "offline_query": "drug label",
        "matched_source": openfda_sources[0],
        "loaded_agent_tools_before_dynamic_registration": loaded_before_dynamic,
        "administrative_tools_loaded": sorted(
            ADMIN_TOOL_NAMES & set(loaded_before_dynamic)
        ),
        "label": {
            "set_id": label["set_id"],
            "effective_time": label["effective_time"],
            "brand_name": label["brand_name"],
            "generic_name": label["generic_name"],
            "route": label["route"],
            "warning_section_count": len(label["warnings"]),
            "warning_sections_sha256": _digest(label["warnings"]),
        },
        "provenance": label_data["provenance"],
    }
    statuses = Counter(summary["overall_status"] or "UNKNOWN" for summary in summaries)
    phases = Counter(
        phase
        for summary in summaries
        for phase in (summary["phases"] or ["NOT_APPLICABLE"])
    )
    dynamic_rest = {
        "tool_contracts": [
            {
                "name": config["name"],
                "endpoint": config["vsd_operation"]["endpoint"],
                "operation_sha256": operation_digest(config),
            }
            for config in (SEARCH_TOOL, DETAIL_TOOL)
        ],
        "search": {
            "arguments": {
                "condition": "Breast Cancer",
                "location_query": "AREA[LocationState]New York",
                "page_size": 20,
            },
            "provider_total_count": search_result.get("totalCount"),
            "returned_records": len(summaries),
            "returned_nct_ids": [summary["nct_id"] for summary in summaries],
            "status_counts": dict(sorted(statuses.items())),
            "phase_counts": dict(sorted(phases.items())),
            "sample_studies": summaries[:5],
            "provenance": search_data["provenance"],
        },
        "detail_follow_up": {
            "selection_rule": "Lexicographically smallest valid returned NCT ID",
            "selected_nct_id": selected_nct_id,
            "identifier_matches_search": any(
                summary["nct_id"] == detail["nct_id"] for summary in summaries
            ),
            "study": detail,
            "provenance": detail_data["provenance"],
        },
    }
    discovery = {
        "query": DISCOVERY_QUERY,
        "catalog_result_count": discovery_data.get("catalog_result_count"),
        "returned_candidate_count": len(candidate_summaries),
        "candidates": candidate_summaries,
        "selected_candidate": {
            **candidate,
            "fields": candidate.get("fields") or [],
        },
        "selection_rule": (
            "Require non-executable unreviewed state, an official government "
            "API-ready catalog record, and all six demanded fields; then choose "
            "the highest score with candidate ID as the stable tie-breaker."
        ),
        "loaded_agent_tools_after_dynamic_registration": loaded_after_dynamic,
        "boundary": discovery_data.get("boundary"),
        "provenance": discovery_data.get("provenance"),
    }
    return reviewed_source, dynamic_rest, discovery


def _verification_cases(field: str, values: tuple[str, ...]) -> list[dict[str, Any]]:
    return [
        {
            "arguments": {field: value},
            "expect": {
                "min_items": 1,
                "max_items": 25,
                "required_fields": ["protocol", "title", field],
                "equals": {field: value},
            },
        }
        for value in values
    ]


def _promote_and_execute(candidate: dict[str, Any], workspace: Path) -> dict[str, Any]:
    promotion_workspace = workspace / "promotion"
    promotions = []
    for spec in PROMOTION_SPECS:
        draft = create_draft(
            candidate,
            tool_name=spec["tool_name"],
            description=spec["description"],
            filter_fields=[spec["filter_field"]],
            return_fields=RETURN_FIELDS,
            max_records=25,
            workspace=promotion_workspace,
        )
        evidence = verify_draft(
            draft["draft_id"],
            _verification_cases(spec["filter_field"], spec["verification_values"]),
            workspace=promotion_workspace,
        )
        approval = approve_draft(
            draft["draft_id"],
            reviewed_by="SufianTA",
            decision_note=(
                "Technical approval after field-contract review and three live "
                "provider cases; not scientific or clinical endorsement."
            ),
            workspace=promotion_workspace,
        )
        publication = publish_draft(
            draft["draft_id"], workspace=promotion_workspace, replace=True
        )
        promotions.append(
            {
                "tool_name": spec["tool_name"],
                "filter_field": spec["filter_field"],
                "draft_id": draft["draft_id"],
                "draft_sha256": draft["draft_sha256"],
                "operation_sha256": draft["operation_sha256"],
                "verification_sha256": evidence["verification_sha256"],
                "approval_sha256": approval["approval_sha256"],
                "publication_sha256": publication["publication_sha256"],
                "case_count": evidence["case_count"],
                "all_cases_passed": evidence["all_cases_passed"],
                "cases": evidence["cases"],
            }
        )

    runtime = ToolUniverse(
        tool_files={},
        keep_default_tools=False,
        workspace=str(workspace / ".runtime"),
    )
    try:
        loaded_before = sorted(tool["name"] for tool in runtime.all_tools)
        loaded = load_published_tools(runtime, workspace=promotion_workspace)
        checks = []
        for spec in PROMOTION_SPECS:
            arguments = {spec["filter_field"]: spec["runtime_value"]}
            data = _tool_call(runtime, spec["tool_name"], arguments)
            rows = data["result"]
            if not rows or any(
                row.get(spec["filter_field"]) != spec["runtime_value"] for row in rows
            ):
                raise RuntimeError("Published tool violated its reviewed exact filter")
            checks.append(
                {
                    "tool_name": spec["tool_name"],
                    "arguments": arguments,
                    "row_count": len(rows),
                    "sample_rows": rows[:3],
                    "provenance": data["provenance"],
                }
            )
    finally:
        runtime.close()
    return {
        "promotions": promotions,
        "verification_case_count": sum(item["case_count"] for item in promotions),
        "promoted_tools_present_before_explicit_load": sorted(
            set(loaded_before) & {spec["tool_name"] for spec in PROMOTION_SPECS}
        ),
        "loaded_tools": loaded,
        "runtime_checks": checks,
        "promotion_state": list_promotion_state(workspace=promotion_workspace),
    }


def _audit_inputs(snapshot: dict[str, Any]) -> dict[str, Any]:
    return {
        "admin_query_payload": snapshot["administrative_source_lifecycle"]["query"][
            "normalized_payload_sha256"
        ],
        "reviewed_label_payload": snapshot["reviewed_source_adapter"]["provenance"][
            "payload_sha256"
        ],
        "dynamic_contracts": [
            contract["operation_sha256"]
            for contract in snapshot["reviewed_dynamic_rest"]["tool_contracts"]
        ],
        "dynamic_payloads": [
            snapshot["reviewed_dynamic_rest"]["search"]["provenance"]["payload_sha256"],
            snapshot["reviewed_dynamic_rest"]["detail_follow_up"]["provenance"][
                "payload_sha256"
            ],
        ],
        "discovery_payload": snapshot["demand_discovery"]["provenance"][
            "payload_sha256"
        ],
        "selected_candidate": snapshot["demand_discovery"]["selected_candidate"][
            "candidate_id"
        ],
        "promotion_chains": [
            {
                key: promotion[key]
                for key in (
                    "draft_sha256",
                    "operation_sha256",
                    "verification_sha256",
                    "approval_sha256",
                    "publication_sha256",
                )
            }
            for promotion in snapshot["reviewed_promotion"]["promotions"]
        ],
        "runtime_payloads": [
            check["provenance"]["payload_sha256"]
            for check in snapshot["reviewed_promotion"]["runtime_checks"]
        ],
    }


def validate_snapshot(snapshot: dict[str, Any]) -> None:
    """Fail closed if any stage or audit-chain assertion is incomplete."""
    if snapshot.get("case") != "complete_vsd_oncology_source_governance":
        raise ValueError("Unexpected complete-case identifier")
    assertions = snapshot.get("end_to_end_assertions")
    if (
        not isinstance(assertions, dict)
        or set(assertions) != EXPECTED_ASSERTIONS
        or not all(value is True for value in assertions.values())
    ):
        raise ValueError("One or more end-to-end assertions did not pass")
    audit = snapshot.get("audit_chain")
    if not isinstance(audit, dict) or audit.get("inputs") != _audit_inputs(snapshot):
        raise ValueError("Audit-chain inputs do not match the stage evidence")
    if audit.get("sha256") != _digest(audit["inputs"]):
        raise ValueError("Audit-chain digest does not match its inputs")


def run_case(*, workspace: Path) -> dict[str, Any]:
    administrative, set_id = _admin_source_lifecycle(workspace)
    reviewed_source, dynamic_rest, discovery = _run_agent_review(set_id)
    promotion = _promote_and_execute(discovery["selected_candidate"], workspace)

    expected_loaded = sorted(spec["tool_name"] for spec in PROMOTION_SPECS)
    hash_fields = (
        "draft_sha256",
        "operation_sha256",
        "verification_sha256",
        "approval_sha256",
        "publication_sha256",
    )
    assertions = {
        "administrative_catalog_restored": administrative["catalog_restored"],
        "administrative_tools_not_agent_facing": not reviewed_source[
            "administrative_tools_loaded"
        ],
        "reviewed_source_discovered_offline": reviewed_source["matched_source"].get(
            "source_id"
        )
        == "openfda_labels",
        "fixed_adapter_matches_admin_record": reviewed_source["label"]["set_id"]
        == administrative["query"]["selected_set_id"],
        "dynamic_search_detail_identifier_match": dynamic_rest["detail_follow_up"][
            "identifier_matches_search"
        ],
        "discovery_candidate_remained_non_executable": discovery["selected_candidate"][
            "execution_allowed"
        ]
        is False,
        "discovery_candidate_has_required_fields": not next(
            candidate["missing_required_fields"]
            for candidate in discovery["candidates"]
            if candidate["candidate_id"]
            == discovery["selected_candidate"]["candidate_id"]
        ),
        "six_live_promotion_cases_passed": promotion["verification_case_count"] == 6
        and all(item["all_cases_passed"] for item in promotion["promotions"]),
        "promotion_hash_chain_complete": all(
            re.fullmatch(r"[0-9a-f]{64}", str(item.get(field, "")))
            for item in promotion["promotions"]
            for field in hash_fields
        ),
        "promoted_tools_absent_before_explicit_load": not promotion[
            "promoted_tools_present_before_explicit_load"
        ],
        "published_tools_loaded_explicitly": promotion["loaded_tools"]
        == expected_loaded,
        "published_runtime_filters_exact": all(
            check["row_count"] >= 1
            and all(
                row.get(next(iter(check["arguments"])))
                == next(iter(check["arguments"].values()))
                for row in check["sample_rows"]
            )
            for check in promotion["runtime_checks"]
        ),
    }
    snapshot = {
        "case": "complete_vsd_oncology_source_governance",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "decision_question": (
            "Can ToolUniverse start from an oncology evidence need, keep generic "
            "source administration outside the agent boundary, execute reviewed "
            "contracts, discover an unknown API without executing it, and promote "
            "only verified narrow tools with a complete audit chain?"
        ),
        "administrative_source_lifecycle": administrative,
        "reviewed_source_adapter": reviewed_source,
        "reviewed_dynamic_rest": dynamic_rest,
        "demand_discovery": discovery,
        "reviewed_promotion": promotion,
        "end_to_end_assertions": assertions,
        "interpretation_boundary": DISCLAIMER,
    }
    inputs = _audit_inputs(snapshot)
    snapshot["audit_chain"] = {"inputs": inputs, "sha256": _digest(inputs)}
    validate_snapshot(snapshot)
    return snapshot


def render_markdown(snapshot: dict[str, Any]) -> str:
    admin = snapshot["administrative_source_lifecycle"]
    source = snapshot["reviewed_source_adapter"]
    dynamic = snapshot["reviewed_dynamic_rest"]
    discovery = snapshot["demand_discovery"]
    promotion = snapshot["reviewed_promotion"]
    selected = discovery["selected_candidate"]
    lines = [
        "# Complete VSD Oncology Source-Governance Case Study",
        "",
        "## Decision Question",
        "",
        snapshot["decision_question"],
        "",
        "## End-to-End Result",
        "",
        "| Stage | Boundary exercised | Live proof |",
        "| ---: | --- | --- |",
        (
            "| 1 | Administrator-only source catalog | Registered, probed, listed, "
            "queried, removed, and restored the temporary catalog |"
        ),
        (
            "| 2 | Packaged reviewed adapter | Discovered openFDA offline and "
            "retrieved the same tamoxifen label through a fixed typed tool |"
        ),
        (
            "| 3 | Reviewed dynamic REST | Searched active/upcoming New York breast-"
            "cancer studies and retrieved one deterministic NCT record |"
        ),
        (
            "| 4 | Demand-driven discovery | Searched the fixed Socrata catalog and "
            "kept the selected API non-executable pending review |"
        ),
        (
            "| 5 | Reviewed promotion | Ran six live verification cases, approved "
            "hash-bound drafts, and published two bounded tools |"
        ),
        (
            "| 6 | Explicit runtime loading | Loaded both publications into a fresh "
            "ToolUniverse instance and executed exact-filter queries |"
        ),
        "",
        "## 1. Administrative Source Lifecycle",
        "",
        f"- Source: `{admin['source_id']}` at `{admin['endpoint']}`",
        f"- Probe HTTP status: **{admin['registration_probe']['status_code']}**",
        f"- Query records: **{admin['query']['returned_records']}** of "
        f"**{admin['query']['provider_total_records']}** provider matches",
        f"- Selected label set ID: `{admin['query']['selected_set_id']}`",
        f"- Removed after inspection: **{str(admin['removed']).lower()}**",
        f"- Catalog restored: **{str(admin['catalog_restored']).lower()}**",
        f"- Boundary: {admin['boundary']}",
        "",
        "## 2. Reviewed Source Adapter",
        "",
        f"- Offline source: **{source['matched_source']['name']}**",
        f"- Agent-facing tool: `{source['matched_source']['tool_name']}`",
        f"- Label: **{source['label']['brand_name']}** "
        f"(`{source['label']['generic_name']}`)",
        f"- Effective time: `{source['label']['effective_time']}`",
        f"- Route: `{source['label']['route']}`",
        f"- Administrative operations present in the agent runtime: "
        f"**{len(source['administrative_tools_loaded'])}**",
        f"- Provider payload: `{source['provenance']['payload_sha256']}`",
        "",
        "The generic administrative query established a record identifier only. "
        "The agent-facing call used the fixed openFDA endpoint, UUID input contract, "
        "source-specific response validation, and typed provenance.",
        "",
        "## 3. Reviewed Dynamic REST",
        "",
        f"- National registry matches: **{dynamic['search']['provider_total_count']}**",
        f"- Bounded records returned: **{dynamic['search']['returned_records']}**",
        f"- Status counts: `{json.dumps(dynamic['search']['status_counts'], sort_keys=True)}`",
        f"- Phase counts: `{json.dumps(dynamic['search']['phase_counts'], sort_keys=True)}`",
        f"- Deterministic detail record: `{dynamic['detail_follow_up']['selected_nct_id']}`",
        f"- Search/detail ID match: "
        f"**{str(dynamic['detail_follow_up']['identifier_matches_search']).lower()}**",
        "",
        "Both operations are reviewed HTTPS GET contracts with exact argument "
        "mappings, bounded schemas, no credentials, zero redirects, pinned public "
        "destinations, response limits, and operation/payload hashes.",
        "",
        "## 4. Demand-Driven API Discovery",
        "",
        f"- Demand query: `{discovery['query']}`",
        f"- Catalog matches: **{discovery['catalog_result_count']}**",
        f"- Candidates reviewed: **{discovery['returned_candidate_count']}**",
        f"- Selected dataset: **{selected['name']}** (`{selected['dataset_id']}`)",
        f"- Proposed endpoint: `{selected['api_endpoint']}`",
        f"- Required fields present: **{len(REQUIRED_DISCOVERY_FIELDS)}/"
        f"{len(REQUIRED_DISCOVERY_FIELDS)}**",
        f"- Execution allowed before review: **{str(selected['execution_allowed']).lower()}**",
        f"- Selection rule: {discovery['selection_rule']}",
        "",
        "## 5. Promotion And Fresh Runtime",
        "",
        "| Tool | Required filter | Verification rows | Runtime query | Runtime rows |",
        "| --- | --- | --- | --- | ---: |",
    ]
    for item, runtime in zip(
        promotion["promotions"], promotion["runtime_checks"], strict=True
    ):
        verification_rows = ", ".join(str(case["row_count"]) for case in item["cases"])
        argument = next(iter(runtime["arguments"].items()))
        lines.append(
            f"| `{item['tool_name']}` | `{item['filter_field']}` | "
            f"{verification_rows} | `{argument[0]}={argument[1]}` | "
            f"{runtime['row_count']} |"
        )
    lines.extend(
        [
            "",
            f"- Live verification cases: **{promotion['verification_case_count']}**",
            f"- Promoted tools present before explicit load: "
            f"**{len(promotion['promoted_tools_present_before_explicit_load'])}**",
            "- Explicitly loaded publications: "
            + ", ".join(f"`{name}`" for name in promotion["loaded_tools"]),
            "",
            "Every draft, verification result, approval, and publication is bound "
            "to the preceding SHA-256 records. Loading is a separate explicit call; "
            "discovery alone never executes or publishes a candidate.",
            "",
            "## End-to-End Assertions",
            "",
            "| Assertion | Result |",
            "| --- | --- |",
        ]
    )
    for name, passed in sorted(snapshot["end_to_end_assertions"].items()):
        lines.append(f"| `{name}` | {'PASS' if passed else 'FAIL'} |")
    lines.extend(
        [
            "",
            "## Reproducibility And Audit Chain",
            "",
            f"- End-to-end evidence-chain SHA-256: `{snapshot['audit_chain']['sha256']}`",
            f"- Generated at: `{snapshot['generated_at']}`",
            "- The JSON artifact contains provider payload hashes, reviewed operation "
            "hashes, promotion hashes, exact arguments, bounded samples, and every "
            "assertion used to accept the run.",
            "",
            "## Interpretation Boundary",
            "",
            snapshot["interpretation_boundary"],
            "",
        ]
    )
    return "\n".join(lines)


def write_artifacts(
    snapshot: dict[str, Any], output_json: Path, output_markdown: Path
) -> tuple[Path, Path]:
    validate_snapshot(snapshot)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_markdown.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(
        json.dumps(snapshot, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    output_markdown.write_text(render_markdown(snapshot), encoding="utf-8")
    return output_json, output_markdown


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=DEFAULT_WORKSPACE)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--output-markdown", type=Path, default=DEFAULT_MARKDOWN)
    arguments = parser.parse_args(argv)
    snapshot = run_case(workspace=arguments.workspace)
    write_artifacts(snapshot, arguments.output_json, arguments.output_markdown)
    print(
        json.dumps(
            {
                "assertions_passed": sum(snapshot["end_to_end_assertions"].values()),
                "audit_chain_sha256": snapshot["audit_chain"]["sha256"],
                "loaded_tools": snapshot["reviewed_promotion"]["loaded_tools"],
                "output_json": str(arguments.output_json),
                "output_markdown": str(arguments.output_markdown),
                "verification_cases": snapshot["reviewed_promotion"][
                    "verification_case_count"
                ],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
