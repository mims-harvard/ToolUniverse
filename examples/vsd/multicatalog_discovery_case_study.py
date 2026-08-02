"""Prove multi-catalog discovery closes a real ToolUniverse capability gap."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

import tooluniverse.vsd_catalog_providers as catalogs
from tooluniverse import (
    ToolUniverse,
    vsd_discovery,
    vsd_dynamic_rest,
)
from tooluniverse import (
    vsd_promotion as promotion_module,
)
from tooluniverse.vsd_demand import (
    export_proposals,
    rank_demands,
    record_plan_demands,
    validate_proposal_export,
)
from tooluniverse.vsd_openapi import inspect_openapi_document
from tooluniverse.vsd_planning import plan_workflow
from tooluniverse.vsd_promotion import (
    VSDPromotionError,
    approve_draft,
    create_openapi_draft,
    load_published_tools,
    publish_draft,
    verify_draft,
)

HERE = Path(__file__).resolve().parent
REPOSITORY = HERE.parents[1]
FIXTURES = REPOSITORY / "tests" / "fixtures" / "vsd_catalogs"
ARTIFACTS = HERE / "artifacts"
DEFAULT_JSON = ARTIFACTS / "multicatalog_discovery_snapshot.json"
DEFAULT_MARKDOWN = ARTIFACTS / "multicatalog_discovery_snapshot.md"
DEFAULT_PROPOSALS = ARTIFACTS / "multicatalog_discovery_demand_proposal.json"

QUERY = "ALS rare disease longitudinal cohort outcomes specialist access"
TOOL_NAME = "VSDRareDiseaseLongitudinalCohort"
ENDPOINT = "https://data.example.gov/resource/abcd-1234.json"
CAPABILITY = {
    "description": (
        "retrieve a rare disease longitudinal cohort record with progression, "
        "genotype, clinical outcome, and specialist access measures"
    ),
    "provider": "data.example.gov",
    "method": "GET",
    "endpoint": ENDPOINT,
    "required_inputs": ["cohort_id"],
    "output_fields": [
        "cohort_id",
        "disease",
        "participants",
        "follow_up_months",
        "progression_score_change",
        "genes",
        "specialist_access_days",
        "active_trial_ids",
    ],
}
WORKFLOW = [
    {"step_id": "cohort_evidence", **CAPABILITY},
    {
        "step_id": "compare_strata",
        "description": (
            "compare progression and specialist access across rare disease cohorts"
        ),
        "fulfillment": "agent",
        "depends_on": ["cohort_evidence"],
    },
]
PUBLIC_SUMMARY = (
    "Rare disease cohort progression genotype outcomes and specialist access"
)
RECORDS = {
    "ALS-NEURO-001": {
        "cohort_id": "ALS-NEURO-001",
        "disease": "Amyotrophic lateral sclerosis",
        "participants": 428,
        "follow_up_months": 36,
        "progression_score_change": -13.4,
        "genes": ["C9orf72", "SOD1", "TARDBP"],
        "specialist_access_days": 47,
        "active_trial_ids": ["NCT05163886", "NCT05619783"],
    },
    "DMD-PED-014": {
        "cohort_id": "DMD-PED-014",
        "disease": "Duchenne muscular dystrophy",
        "participants": 312,
        "follow_up_months": 48,
        "progression_score_change": -8.1,
        "genes": ["DMD"],
        "specialist_access_days": 62,
        "active_trial_ids": ["NCT05096221", "NCT05429372"],
    },
    "SMA-NAT-022": {
        "cohort_id": "SMA-NAT-022",
        "disease": "Spinal muscular atrophy",
        "participants": 196,
        "follow_up_months": 30,
        "progression_score_change": -5.7,
        "genes": ["SMN1", "SMN2"],
        "specialist_access_days": 35,
        "active_trial_ids": ["NCT05337553", "NCT05794139"],
    },
}
EXPECTED_ASSERTIONS = {
    "all_five_catalog_providers_succeeded",
    "catalog_credentials_are_not_persisted",
    "catalog_metadata_remained_inert",
    "cross_catalog_duplicates_were_merged",
    "demand_was_observed_three_times",
    "discovered_endpoint_matches_reviewed_contract",
    "five_distinct_candidates_survived_format_and_relevance_filters",
    "initial_workflow_identified_the_real_gap",
    "irrelevant_and_unusable_records_were_filtered",
    "post_publication_discovery_suppressed_registered_endpoint",
    "published_tool_was_absent_until_explicit_load",
    "published_tool_closed_the_workflow_gap",
    "review_gate_blocked_early_publication",
    "three_complex_cohort_records_executed",
    "three_verification_cases_passed",
    "verification_approval_publication_hash_chain_is_complete",
}


def _digest(value: Any) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _payload(provider: str) -> dict[str, Any]:
    filename = {
        "socrata": "socrata.json",
        "datagov": "datagov.json",
        "data_europa": "data_europa.json",
        "ckan_data_gov_uk": "ckan.json",
        "apis_guru": "apis_guru.json",
    }[provider]
    return json.loads((FIXTURES / filename).read_text(encoding="utf-8"))


def _request(url: str, payload: Any) -> dict[str, Any]:
    return {
        "url": url,
        "status_code": 200,
        "content_type": "application/json",
        "response_bytes": len(json.dumps(payload, sort_keys=True).encode("utf-8")),
        "peer_ip": "93.184.216.34",
        "redirects": 0,
    }


def _record_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "cohort_id": {"type": "string"},
            "disease": {"type": "string"},
            "participants": {"type": "integer", "minimum": 1},
            "follow_up_months": {"type": "integer", "minimum": 1},
            "progression_score_change": {"type": "number"},
            "genes": {"type": "array", "items": {"type": "string"}},
            "specialist_access_days": {"type": "integer", "minimum": 0},
            "active_trial_ids": {
                "type": "array",
                "items": {"type": "string", "pattern": "^NCT[0-9]{8}$"},
            },
        },
        "required": list(CAPABILITY["output_fields"]),
        "additionalProperties": False,
    }


def _specification() -> dict[str, Any]:
    return {
        "openapi": "3.1.0",
        "info": {
            "title": "Rare Disease Longitudinal Cohort API",
            "version": "2.1.0",
        },
        "servers": [{"url": "https://data.example.gov"}],
        "paths": {
            "/resource/abcd-1234.json": {
                "get": {
                    "operationId": "getLongitudinalCohort",
                    "summary": "Retrieve one rare disease longitudinal cohort",
                    "parameters": [
                        {
                            "name": "cohort_id",
                            "in": "query",
                            "required": True,
                            "schema": {
                                "type": "string",
                                "enum": sorted(RECORDS),
                            },
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "One longitudinal cohort record",
                            "content": {
                                "application/json": {"schema": _record_schema()}
                            },
                        }
                    },
                }
            }
        },
    }


def _verification_cases() -> list[dict[str, Any]]:
    return [
        {
            "arguments": {"cohort_id": cohort_id},
            "expect": {
                "result_type": "object",
                "required_fields": list(CAPABILITY["output_fields"]),
                "equals": {"cohort_id": cohort_id},
                "required_paths": [
                    "/genes/0",
                    "/active_trial_ids/0",
                    "/specialist_access_days",
                    "/progression_score_change",
                ],
                "equals_paths": {},
            },
        }
        for cohort_id in RECORDS
    ]


def _tool_data(
    tooluniverse: ToolUniverse, name: str, arguments: dict[str, Any]
) -> dict[str, Any]:
    result = tooluniverse.run_one_function(
        {"name": name, "arguments": arguments}, use_cache=False
    )
    if not isinstance(result, dict) or result.get("status") == "error":
        raise RuntimeError(f"{name} failed: {result!r}")
    return result.get("data", result)


def run_case(workspace: Path) -> dict[str, Any]:
    """Run demand, discovery, promotion, execution, and registry closure."""
    workspace = Path(workspace)
    promotion_workspace = workspace / "promotion"
    demand_workspace = workspace / "demand"
    proposal_path = workspace / "reviewed-demand-proposal.json"
    specification_path = workspace / "rare-cohort-openapi.json"
    workspace.mkdir(parents=True, exist_ok=True)
    specification_path.write_text(
        json.dumps(_specification(), indent=2, sort_keys=True), encoding="utf-8"
    )

    endpoint_to_provider = {value: key for key, value in catalogs._ENDPOINTS.items()}
    catalog_transport_log: list[dict[str, Any]] = []
    provider_transport_log: list[dict[str, Any]] = []
    catalog_secret = "multicatalog-case-key-must-not-be-persisted"
    previous_catalog_key = os.environ.get("TOOLUNIVERSE_DATAGOV_API_KEY")

    def catalog_fetch(url, params=None, **kwargs):
        provider = endpoint_to_provider[url]
        payload = _payload(provider)
        catalog_transport_log.append(
            {
                "provider": provider,
                "endpoint": url,
                "query_params": copy.deepcopy(params or {}),
                "request_header_names": sorted((kwargs.get("headers") or {}).keys()),
                "max_response_bytes": kwargs.get("max_response_bytes", 1_000_000),
            }
        )
        return payload, _request(url, payload)

    def provider_fetch(url, params, *, timeout, **_kwargs):
        if url != ENDPOINT or set(params) != {"cohort_id"}:
            raise AssertionError("published tool escaped its reviewed operation")
        cohort_id = params["cohort_id"]
        provider_transport_log.append(
            {"endpoint": url, "cohort_id": cohort_id, "timeout": timeout}
        )
        payload = copy.deepcopy(RECORDS[cohort_id])
        return payload, _request(url, payload)

    class FixedCatalogDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            value = datetime.fromisoformat("2026-08-01T12:00:00+00:00")
            return (
                value.astimezone(tz) if tz is not None else value.replace(tzinfo=None)
            )

    class FixedPromotionDateTime(datetime):
        counter = 0

        @classmethod
        def now(cls, tz=None):
            cls.counter += 1
            value = datetime.fromisoformat("2026-08-04T12:00:00+00:00").replace(
                minute=cls.counter
            )
            return (
                value.astimezone(tz) if tz is not None else value.replace(tzinfo=None)
            )

    class FixedRuntimeDateTime(datetime):
        counter = 0

        @classmethod
        def now(cls, tz=None):
            cls.counter += 1
            value = datetime.fromisoformat("2026-08-05T12:00:00+00:00").replace(
                minute=cls.counter
            )
            return (
                value.astimezone(tz) if tz is not None else value.replace(tzinfo=None)
            )

    original_discovery_fetch = vsd_discovery._safe_get_json
    original_catalog_datetime = catalogs.datetime
    original_provider_fetch = vsd_dynamic_rest._safe_get_json
    original_promotion_datetime = promotion_module.datetime
    original_runtime_datetime = vsd_dynamic_rest.datetime
    try:
        os.environ["TOOLUNIVERSE_DATAGOV_API_KEY"] = catalog_secret
        vsd_discovery._safe_get_json = catalog_fetch
        catalogs.datetime = FixedCatalogDateTime
        vsd_dynamic_rest._safe_get_json = provider_fetch
        promotion_module.datetime = FixedPromotionDateTime
        vsd_dynamic_rest.datetime = FixedRuntimeDateTime

        initial_universe = ToolUniverse()
        try:
            initial_universe.load_tools(
                include_tools=["VSDDiscoverAPICandidates"], quiet=True
            )
            initial_plan = plan_workflow(
                initial_universe,
                goal=(
                    "Compare genotype-stratified progression and specialist access "
                    "across ALS, DMD, and SMA cohorts"
                ),
                capabilities=WORKFLOW,
                limit=5,
            )
            demand_batches = [
                record_plan_demands(
                    initial_plan,
                    {"cohort_evidence": PUBLIC_SUMMARY},
                    workspace=demand_workspace,
                    source="scheduled_scan",
                    run_id=f"rare-cohort-gap-{index:03d}",
                    observed_at=f"2026-08-0{index}T10:00:00+00:00",
                )
                for index in range(1, 4)
            ]
            discovery = _tool_data(
                initial_universe,
                "VSDDiscoverAPICandidates",
                {
                    "query": QUERY,
                    "providers": list(catalogs.PROVIDER_ORDER),
                    "exclude_registered": True,
                    "limit": 20,
                },
            )
        finally:
            initial_universe.close()

        ranking = rank_demands(workspace=demand_workspace)["data"]
        demand_id = ranking["ranked_demands"][0]["demand_id"]
        proposal = export_proposals(
            [demand_id],
            proposal_path,
            reviewed_by="Multi-Catalog Case Study Reviewer",
            decision_note=(
                "Selected after three independent workflow preflights found the "
                "same missing longitudinal-cohort operation."
            ),
            workspace=demand_workspace,
            created_at="2026-08-04T10:00:00+00:00",
        )
        validate_proposal_export(proposal)

        selected = next(
            candidate
            for candidate in discovery["candidates"]
            if candidate["api_endpoint"] == ENDPOINT
        )
        inspection = inspect_openapi_document(specification_path)
        openapi_candidate = next(
            candidate
            for candidate in inspection["candidates"]
            if candidate["operation_id"] == "getLongitudinalCohort"
        )
        draft = create_openapi_draft(
            openapi_candidate,
            tool_name=TOOL_NAME,
            description=(
                "Retrieve one reviewed rare-disease longitudinal cohort with "
                "progression, genotype, outcome, and specialist-access measures."
            ),
            include_parameters=["cohort_id"],
            workspace=promotion_workspace,
        )
        early_publication_blocked = False
        try:
            publish_draft(draft["draft_id"], workspace=promotion_workspace)
        except VSDPromotionError:
            early_publication_blocked = True
        verification = verify_draft(
            draft["draft_id"],
            _verification_cases(),
            workspace=promotion_workspace,
        )
        approval = approve_draft(
            draft["draft_id"],
            reviewed_by="Multi-Catalog Case Study Reviewer",
            decision_note=(
                "Approved after the exact endpoint contract and three distinct "
                "rare-disease cohort responses passed schema and value checks."
            ),
            workspace=promotion_workspace,
        )
        publication = publish_draft(draft["draft_id"], workspace=promotion_workspace)

        active_universe = ToolUniverse()
        try:
            active_universe.load_tools(
                include_tools=["VSDDiscoverAPICandidates"], quiet=True
            )
            absent_before_load = TOOL_NAME not in active_universe.all_tool_dict
            loaded = load_published_tools(
                active_universe, workspace=promotion_workspace
            )
            executions = [
                _tool_data(
                    active_universe,
                    TOOL_NAME,
                    {"cohort_id": cohort_id},
                )
                for cohort_id in RECORDS
            ]
            final_plan = plan_workflow(
                active_universe,
                goal=(
                    "Compare genotype-stratified progression and specialist access "
                    "across ALS, DMD, and SMA cohorts"
                ),
                capabilities=WORKFLOW,
                limit=5,
            )
            post_publication_discovery = _tool_data(
                active_universe,
                "VSDDiscoverAPICandidates",
                {
                    "query": QUERY,
                    "providers": list(catalogs.PROVIDER_ORDER),
                    "exclude_registered": True,
                    "limit": 20,
                },
            )
        finally:
            active_universe.close()
    finally:
        vsd_discovery._safe_get_json = original_discovery_fetch
        catalogs.datetime = original_catalog_datetime
        vsd_dynamic_rest._safe_get_json = original_provider_fetch
        promotion_module.datetime = original_promotion_datetime
        vsd_dynamic_rest.datetime = original_runtime_datetime
        if previous_catalog_key is None:
            os.environ.pop("TOOLUNIVERSE_DATAGOV_API_KEY", None)
        else:
            os.environ["TOOLUNIVERSE_DATAGOV_API_KEY"] = previous_catalog_key

    initial = initial_plan["data"]
    final = final_plan["data"]
    shared_sources = {source["provider"] for source in selected["catalog_sources"]}
    executed_records = [item["result"] for item in executions]
    hash_chain = {
        "catalog_payloads": [
            provider["provenance"]["payload_sha256"]
            for provider in discovery["provider_results"]
        ],
        "source_document": inspection["source_document_sha256"],
        "candidate": openapi_candidate["candidate_sha256"],
        "draft": draft["draft_sha256"],
        "verification": verification["verification_sha256"],
        "approval": approval["approval_sha256"],
        "publication": publication["publication_sha256"],
    }
    assertions = {
        "all_five_catalog_providers_succeeded": (
            discovery["successful_provider_count"] == 5
            and discovery["failed_provider_count"] == 0
        ),
        "catalog_credentials_are_not_persisted": catalog_secret
        not in json.dumps(
            {"discovery": discovery, "transport": catalog_transport_log},
            sort_keys=True,
        ),
        "catalog_metadata_remained_inert": all(
            candidate["execution_allowed"] is False
            and candidate["approval_state"] == "unreviewed_candidate"
            for candidate in discovery["candidates"]
        ),
        "cross_catalog_duplicates_were_merged": (
            discovery["cross_catalog_duplicate_count"] == 2
            and shared_sources == {"datagov", "socrata"}
        ),
        "demand_was_observed_three_times": (
            len(demand_batches) == 3
            and ranking["ranked_demands"][0]["observation_counts"]["missing"] == 3
        ),
        "discovered_endpoint_matches_reviewed_contract": (
            selected["api_endpoint"]
            == f"{openapi_candidate['server_url']}{openapi_candidate['path']}"
            == draft["config"]["vsd_operation"]["endpoint"]
        ),
        "five_distinct_candidates_survived_format_and_relevance_filters": (
            discovery["candidate_count"] == 5
            and len({item["candidate_id"] for item in discovery["candidates"]}) == 5
            and all(
                item["score"]["matched_query_terms"] >= 2
                for item in discovery["candidates"]
            )
        ),
        "initial_workflow_identified_the_real_gap": (
            initial["steps"][0]["classification"] == "missing"
            and initial["steps"][0]["finder_handoff"]["next_tool"]
            == "VSDDiscoverAPICandidates"
        ),
        "irrelevant_and_unusable_records_were_filtered": (
            discovery["catalog_result_count"] == 10
            and discovery["candidate_count"] == 5
            and not any(
                "weather" in item["name"].casefold()
                or item["response_format"] in {"html", "zip"}
                for item in discovery["candidates"]
            )
        ),
        "post_publication_discovery_suppressed_registered_endpoint": (
            post_publication_discovery["registered_duplicate_count"] == 1
            and any(
                duplicate["identity"] == ENDPOINT and TOOL_NAME in duplicate["matches"]
                for duplicate in post_publication_discovery["registered_duplicates"]
            )
            and not any(
                item["api_endpoint"] == ENDPOINT
                for item in post_publication_discovery["candidates"]
            )
        ),
        "published_tool_was_absent_until_explicit_load": (
            absent_before_load and loaded == [TOOL_NAME]
        ),
        "published_tool_closed_the_workflow_gap": (
            final["steps"][0]["classification"] == "existing_exact"
            and final["steps"][0]["selected_match"]["name"] == TOOL_NAME
            and final["overall_action"] == "compose_existing_tools"
        ),
        "review_gate_blocked_early_publication": early_publication_blocked,
        "three_complex_cohort_records_executed": (
            [record["cohort_id"] for record in executed_records] == list(RECORDS)
            and all(
                record["genes"] and record["active_trial_ids"]
                for record in executed_records
            )
            and len(provider_transport_log) == 6
        ),
        "three_verification_cases_passed": verification["case_count"] == 3,
        "verification_approval_publication_hash_chain_is_complete": (
            approval["verification_sha256"] == verification["verification_sha256"]
            and publication["approval_sha256"] == approval["approval_sha256"]
            and all(
                len(value) == 64
                for key, value in hash_chain.items()
                if key != "catalog_payloads"
            )
            and all(len(value) == 64 for value in hash_chain["catalog_payloads"])
        ),
    }
    snapshot = {
        "title": "Multi-Catalog Rare-Disease Capability Growth Study",
        "question": (
            "Can repeated demand for genotype-stratified rare-disease progression "
            "and specialist-access evidence become a reviewed ToolUniverse tool?"
        ),
        "answer": (
            "Yes. Five verified catalogs yielded five relevant inert candidates; "
            "duplicate US listings converged on one endpoint, an administrator "
            "reviewed its contract, three disease cohorts passed verification, and "
            "the published tool closed the workflow gap."
        ),
        "fixture_boundary": (
            "Deterministic catalog and cohort responses replace network transport. "
            "Agent invocation, provider dispatch, normalization, ranking, deduplication, "
            "registry comparison, demand, planning, OpenAPI inspection, promotion, "
            "verification, publication, loading, execution, and provenance use production code."
        ),
        "initial_gap": {
            "classification": initial["steps"][0]["classification"],
            "overall_action": initial["overall_action"],
            "plan_sha256": initial["plan_sha256"],
            "demand_id": demand_id,
            "demand_observations": ranking["ranked_demands"][0]["observation_counts"],
            "proposal_sha256": proposal["export_sha256"],
        },
        "catalog_search": {
            "query": QUERY,
            "provider_results": discovery["provider_results"],
            "catalog_result_count": discovery["catalog_result_count"],
            "candidate_count": discovery["candidate_count"],
            "cross_catalog_duplicate_count": discovery["cross_catalog_duplicate_count"],
            "candidates": discovery["candidates"],
            "transport_log": catalog_transport_log[:5],
        },
        "selected_handoff": {
            "candidate_id": selected["candidate_id"],
            "endpoint": selected["api_endpoint"],
            "catalog_sources": selected["catalog_sources"],
            "openapi_candidate_id": openapi_candidate["candidate_id"],
            "openapi_candidate_sha256": openapi_candidate["candidate_sha256"],
            "operation_id": openapi_candidate["operation_id"],
            "blockers": openapi_candidate["blockers"],
        },
        "promotion": {
            "tool_name": TOOL_NAME,
            "verification_case_count": verification["case_count"],
            "loaded_tools": loaded,
            "hash_chain": hash_chain,
        },
        "executed_cohorts": executed_records,
        "provider_transport_log": provider_transport_log,
        "closed_gap": {
            "classification": final["steps"][0]["classification"],
            "selected_tool": final["steps"][0]["selected_match"]["name"],
            "overall_action": final["overall_action"],
            "plan_sha256": final["plan_sha256"],
            "registered_duplicate_count": post_publication_discovery[
                "registered_duplicate_count"
            ],
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
    initial = snapshot["initial_gap"]
    search = snapshot["catalog_search"]
    selected = snapshot["selected_handoff"]
    promotion = snapshot["promotion"]
    closed = snapshot["closed_gap"]
    lines = [
        "# Multi-Catalog Rare-Disease Capability Growth Study",
        "",
        "## Evaluation Objective",
        "",
        snapshot["question"],
        "",
        f"**Result:** {snapshot['answer']}",
        "",
        "## Evaluation Context",
        "",
        (
            "A comparative ALS, Duchenne muscular dystrophy, and spinal muscular atrophy "
            "workflow needed longitudinal progression, genotype, clinical-outcome, and "
            "specialist-access measures from one machine-readable cohort operation. The "
            "existing registry could not satisfy that operation, so planning produced a "
            "specific discovery handoff rather than treating a related tool as exact coverage."
        ),
        "",
        snapshot["fixture_boundary"],
        "",
        "## Demand Evidence",
        "",
        (
            f"Three independent preflights recorded the same missing capability as "
            f"`{initial['demand_id']}`. The reviewed local proposal is bound by "
            f"`{initial['proposal_sha256']}`; exporting it did not submit or approve a tool."
        ),
        "",
        "## Five-Catalog Search",
        "",
        (
            f"The agent-facing discovery tool searched all five providers and inspected "
            f"{search['catalog_result_count']} catalog records. Format, URL, and relevance "
            f"filters retained {search['candidate_count']} inert candidates. Two duplicate "
            "records were collapsed by exact endpoint/specification identity."
        ),
        "",
        "| Provider | Catalog records | Candidates | Status |",
        "| --- | ---: | ---: | --- |",
    ]
    lines.extend(
        f"| `{item['provider_id']}` | {item['catalog_result_count']} | "
        f"{item['candidate_count']} | {item['status']} |"
        for item in search["provider_results"]
    )
    lines.extend(
        [
            "",
            "| Candidate | Catalog evidence | Format | Matched terms | Score |",
            "| --- | --- | --- | ---: | ---: |",
        ]
    )
    for candidate in search["candidates"]:
        safe_name = candidate["name"].replace("|", "\\|")
        sources = ", ".join(
            sorted(source["provider"] for source in candidate["catalog_sources"])
        )
        lines.append(
            f"| {safe_name} | {sources} | "
            f"`{candidate['interface_type']}/{candidate['response_format']}` | "
            f"{candidate['score']['matched_query_terms']} | "
            f"{candidate['score']['total']:.4f} |"
        )
    lines.extend(
        [
            "",
            (
                "The APIs.guru result is an OpenAPI lead; the government-catalog results "
                "are endpoint leads. Neither form becomes executable. Catalog provenance "
                "is evidence for review, not approval or scientific endorsement."
            ),
            "",
            "## Contract Review and Promotion",
            "",
            (
                f"Data.gov and Socrata independently pointed to `{selected['endpoint']}`. "
                "An administrator obtained and inspected the provider contract, selected "
                f"`{selected['operation_id']}`, and confirmed that the contract endpoint "
                "matched the discovered identity. Publication was rejected before "
                "verification and approval."
            ),
            "",
            "| Promotion boundary | SHA-256 |",
            "| --- | --- |",
            f"| Catalog candidate | `{selected['candidate_id']}` |",
            f"| OpenAPI candidate | `{selected['openapi_candidate_sha256']}` |",
            f"| Draft | `{promotion['hash_chain']['draft']}` |",
            f"| Verification | `{promotion['hash_chain']['verification']}` |",
            f"| Approval | `{promotion['hash_chain']['approval']}` |",
            f"| Publication | `{promotion['hash_chain']['publication']}` |",
            "",
            "## End-to-End Execution",
            "",
            (
                "Three records passed the reviewed response schema, required nested-value "
                "checks, and exact cohort-identifier checks. After explicit loading into "
                "a fresh ToolUniverse instance, the same three cohort calls executed:"
            ),
            "",
            "| Cohort | Disease | Participants | Follow-up | Progression change | Access wait |",
            "| --- | --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for record in snapshot["executed_cohorts"]:
        lines.append(
            f"| `{record['cohort_id']}` | {record['disease']} | "
            f"{record['participants']} | {record['follow_up_months']} months | "
            f"{record['progression_score_change']} | "
            f"{record['specialist_access_days']} days |"
        )
    lines.extend(
        [
            "",
            "## Post-Publication Registry Validation",
            "",
            (
                f"Replanning classified the original gap as `{closed['classification']}` "
                f"and selected `{closed['selected_tool']}`. Repeating the same catalog "
                "search then removed the already-registered endpoint and returned an "
                "auditable duplicate reason, preventing the growth loop from proposing it again."
            ),
            "",
            "## Validation Results",
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
            "## Interpretation Limits",
            "",
            (
                "This evaluation covers discovery and software-governance behavior against "
                "deterministic provider fixtures. It does not certify the scientific "
                "quality of a catalog record, approve a provider automatically, or let "
                "an agent bypass contract review and human approval."
            ),
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
    with tempfile.TemporaryDirectory(prefix="tooluniverse-vsd-catalogs-") as directory:
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
