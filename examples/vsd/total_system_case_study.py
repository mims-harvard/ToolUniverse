"""Exercise the complete demand-to-reviewed-tool VSD growth loop."""

from __future__ import annotations

import copy
import hashlib
import io
import json
import os
import tempfile
from contextlib import redirect_stdout
from datetime import datetime
from pathlib import Path
from typing import Any

from tooluniverse import (
    ToolUniverse,
    vsd_discovery,
    vsd_dynamic_rest,
    vsd_lifecycle as vsd_lifecycle_module,
    vsd_promotion as vsd_promotion_module,
    vsd_tool,
)
from tooluniverse.tool_registry import get_config_registry, get_tool_registry
from tooluniverse.vsd_admin_cli import main as admin_main
from tooluniverse.vsd_coverage import resolve_capability
from tooluniverse.vsd_demand import (
    export_proposals,
    observe_capability_demand,
    rank_demands,
    record_plan_demands,
    remove_demand,
    validate_proposal_export,
)
from tooluniverse.vsd_lifecycle import (
    assess_openapi_drift,
    list_publication_states,
    set_publication_state,
)
from tooluniverse.vsd_openapi import inspect_openapi_document
from tooluniverse.vsd_planning import plan_workflow
from tooluniverse.vsd_promotion import (
    approve_draft,
    create_openapi_draft,
    load_published_tools,
    publish_draft,
    verify_draft,
)

HERE = Path(__file__).resolve().parent
ARTIFACTS = HERE / "artifacts"
DEFAULT_JSON = ARTIFACTS / "total_system_snapshot.json"
DEFAULT_MARKDOWN = ARTIFACTS / "total_system_snapshot.md"
DEFAULT_PROPOSALS = ARTIFACTS / "total_system_demand_proposal.json"

ENV_VAR = "TOOLUNIVERSE_VSD_TOTAL_CASE_KEY"
TOOL_NAME = "VSDProtectedRareDiseaseEvidenceById"
SOURCE_ID = "protected_rare_registry"
PROVIDER_HOST = "rare-registry.example.org"
PROVIDER_BASE = f"https://{PROVIDER_HOST}/v1"
PUBLIC_SUMMARY = (
    "Protected rare-disease genes phenotypes and trials retrieval for ALS workflows"
)
RAW_DESCRIPTION = (
    "retrieve consolidated protected rare disease genes phenotypes and clinical "
    "trial identifiers by registry record"
)
CAPABILITY = {
    "description": RAW_DESCRIPTION,
    "provider": PROVIDER_HOST,
    "method": "GET",
    "endpoint": f"{PROVIDER_BASE}/evidence/{{recordId}}",
    "required_inputs": ["recordId"],
    "output_fields": ["record_id", "disease", "genes", "phenotypes", "trials"],
}
WORKFLOW_GOAL = (
    "Build a reviewed ALS registry brief with consolidated genes phenotypes and trials"
)
WORKFLOW_STEPS = [
    {"step_id": "registry_evidence", **CAPABILITY},
    {
        "step_id": "synthesis",
        "description": "synthesize the reviewed ALS registry evidence into a brief",
        "fulfillment": "agent",
        "depends_on": ["registry_evidence"],
    },
]
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
    "admin_source_lifecycle_is_complete_and_restored",
    "administrative_mutations_are_not_agent_facing",
    "api_catalog_candidate_is_inert",
    "breaking_drift_recommends_suspension",
    "credential_reference_is_persisted_without_value",
    "credential_rotation_preserves_operation_identity",
    "demand_closure_is_explicit_and_hash_bound",
    "demand_export_is_sanitized_local_and_hash_bound",
    "exact_observation_updates_original_demand",
    "final_reactivated_tool_executes",
    "finder_and_replanner_share_expanded_registry",
    "initial_capability_is_missing",
    "initial_workflow_routes_only_real_gap",
    "lifecycle_anchor_and_events_are_consistent",
    "openapi_candidate_is_authenticated_inert_and_promotable",
    "post_publication_capability_is_exact",
    "provider_transport_uses_only_reviewed_header",
    "repaired_contract_supports_safe_activation",
    "repeated_private_demand_ranks_first",
    "replanned_workflow_reuses_published_tool",
    "secret_values_are_absent_from_artifacts_and_results",
    "source_and_credential_environment_is_restored",
    "suspension_prevents_fresh_loading",
    "three_protected_verification_cases_pass",
    "tool_is_absent_until_explicit_publication_load",
    "workflow_and_demand_inputs_remain_private",
}


def _digest(value: Any) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _secret(label: str) -> str:
    return hashlib.sha256(f"vsd-total-system:{label}".encode()).hexdigest()


def _record_schema() -> dict[str, Any]:
    return {
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


def _specification(
    *, server_url: str = PROVIDER_BASE, version: str = "1.0.0"
) -> dict[str, Any]:
    return {
        "openapi": "3.1.0",
        "info": {"title": "Protected Rare Disease Registry", "version": version},
        "servers": [{"url": server_url}],
        "security": [{"registryKey": []}],
        "paths": {
            "/evidence/{recordId}": {
                "get": {
                    "operationId": "getRareDiseaseEvidence",
                    "summary": "Retrieve consolidated rare-disease evidence",
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
                            "description": "One reviewed evidence record",
                            "content": {
                                "application/json": {"schema": _record_schema()}
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
                    "in": "header",
                    "name": "X-Rare-Disease-Key",
                }
            }
        },
    }


def _write_spec(workspace: Path, name: str, document: dict[str, Any]) -> Path:
    path = workspace / "provider-contracts" / f"{name}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2, sort_keys=True), encoding="utf-8")
    return path


def _verification_cases() -> list[dict[str, Any]]:
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


def _catalog_item(
    *, name: str, domain: str, dataset_id: str, provenance: str
) -> dict[str, Any]:
    fields = ["record_id", "disease", "genes", "phenotypes", "trials"]
    return {
        "resource": {
            "name": name,
            "id": dataset_id,
            "description": (
                "Rare disease evidence with genes phenotypes and trial identifiers."
            ),
            "type": "dataset",
            "updatedAt": "2026-07-01T00:00:00Z",
            "provenance": provenance,
            "columns_name": [field.replace("_", " ").title() for field in fields],
            "columns_field_name": fields,
            "columns_datatype": ["Text"] * len(fields),
            "columns_description": [f"Reviewed hint for {field}" for field in fields],
        },
        "metadata": {"domain": domain},
        "classification": {
            "domain_tags": ["rare disease", "genes", "phenotypes", "trials"]
        },
        "permalink": f"https://{domain}/d/{dataset_id}",
    }


def _catalog_payload() -> dict[str, Any]:
    return {
        "results": [
            _catalog_item(
                name="Rare Disease Evidence Registry",
                domain="health.data.ny.gov",
                dataset_id="rare-1234",
                provenance="official",
            ),
            _catalog_item(
                name="Community Disease Resource Inventory",
                domain="community.example.org",
                dataset_id="comm-5678",
                provenance="community",
            ),
        ],
        "resultSetSize": 2,
    }


def _run_admin(arguments: list[str], catalog_directory: Path) -> dict[str, Any]:
    previous = os.environ.get("TOOLUNIVERSE_VSD_DIR")
    os.environ["TOOLUNIVERSE_VSD_DIR"] = str(catalog_directory)
    output = io.StringIO()
    try:
        with redirect_stdout(output):
            code = admin_main(arguments)
    finally:
        if previous is None:
            os.environ.pop("TOOLUNIVERSE_VSD_DIR", None)
        else:
            os.environ["TOOLUNIVERSE_VSD_DIR"] = previous
    if code != 0:
        raise RuntimeError(f"VSD administrator command failed: {arguments!r}")
    return json.loads(output.getvalue())["data"]


def _tool_data(
    tooluniverse: ToolUniverse, name: str, arguments: dict[str, Any]
) -> dict[str, Any]:
    result = tooluniverse.run_one_function(
        {"name": name, "arguments": arguments}, use_cache=False
    )
    if not isinstance(result, dict) or result.get("status") == "error":
        raise RuntimeError(f"{name} failed: {result!r}")
    if result.get("status") == "success" and isinstance(result.get("data"), dict):
        return result["data"]
    return result


def run_case(workspace: Path) -> dict[str, Any]:
    workspace = Path(workspace)
    promotion_workspace = workspace / "promotion"
    demand_workspace = workspace / "demand"
    catalog_workspace = workspace / "source-catalog"
    proposal_path = workspace / "reviewed-demand-proposal.json"
    baseline_spec = _write_spec(workspace, "baseline", _specification())
    breaking_spec = _write_spec(
        workspace,
        "breaking-endpoint",
        _specification(server_url=f"https://{PROVIDER_HOST}/v2", version="2.0.0"),
    )
    initial_secret = _secret("initial")
    rotated_secret = _secret("rotated")
    secrets = (initial_secret, rotated_secret)
    previous_environment = {
        ENV_VAR: os.environ.get(ENV_VAR),
        "TOOLUNIVERSE_VSD_ALLOWED_HOSTS": os.environ.get(
            "TOOLUNIVERSE_VSD_ALLOWED_HOSTS"
        ),
        "TOOLUNIVERSE_VSD_DIR": os.environ.get("TOOLUNIVERSE_VSD_DIR"),
    }
    original_source_transport = vsd_tool._safe_get_json
    original_resolver = vsd_tool._resolve_public_addresses
    original_discovery_transport = vsd_discovery._safe_get_json
    original_dynamic_transport = vsd_dynamic_rest._safe_get_json
    original_dynamic_datetime = vsd_dynamic_rest.datetime
    original_promotion_datetime = vsd_promotion_module.datetime
    original_lifecycle_timestamp = vsd_lifecycle_module._timestamp
    source_transport_log: list[dict[str, Any]] = []
    provider_transport_log: list[dict[str, Any]] = []
    promotion_clock = iter(
        datetime.fromisoformat(value)
        for value in (
            "2026-08-04T13:00:00+00:00",
            "2026-08-04T13:30:00+00:00",
            "2026-08-04T14:00:00+00:00",
            "2026-08-04T14:30:00+00:00",
        )
    )
    lifecycle_clock = iter(
        (
            "2026-08-04T15:00:00+00:00",
            "2026-08-06T12:00:00+00:00",
            "2026-08-06T12:05:00+00:00",
            "2026-08-07T12:00:00+00:00",
            "2026-08-07T12:05:00+00:00",
        )
    )
    runtime_clock = iter(
        datetime.fromisoformat(value)
        for value in (
            "2026-08-04T13:10:00+00:00",
            "2026-08-04T13:11:00+00:00",
            "2026-08-04T13:12:00+00:00",
            "2026-08-05T12:00:00+00:00",
            "2026-08-05T12:05:00+00:00",
            "2026-08-07T12:10:00+00:00",
        )
    )

    class StudyDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            value = next(promotion_clock)
            return value.astimezone(tz) if tz is not None else value.replace(tzinfo=None)

    class StudyRuntimeDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            value = next(runtime_clock)
            return value.astimezone(tz) if tz is not None else value.replace(tzinfo=None)

    def source_transport(url, params, *, timeout=20.0, **_):
        if url != f"{PROVIDER_BASE}/search":
            raise AssertionError("administrator source escaped the reviewed endpoint")
        source_transport_log.append(
            {"url": url, "params": dict(params), "timeout": timeout}
        )
        payload = {"records": [copy.deepcopy(RECORDS["RD-ALS"])]}
        return payload, {
            "url": url,
            "status_code": 200,
            "content_type": "application/json",
            "response_bytes": len(json.dumps(payload).encode()),
            "peer_ip": "93.184.216.34",
            "redirects": 0,
        }

    def discovery_transport(url, params, *, timeout):
        if url != "https://api.us.socrata.com/api/catalog/v1":
            raise AssertionError("discovery escaped the fixed catalog endpoint")
        payload = _catalog_payload()
        return payload, {
            "status_code": 200,
            "content_type": "application/json",
            "response_bytes": len(json.dumps(payload).encode()),
            "redirects": 0,
        }

    def provider_transport(url, params, *, timeout, headers):
        secret = headers.get("X-Rare-Disease-Key")
        slot = {initial_secret: "initial", rotated_secret: "rotated"}.get(secret)
        if set(headers) != {"X-Rare-Disease-Key"} or slot is None:
            raise AssertionError("provider did not receive the reviewed credential")
        record_id = url.rsplit("/", 1)[-1]
        provider_transport_log.append(
            {
                "credential_slot": slot,
                "endpoint": url,
                "record_id": record_id,
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

    source_removed = False
    try:
        os.environ[ENV_VAR] = initial_secret
        allowed = previous_environment["TOOLUNIVERSE_VSD_ALLOWED_HOSTS"] or ""
        os.environ["TOOLUNIVERSE_VSD_ALLOWED_HOSTS"] = ",".join(
            item for item in (allowed, PROVIDER_HOST) if item
        )
        vsd_tool._safe_get_json = source_transport
        vsd_tool._resolve_public_addresses = lambda host, port: ("93.184.216.34",)
        vsd_discovery._safe_get_json = discovery_transport
        vsd_dynamic_rest._safe_get_json = provider_transport
        vsd_dynamic_rest.datetime = StudyRuntimeDateTime
        vsd_promotion_module.datetime = StudyDateTime
        vsd_lifecycle_module._timestamp = lambda: next(lifecycle_clock)

        initial_universe = ToolUniverse()
        try:
            initial_universe.load_tools(
                include_tools=[
                    "VSDDiscoverAPICandidates",
                    "VSDRegisterSource",
                    "VSDListSources",
                    "VSDQuerySource",
                    "VSDRemoveSource",
                ],
                quiet=True,
            )
            initially_loaded = sorted(initial_universe.all_tool_dict)
            initial_coverage = resolve_capability(initial_universe, CAPABILITY)["data"]
            initial_plan = plan_workflow(
                initial_universe,
                goal=WORKFLOW_GOAL,
                capabilities=WORKFLOW_STEPS,
                limit=5,
            )
            demand_batches = [
                record_plan_demands(
                    initial_plan,
                    {"registry_evidence": PUBLIC_SUMMARY},
                    workspace=demand_workspace,
                    source="scheduled_scan",
                    run_id=f"als-gap-run-{index:03d}",
                    observed_at=f"2026-08-0{index}T12:00:00+00:00",
                )
                for index in range(1, 4)
            ]
            discovery = _tool_data(
                initial_universe,
                "VSDDiscoverAPICandidates",
                {
                    "query": "rare disease genes phenotypes clinical trials",
                    "limit": 5,
                },
            )
        finally:
            initial_universe.close()

        initial_ranking = rank_demands(workspace=demand_workspace)["data"]
        demand_id = initial_ranking["ranked_demands"][0]["demand_id"]
        proposal = export_proposals(
            [demand_id],
            proposal_path,
            reviewed_by="Total System Case Reviewer",
            decision_note=(
                "Selected after three independent workflow preflights found the gap."
            ),
            workspace=demand_workspace,
            created_at="2026-08-04T12:00:00+00:00",
        )
        validate_proposal_export(proposal)

        source_registration = _run_admin(
            [
                "register",
                SOURCE_ID,
                f"{PROVIDER_BASE}/search",
                "--name",
                "Protected rare-disease registry review",
                "--description",
                "Administrator inspection of a protected rare-disease JSON API.",
                "--default-params",
                json.dumps({"disease": "ALS"}),
            ],
            catalog_workspace,
        )
        listed_during_review = _run_admin(["list"], catalog_workspace)
        source_query = _run_admin(
            ["query", SOURCE_ID, "--params", json.dumps({"limit": 1})],
            catalog_workspace,
        )
        source_removal = _run_admin(["remove", SOURCE_ID], catalog_workspace)
        source_removed = source_removal["removed"]
        final_source_list = _run_admin(["list"], catalog_workspace)

        inspection = inspect_openapi_document(baseline_spec)
        candidate = inspection["candidates"][0]
        draft = create_openapi_draft(
            candidate,
            tool_name=TOOL_NAME,
            description=(
                "Retrieve consolidated protected rare-disease evidence by record ID."
            ),
            include_parameters=["recordId"],
            credential_env=ENV_VAR,
            workspace=promotion_workspace,
        )
        evidence = verify_draft(
            draft["draft_id"],
            _verification_cases(),
            workspace=promotion_workspace,
        )
        approval = approve_draft(
            draft["draft_id"],
            reviewed_by="Total System Case Reviewer",
            decision_note=(
                "Approved after three protected disease records passed exact checks."
            ),
            workspace=promotion_workspace,
        )
        publication = publish_draft(
            draft["draft_id"], workspace=promotion_workspace
        )
        unchanged = assess_openapi_drift(
            TOOL_NAME, baseline_spec, workspace=promotion_workspace
        )

        active_universe = ToolUniverse()
        try:
            active_universe.load_tools(
                include_tools=["Tool_Finder_Keyword"], quiet=True
            )
            published_present_before_load = TOOL_NAME in active_universe.all_tool_dict
            active_loaded = load_published_tools(
                active_universe, workspace=promotion_workspace
            )
            post_coverage = resolve_capability(active_universe, CAPABILITY)["data"]
            replanned = plan_workflow(
                active_universe,
                goal=WORKFLOW_GOAL,
                capabilities=WORKFLOW_STEPS,
                limit=5,
            )
            finder = _tool_data(
                active_universe,
                "Tool_Finder_Keyword",
                {
                    "description": RAW_DESCRIPTION,
                    "limit": 5,
                    "include_capability_coverage": True,
                    "capability_request": CAPABILITY,
                },
            )
            first_result = active_universe.run_one_function(
                {"name": TOOL_NAME, "arguments": {"recordId": "RD-ALS"}},
                use_cache=False,
            )
            operation_sha256 = first_result["data"]["provenance"][
                "operation_sha256"
            ]
            os.environ[ENV_VAR] = rotated_secret
            rotated_result = active_universe.run_one_function(
                {"name": TOOL_NAME, "arguments": {"recordId": "RD-DMD"}},
                use_cache=False,
            )
            exact_observation = observe_capability_demand(
                active_universe,
                CAPABILITY,
                public_summary=PUBLIC_SUMMARY,
                source="manual_review",
                event_id="als-gap-resolved-001",
                observed_at="2026-08-05T12:00:00+00:00",
                workspace=demand_workspace,
            )
        finally:
            active_universe.close()

        resolved_history = rank_demands(
            workspace=demand_workspace, include_satisfied=True
        )["data"]
        removal = remove_demand(
            demand_id, workspace=demand_workspace, confirm=True
        )
        closed_ranking = rank_demands(workspace=demand_workspace)["data"]

        breaking = assess_openapi_drift(
            TOOL_NAME, breaking_spec, workspace=promotion_workspace
        )
        suspended = set_publication_state(
            TOOL_NAME,
            "suspended",
            changed_by="Total System Case Reviewer",
            reason="Suspended after the provider declared a new major endpoint.",
            assessment_sha256=breaking["assessment_sha256"],
            workspace=promotion_workspace,
        )
        suspended_universe = ToolUniverse()
        try:
            suspended_loaded = load_published_tools(
                suspended_universe, workspace=promotion_workspace
            )
            suspended_present = TOOL_NAME in suspended_universe.all_tool_dict
        finally:
            suspended_universe.close()

        repaired = assess_openapi_drift(
            TOOL_NAME, baseline_spec, workspace=promotion_workspace
        )
        activated = set_publication_state(
            TOOL_NAME,
            "active",
            changed_by="Total System Case Reviewer",
            reason="Reactivated after the original reviewed contract was confirmed.",
            assessment_sha256=repaired["assessment_sha256"],
            workspace=promotion_workspace,
        )
        final_universe = ToolUniverse()
        try:
            final_loaded = load_published_tools(
                final_universe, workspace=promotion_workspace
            )
            final_result = final_universe.run_one_function(
                {"name": TOOL_NAME, "arguments": {"recordId": "RD-SMA"}},
                use_cache=False,
            )
        finally:
            final_universe.close()
        lifecycle_status = list_publication_states(
            TOOL_NAME, workspace=promotion_workspace
        )["tools"][0]
    finally:
        if not source_removed:
            try:
                _run_admin(["remove", SOURCE_ID], catalog_workspace)
            except Exception:
                pass
        vsd_tool._safe_get_json = original_source_transport
        vsd_tool._resolve_public_addresses = original_resolver
        vsd_discovery._safe_get_json = original_discovery_transport
        vsd_dynamic_rest._safe_get_json = original_dynamic_transport
        vsd_dynamic_rest.datetime = original_dynamic_datetime
        vsd_promotion_module.datetime = original_promotion_datetime
        vsd_lifecycle_module._timestamp = original_lifecycle_timestamp
        for name, value in previous_environment.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value

    proposal_text = proposal_path.read_text(encoding="utf-8")
    ledger_text_before_closure = json.dumps(resolved_history, sort_keys=True)
    persisted_text = "\n".join(
        path.read_text(encoding="utf-8") for path in workspace.rglob("*.json")
    )
    result_text = json.dumps(
        {"first": first_result, "rotated": rotated_result, "final": final_result},
        sort_keys=True,
    )
    exact_record = exact_observation["data"]["demand"]
    plan_before = initial_plan["data"]
    plan_after = replanned["data"]
    initial_step = plan_before["steps"][0]
    post_step = plan_after["steps"][0]
    source_ids_during = [
        item["source_id"] for item in listed_during_review["sources"]
    ]
    forbidden_agent_tools = {
        "VSDRegisterSource",
        "VSDListSources",
        "VSDQuerySource",
        "VSDRemoveSource",
        "VSDRecordDemand",
        "VSDRankDemands",
        "VSDExportProposals",
        "VSDSetPublicationState",
    }
    assertions = {
        "initial_capability_is_missing": (
            initial_coverage["classification"] == "missing"
            and initial_coverage["matches"] == []
        ),
        "initial_workflow_routes_only_real_gap": (
            plan_before["required_gap_count"] == 1
            and initial_step["classification"] == "missing"
            and initial_step["finder_handoff"]["next_tool"]
            == "VSDDiscoverAPICandidates"
            and plan_before["steps"][1]["fulfillment"] == "agent"
            and plan_before["steps"][1]["finder_handoff"]["next_tool"] is None
        ),
        "repeated_private_demand_ranks_first": (
            all(batch["data"]["recorded_count"] == 1 for batch in demand_batches)
            and initial_ranking["matching_demand_count"] == 1
            and initial_ranking["ranked_demands"][0]["priority_score"] == 15
            and initial_ranking["ranked_demands"][0]["total_observations"] == 3
        ),
        "demand_export_is_sanitized_local_and_hash_bound": (
            len(proposal["proposals"]) == 1
            and proposal["transmission"].startswith("none;")
            and len(proposal["export_sha256"]) == 64
            and demand_id not in proposal_text
            and RAW_DESCRIPTION not in proposal_text
        ),
        "administrative_mutations_are_not_agent_facing": (
            forbidden_agent_tools.isdisjoint(initially_loaded)
            and forbidden_agent_tools.isdisjoint(get_tool_registry())
            and forbidden_agent_tools.isdisjoint(get_config_registry())
        ),
        "admin_source_lifecycle_is_complete_and_restored": (
            source_registration["registered"] is True
            and SOURCE_ID in source_ids_during
            and len(source_query["result"]["records"]) == 1
            and source_removal["removed"] is True
            and final_source_list["sources"] == []
            and len(source_transport_log) == 2
        ),
        "api_catalog_candidate_is_inert": (
            discovery["candidate_count"] == 2
            and discovery["candidates"][0]["dataset_id"] == "rare-1234"
            and discovery["candidates"][0]["execution_allowed"] is False
            and discovery["candidates"][0]["approval_state"]
            == "unreviewed_candidate"
        ),
        "openapi_candidate_is_authenticated_inert_and_promotable": (
            inspection["promotable_count"] == 1
            and candidate["execution_allowed"] is False
            and candidate["approval_state"] == "unreviewed_candidate"
            and candidate["auth"]
            == {
                "type": "api_key_header",
                "scheme_name": "registryKey",
                "header": "X-Rare-Disease-Key",
            }
        ),
        "credential_reference_is_persisted_without_value": (
            publication["config"]["vsd_operation"]["auth"]
            == {
                "type": "api_key_header_env",
                "env_var": ENV_VAR,
                "header": "X-Rare-Disease-Key",
            }
            and ENV_VAR in persisted_text
        ),
        "three_protected_verification_cases_pass": (
            evidence["all_cases_passed"] is True and evidence["case_count"] == 3
        ),
        "tool_is_absent_until_explicit_publication_load": (
            published_present_before_load is False and active_loaded == [TOOL_NAME]
        ),
        "post_publication_capability_is_exact": (
            post_coverage["classification"] == "existing_exact"
            and post_coverage["matches"][0]["name"] == TOOL_NAME
            and post_coverage["matches"][0]["operation_match"] is True
        ),
        "replanned_workflow_reuses_published_tool": (
            plan_after["required_gap_count"] == 0
            and post_step["classification"] == "existing_exact"
            and post_step["state"] == "ready_existing"
            and post_step["selected_match"]["name"] == TOOL_NAME
            and plan_after["overall_action"] == "compose_existing_tools"
            and plan_before["registry_sha256"] != plan_after["registry_sha256"]
        ),
        "finder_and_replanner_share_expanded_registry": (
            finder["capability_coverage"]["classification"] == "existing_exact"
            and finder["capability_coverage"]["matches"][0]["name"] == TOOL_NAME
            and finder["capability_coverage"]["registry_sha256"]
            == plan_after["registry_sha256"]
        ),
        "credential_rotation_preserves_operation_identity": (
            first_result["data"]["result"]["record_id"] == "RD-ALS"
            and rotated_result["data"]["result"]["record_id"] == "RD-DMD"
            and rotated_result["data"]["provenance"]["operation_sha256"]
            == operation_sha256
        ),
        "exact_observation_updates_original_demand": (
            exact_record["demand_id"] == demand_id
            and exact_record["observation_counts"] == {
                "exact": 1,
                "missing": 3,
                "partial": 0,
            }
            and exact_record["last_matches"][0] == TOOL_NAME
            and exact_record["unmet_rate"] == 0.75
        ),
        "demand_closure_is_explicit_and_hash_bound": (
            removal["data"]["removed"] is True
            and len(removal["data"]["ledger_sha256"]) == 64
            and closed_ranking["total_demand_count"] == 0
            and closed_ranking["ranked_demands"] == []
        ),
        "breaking_drift_recommends_suspension": (
            unchanged["classification"] == "unchanged"
            and breaking["classification"] == "breaking"
            and breaking["changes"] == ["endpoint"]
            and breaking["suspension_recommended"] is True
        ),
        "suspension_prevents_fresh_loading": (
            suspended["state"] == "suspended"
            and suspended_loaded == []
            and suspended_present is False
        ),
        "repaired_contract_supports_safe_activation": (
            repaired["classification"] == "unchanged"
            and activated["state"] == "active"
            and final_loaded == [TOOL_NAME]
        ),
        "final_reactivated_tool_executes": (
            final_result["status"] == "success"
            and final_result["data"]["result"]["record_id"] == "RD-SMA"
            and final_result["data"]["provenance"]["operation_sha256"]
            == operation_sha256
        ),
        "lifecycle_anchor_and_events_are_consistent": (
            lifecycle_status["state"] == "active"
            and lifecycle_status["revision"] == 2
            and lifecycle_status["lifecycle_managed"] is True
            and lifecycle_status["event_sha256"] == activated["event_sha256"]
            and activated["previous_event_sha256"] == suspended["event_sha256"]
            and bool(publication["lifecycle"]["anchor_id"])
        ),
        "provider_transport_uses_only_reviewed_header": (
            len(provider_transport_log) == 6
            and all(
                entry["endpoint"].startswith(PROVIDER_BASE + "/evidence/")
                and entry["params"] == {}
                for entry in provider_transport_log
            )
        ),
        "secret_values_are_absent_from_artifacts_and_results": all(
            secret not in persisted_text and secret not in result_text
            for secret in secrets
        ),
        "workflow_and_demand_inputs_remain_private": (
            RAW_DESCRIPTION not in proposal_text
            and RAW_DESCRIPTION not in ledger_text_before_closure
            and all(
                marker not in proposal_text and marker not in ledger_text_before_closure
                for marker in (
                    "als-gap-run-001",
                    "als-gap-run-002",
                    "als-gap-run-003",
                    "als-gap-resolved-001",
                )
            )
        ),
        "source_and_credential_environment_is_restored": all(
            os.environ.get(name) == value
            for name, value in previous_environment.items()
        ),
    }
    snapshot = {
        "title": "ALS Demand-To-Reviewed-Tool Total VSD System Study",
        "question": (
            "Can repeated unmet ALS workflow demand safely become a reviewed, "
            "credentialed, lifecycle-managed ToolUniverse capability?"
        ),
        "answer": (
            "Yes. One missing protected registry step was privately ranked and "
            "explicitly proposed, reviewed through source and OpenAPI boundaries, "
            "verified on three diseases, published, reused by planning and Finder, "
            "executed, explicitly closed in the demand ledger, suspended on drift, "
            "and safely reactivated after contract repair."
        ),
        "provider_fixture": (
            "The protected rare-disease provider and fixed catalog response are "
            "deterministic because the repository cannot bundle a live credential. "
            "All registry, planning, demand, admin, inspection, promotion, runtime, "
            "credential, lifecycle, and audit paths use production code."
        ),
        "initial_gap": {
            "capability_id": initial_coverage["capability_id"],
            "classification": initial_coverage["classification"],
            "registry_sha256": initial_coverage["registry_sha256"],
            "plan_id": plan_before["plan_id"],
            "plan_sha256": plan_before["plan_sha256"],
            "overall_action": plan_before["overall_action"],
        },
        "private_demand": {
            "demand_id": demand_id,
            "initial_observation_count": 3,
            "initial_priority_score": initial_ranking["ranked_demands"][0][
                "priority_score"
            ],
            "proposal_id": proposal["proposals"][0]["proposal_id"],
            "proposal_sha256": proposal["export_sha256"],
            "resolved_observation_counts": exact_record["observation_counts"],
            "resolved_unmet_rate": exact_record["unmet_rate"],
            "closure_ledger_sha256": removal["data"]["ledger_sha256"],
            "final_demand_count": closed_ranking["total_demand_count"],
        },
        "source_review": {
            "source_id": SOURCE_ID,
            "probe_result_type": source_registration["source"]["last_probe"][
                "result_type"
            ],
            "query_record_id": source_query["result"]["records"][0]["record_id"],
            "transport_calls": source_transport_log,
            "catalog_restored": final_source_list["sources"] == [],
        },
        "candidate_boundaries": {
            "catalog_candidate_id": discovery["candidates"][0]["candidate_id"],
            "catalog_candidate_execution_allowed": discovery["candidates"][0][
                "execution_allowed"
            ],
            "openapi_candidate_id": candidate["candidate_id"],
            "openapi_candidate_sha256": candidate["candidate_sha256"],
            "openapi_auth": candidate["auth"],
            "openapi_candidate_execution_allowed": candidate["execution_allowed"],
        },
        "promotion": {
            "draft_id": draft["draft_id"],
            "draft_sha256": draft["draft_sha256"],
            "operation_sha256": draft["operation_sha256"],
            "verification_sha256": evidence["verification_sha256"],
            "approval_sha256": approval["approval_sha256"],
            "publication_sha256": publication["publication_sha256"],
            "lifecycle_anchor_id": publication["lifecycle"]["anchor_id"],
            "verification_case_count": evidence["case_count"],
        },
        "expanded_registry": {
            "classification": post_coverage["classification"],
            "selected_tool": post_coverage["matches"][0]["name"],
            "registry_sha256": post_coverage["registry_sha256"],
            "plan_id": plan_after["plan_id"],
            "plan_sha256": plan_after["plan_sha256"],
            "overall_action": plan_after["overall_action"],
            "finder_registry_sha256": finder["capability_coverage"][
                "registry_sha256"
            ],
        },
        "runtime": {
            "loaded_tools": active_loaded,
            "record_ids": [
                first_result["data"]["result"]["record_id"],
                rotated_result["data"]["result"]["record_id"],
                final_result["data"]["result"]["record_id"],
            ],
            "operation_sha256_before_rotation": operation_sha256,
            "operation_sha256_after_rotation": rotated_result["data"][
                "provenance"
            ]["operation_sha256"],
            "transport_log": provider_transport_log,
        },
        "lifecycle": {
            "unchanged_assessment_sha256": unchanged["assessment_sha256"],
            "breaking_assessment_sha256": breaking["assessment_sha256"],
            "repaired_assessment_sha256": repaired["assessment_sha256"],
            "states": [suspended["state"], activated["state"]],
            "event_sha256": [
                suspended["event_sha256"],
                activated["event_sha256"],
            ],
            "suspended_loaded_tools": suspended_loaded,
            "final_loaded_tools": final_loaded,
        },
        "docker_boundary": {
            "pull_request": "https://github.com/mims-harvard/ToolUniverse/pull/420",
            "relationship": (
                "Independent administrator-only Docker provisioning phase; it is "
                "intentionally not callable from this VSD agent workflow."
            ),
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
    if not all(value is True for value in assertions.values()):
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
    demand = snapshot["private_demand"]
    promotion = snapshot["promotion"]
    runtime = snapshot["runtime"]
    lifecycle = snapshot["lifecycle"]
    lines = [
        "# ALS Demand-To-Reviewed-Tool Total VSD System Study",
        "",
        "## Decision Question",
        "",
        snapshot["question"],
        "",
        f"**Result:** {snapshot['answer']}",
        "",
        "## Research Case",
        "",
        "An ALS evidence workflow needed one protected registry operation that "
        "returns a consolidated record of genes, phenotypes, and clinical-trial "
        "identifiers. The initial registry had no operation at the reviewed provider "
        "endpoint, so planning isolated that step as the only tool gap while keeping "
        "the final synthesis agent-native.",
        "",
        snapshot["provider_fixture"],
        "",
        "## Organic Demand Loop",
        "",
        f"Three independent preflights produced demand `{demand['demand_id']}` with "
        f"priority score {demand['initial_priority_score']}. An administrator "
        "explicitly exported one sanitized proposal; no transmission occurred. After "
        "publication, the same demand received one exact observation, reducing its "
        f"historical unmet rate to {demand['resolved_unmet_rate']:.2f}. The local "
        "reviewer then explicitly removed the resolved aggregate; the final demand "
        "count is zero.",
        "",
        "| Demand boundary | SHA-256 |",
        "| --- | --- |",
        f"| Sanitized proposal | `{demand['proposal_sha256']}` |",
        f"| Closed local ledger | `{demand['closure_ledger_sha256']}` |",
        "",
        "## Review And Promotion",
        "",
        "The administrator probed, listed, queried, and removed the provider through "
        "the mutable source CLI. A fixed public catalog search returned inert metadata "
        "candidates. The selected provider contract instead entered through local "
        "OpenAPI inspection, where its header API-key requirement was derived without "
        "a credential value.",
        "",
        "| Boundary | SHA-256 |",
        "| --- | --- |",
        f"| Draft | `{promotion['draft_sha256']}` |",
        f"| Operation | `{promotion['operation_sha256']}` |",
        f"| Verification | `{promotion['verification_sha256']}` |",
        f"| Approval | `{promotion['approval_sha256']}` |",
        f"| Publication | `{promotion['publication_sha256']}` |",
        "",
        "ALS, Duchenne muscular dystrophy, and spinal muscular atrophy records all "
        "passed required-field, nested-path, and exact-identifier checks before "
        "approval.",
        "",
        "## Registry Growth And Use",
        "",
        f"The published tool was absent until explicit loading. The expanded registry "
        f"classified the formerly missing capability as exact and selected "
        f"`{snapshot['expanded_registry']['selected_tool']}`. Workflow replanning "
        "removed the external-discovery handoff, and Tool Finder reported the same "
        "expanded registry digest.",
        "",
        f"The fresh runtime returned `{runtime['record_ids'][0]}` and "
        f"`{runtime['record_ids'][1]}` across credential rotation without changing "
        "operation identity.",
        "",
        "## Drift And Recovery",
        "",
        "A declared provider move from `/v1` to `/v2` was classified as breaking and "
        "recommended suspension. The explicit suspension kept the publication out of "
        "a fresh runtime. A later unchanged assessment of the reviewed `/v1` contract "
        f"permitted explicit activation, after which `{runtime['record_ids'][2]}` "
        "executed successfully.",
        "",
        "| Lifecycle boundary | SHA-256 |",
        "| --- | --- |",
        f"| Initial unchanged assessment | `{lifecycle['unchanged_assessment_sha256']}` |",
        f"| Breaking assessment | `{lifecycle['breaking_assessment_sha256']}` |",
        f"| Suspension event | `{lifecycle['event_sha256'][0]}` |",
        f"| Repaired assessment | `{lifecycle['repaired_assessment_sha256']}` |",
        f"| Activation event | `{lifecycle['event_sha256'][1]}` |",
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
            "## Boundaries",
            "",
            "Raw workflow descriptions and event IDs remain absent from the private "
            "ledger and proposal. Credential values remain absent from persisted "
            "artifacts and results. Candidates remain inert, assessments never change "
            "state automatically, and source, demand, promotion, and lifecycle "
            "mutations remain administrator-controlled.",
            "",
            "Docker provisioning remains the independent administrator-only phase in "
            "[#420](https://github.com/mims-harvard/ToolUniverse/pull/420), as required "
            "by the original security review. It is not part of the agent-callable VSD "
            "workflow tested here.",
            "",
            f"**Case audit SHA-256:** `{snapshot['audit_sha256']}`",
            "",
        ]
    )
    return "\n".join(lines)


def write_artifacts(
    snapshot: dict[str, Any],
    proposal: dict[str, Any],
    json_path: Path = DEFAULT_JSON,
    markdown_path: Path = DEFAULT_MARKDOWN,
    proposal_path: Path = DEFAULT_PROPOSALS,
) -> None:
    validate_snapshot(snapshot)
    validate_proposal_export(proposal)
    for path in (json_path, markdown_path, proposal_path):
        path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(snapshot, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(_markdown(snapshot), encoding="utf-8")
    proposal_path.write_text(
        json.dumps(proposal, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="tooluniverse-vsd-total-") as directory:
        workspace = Path(directory)
        snapshot = run_case(workspace)
        proposal = json.loads(
            (workspace / "reviewed-demand-proposal.json").read_text(encoding="utf-8")
        )
    write_artifacts(snapshot, proposal)
    print(json.dumps({"status": "passed", "audit_sha256": snapshot["audit_sha256"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
