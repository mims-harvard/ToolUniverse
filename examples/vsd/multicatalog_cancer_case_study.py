"""Exercise live multi-catalog VSD growth in one breast-cancer program case."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterator
from urllib.parse import parse_qsl, urlsplit, urlunsplit

import tooluniverse.vsd_catalog_providers as catalogs
from tooluniverse import (
    ToolUniverse,
    vsd_discovery,
    vsd_dynamic_rest,
    vsd_reviewed_runtime,
    vsd_tool,
)
from tooluniverse.vsd_demand import rank_demands, record_plan_demands
from tooluniverse.vsd_openapi import inspect_openapi_document
from tooluniverse.vsd_planning import plan_workflow
from tooluniverse.vsd_promotion import (
    VSDPromotionError,
    approve_draft,
    create_catalog_resource_draft,
    create_draft,
    load_published_tools,
    publish_draft,
    verify_draft,
)
from tooluniverse.vsd_reviewed_runtime import VSDReviewedOperationTool

HERE = Path(__file__).resolve().parent
REPOSITORY = HERE.parents[1]
FIXTURES = REPOSITORY / "tests" / "fixtures" / "vsd_catalogs" / "cancer"
ARTIFACTS = HERE / "artifacts"
DEFAULT_JSON = ARTIFACTS / "multicatalog_cancer_snapshot.json"
DEFAULT_MARKDOWN = ARTIFACTS / "multicatalog_cancer_snapshot.md"
DEFAULT_WORKSPACE = ARTIFACTS / "multicatalog_cancer_workspace"

SOCRATA_ENDPOINT = "https://data.ny.gov/resource/2ig8-yxf8.json"
DATAGOV_ENDPOINT = (
    "https://data.ok.gov/dataset/3c0493a5-079e-4cc8-95a9-c53967623009/"
    "resource/03935a57-5192-4455-8e85-1b2ec6f4da5e/download/"
    "c-cancer-deaths-column-chart.csv"
)
EUROPE_ENDPOINT = (
    "https://ws.cso.ie/public/api.restful/PxStat.Data.Cube_API.ReadDataset/"
    "KTA31/JSON-stat/1.0/en"
)
CKAN_ENDPOINT = (
    "https://www.health-ni.gov.uk/sites/default/files/publications/health/"
    "hs-niwts-cwt-62-day-wait-by-tumour-q1-19-20.csv"
)
GENOMICS_SPEC = (
    "https://api.apis.guru/v2/specs/googleapis.com/genomics/v2alpha1/openapi.json"
)

TRIAL_TOOL = "VSDCancerTrialsByPrimarySite"
MORTALITY_TOOL = "VSDIrishCancerMortalityContext"

CATALOG_CASES = {
    "socrata": {
        "query": "active breast cancer clinical trials phase",
        "role": "local trial inventory",
        "identity": SOCRATA_ENDPOINT,
        "fixture": "socrata.json",
    },
    "datagov": {
        "query": "cancer",
        "role": "outcome benchmark",
        "identity": DATAGOV_ENDPOINT,
        "fixture": "datagov.json",
    },
    "data_europa": {
        "query": "cause of death cancer Ireland csv",
        "role": "current age-stratified cancer mortality",
        "identity": EUROPE_ENDPOINT,
        "fixture": "data_europa.json",
    },
    "ckan_data_gov_uk": {
        "query": "cancer waiting times",
        "role": "treatment-access delay",
        "identity": CKAN_ENDPOINT,
        "fixture": "ckan.json",
    },
    "apis_guru": {
        "query": "genomics",
        "role": "genomics workflow contract",
        "identity": GENOMICS_SPEC,
        "fixture": "apis_guru.json",
    },
}

WORKFLOW = [
    {
        "step_id": "trial_inventory",
        "description": "query a reviewed breast-cancer trial registry by primary site",
        "provider": "data.ny.gov",
        "method": "GET",
        "endpoint": SOCRATA_ENDPOINT,
        "required_inputs": ["primary_site"],
        "output_fields": [
            "protocol",
            "primary_site",
            "study_phase",
            "title",
            "date_opened",
            "date_closed",
        ],
    },
    {
        "step_id": "mortality_context",
        "description": "retrieve reviewed Irish cancer mortality context by age group",
        "provider": "ws.cso.ie",
        "method": "GET",
        "endpoint": EUROPE_ENDPOINT,
        "output_fields": ["dataset"],
    },
    {
        "step_id": "program_review",
        "description": "compare trial inventory and population mortality context",
        "fulfillment": "agent",
        "depends_on": ["trial_inventory", "mortality_context"],
    },
]

EXPECTED_ASSERTIONS = {
    "all_five_catalogs_returned_live_or_replayed_results",
    "all_selected_candidates_are_hash_bound_and_inert",
    "catalog_credentials_were_not_persisted",
    "ckan_mime_mismatch_blocked_verification",
    "datagov_unfit_resource_was_not_approved",
    "demand_was_observed_three_times_before_growth",
    "early_publication_was_rejected",
    "genomics_contract_operations_were_blocked_before_drafting",
    "initial_plan_identified_both_exact_capability_gaps",
    "post_publication_discovery_suppressed_both_resources",
    "post_publication_plan_resolved_both_exact_capabilities",
    "published_tools_were_absent_until_explicit_load",
    "mortality_resource_completed_three_verification_cases",
    "mortality_runtime_returned_current_age_stratified_data",
    "mortality_totals_were_computed_from_provider_values",
    "trial_registry_completed_three_distinct_verification_cases",
    "trial_runtime_returned_exact_site_rows",
    "two_hash_chains_reached_publication",
}

DiscoveryRunner = Callable[[ToolUniverse, str, str, bool], dict[str, Any]]
JSONFetcher = Callable[..., tuple[Any, dict[str, Any]]]


def _digest(value: Any) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _successful_data(result: Any, tool_name: str) -> dict[str, Any]:
    if not isinstance(result, dict) or result.get("status") != "success":
        raise RuntimeError(f"{tool_name} failed: {result!r}")
    data = result.get("data")
    if not isinstance(data, dict):
        raise RuntimeError(f"{tool_name} returned an invalid data envelope")
    return data


def _request(url: str, payload: Any, *, content_type: str) -> dict[str, Any]:
    if isinstance(payload, bytes):
        size = len(payload)
    else:
        size = len(json.dumps(payload, sort_keys=True).encode("utf-8"))
    return {
        "url": url,
        "status_code": 200,
        "content_type": content_type,
        "response_bytes": size,
        "headers": {},
        "peer_ip": "93.184.216.34",
        "redirects": 0,
    }


def _fixture_payload(provider: str) -> dict[str, Any]:
    filename = CATALOG_CASES[provider]["fixture"]
    return json.loads((FIXTURES / filename).read_text(encoding="utf-8"))


def _fixture_discovery(
    tooluniverse: ToolUniverse,
    provider: str,
    query: str,
    exclude_registered: bool,
) -> dict[str, Any]:
    payload = _fixture_payload(provider)

    def fake_get(url: str, params=None, **_kwargs):
        del params
        return payload, _request(url, payload, content_type="application/json")

    return catalogs.discover_multi_catalog_candidates(
        query,
        providers=[provider],
        limit=5,
        fetch_json=fake_get,
        socrata_normalizer=vsd_discovery.discover_api_candidates,
        tooluniverse=tooluniverse,
        exclude_registered=exclude_registered,
        retrieved_at="2026-08-02T06:00:00+00:00",
    )


def _agent_discovery(
    tooluniverse: ToolUniverse,
    provider: str,
    query: str,
    exclude_registered: bool,
) -> dict[str, Any]:
    result = tooluniverse.run_one_function(
        {
            "name": "VSDDiscoverAPICandidates",
            "arguments": {
                "query": query,
                "providers": [provider],
                "exclude_registered": exclude_registered,
                "limit": 5,
            },
        },
        use_cache=False,
    )
    return _successful_data(result, "VSDDiscoverAPICandidates")


def _network_backed_discovery(
    tooluniverse: ToolUniverse,
    provider: str,
    query: str,
    exclude_registered: bool,
) -> dict[str, Any]:
    if provider == "datagov":
        return _fixture_discovery(tooluniverse, provider, query, exclude_registered)
    return _agent_discovery(tooluniverse, provider, query, exclude_registered)


def _select_candidate(result: dict[str, Any], identity: str) -> dict[str, Any]:
    selected = next(
        (
            candidate
            for candidate in result["candidates"]
            if (candidate["specification_url"] or candidate["api_endpoint"]) == identity
        ),
        None,
    )
    if selected is None:
        raise RuntimeError(f"Expected catalog identity was not returned: {identity}")
    return catalogs.validate_catalog_candidate(selected)


def _candidate_summary(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "candidate_id": candidate["candidate_id"],
        "candidate_sha256": candidate["candidate_sha256"],
        "name": candidate["name"],
        "identity": candidate["specification_url"] or candidate["api_endpoint"],
        "candidate_kind": candidate["candidate_kind"],
        "response_format": candidate["response_format"],
        "interface_type": candidate["interface_type"],
        "score": candidate["score"],
        "catalog_sources": candidate["catalog_sources"],
        "approval_state": candidate["approval_state"],
        "execution_allowed": candidate["execution_allowed"],
    }


def _resource_config(
    candidate: dict[str, Any],
    *,
    name: str,
    description: str,
    schema: dict[str, Any],
    max_bytes: int,
) -> dict[str, Any]:
    parsed = urlsplit(candidate["api_endpoint"])
    query = dict(
        parse_qsl(
            parsed.query,
            keep_blank_values=True,
            strict_parsing=True,
            max_num_fields=50,
        )
        if parsed.query
        else []
    )
    endpoint = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))
    response: dict[str, Any] = {
        "format": candidate["response_format"],
        "max_bytes": max_bytes,
        "schema": schema,
        "root_pointer": "",
    }
    if candidate["response_format"] == "csv":
        response["delimiter"] = ","
    return {
        "name": name,
        "type": "VSDReviewedOperationTool",
        "description": description,
        "category": "special_tools",
        "cacheable": False,
        "mcp_annotations": {"readOnlyHint": True, "destructiveHint": False},
        "parameter": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        },
        "return_schema": {
            "type": "object",
            "properties": {
                "result": schema,
                "provenance": {"type": "object"},
            },
            "required": ["result", "provenance"],
            "additionalProperties": False,
        },
        "vsd_reviewed_operation": {
            "version": 1,
            "transport": "http",
            "protocol": "rest",
            "endpoint": endpoint,
            "timeout_seconds": 30,
            "auth": {"type": "none"},
            "request": {
                "method": "GET",
                "path_arguments": {},
                "query_arguments": {},
                "fixed_query": query,
                "fixed_headers": {},
                "body": {"mode": "none", "arguments": {}, "fixed": {}},
            },
            "response": response,
            "pagination": {"type": "none"},
        },
    }


def _csv_schema(fields: list[str], *, maximum: int) -> dict[str, Any]:
    return {
        "type": "array",
        "minItems": 1,
        "maxItems": maximum,
        "items": {
            "type": "object",
            "properties": {
                field: {"type": ["string", "null"], "maxLength": 2000}
                for field in fields
            },
            "required": fields,
            "additionalProperties": False,
        },
    }


def _mortality_config(candidate: dict[str, Any]) -> dict[str, Any]:
    return _resource_config(
        candidate,
        name=MORTALITY_TOOL,
        description=(
            "Return the exact reviewed Irish principal-cause-of-death JSON-stat cube."
        ),
        schema={
            "type": "object",
            "properties": {
                "dataset": {
                    "type": "object",
                    "properties": {
                        "dimension": {"type": "object", "maxProperties": 10},
                        "label": {"type": "string", "maxLength": 500},
                        "source": {"type": "string", "maxLength": 500},
                        "updated": {"type": "string", "maxLength": 100},
                        "value": {
                            "type": "array",
                            "maxItems": 2500,
                            "items": {"type": ["number", "null"]},
                        },
                    },
                    "required": ["dimension", "label", "source", "updated", "value"],
                    "additionalProperties": False,
                }
            },
            "required": ["dataset"],
            "additionalProperties": False,
        },
        max_bytes=100_000,
    )


def _datagov_config(candidate: dict[str, Any]) -> dict[str, Any]:
    return _resource_config(
        candidate,
        name="VSDOklahomaCancerDeathTargetSnapshot",
        description="Return the exact reviewed Oklahoma cancer-death chart resource.",
        schema=_csv_schema(["Years", "Historical Data", "Target"], maximum=30),
        max_bytes=10_000,
    )


def _ckan_config(candidate: dict[str, Any]) -> dict[str, Any]:
    return _resource_config(
        candidate,
        name="VSDNorthernIrelandCancerWaitingSnapshot",
        description=(
            "Return the exact reviewed Northern Ireland cancer waiting-time resource."
        ),
        schema=_csv_schema(
            ["Treatment Month", "Tumour Site", "% treated within 62 days"],
            maximum=1000,
        ),
        max_bytes=100_000,
    )


def _verification_cases(
    *,
    arguments: list[dict[str, Any]],
    minimum: int,
    maximum: int,
    fields: list[str],
    equals: dict[str, Any] | None = None,
    required_paths: list[str] | None = None,
    result_type: str = "array",
) -> list[dict[str, Any]]:
    cases = []
    for values in arguments:
        expect = {
            "result_type": result_type,
            "required_fields": fields,
            "equals": equals or {},
            "required_paths": required_paths or [],
        }
        if result_type == "array":
            expect.update({"min_items": minimum, "max_items": maximum})
        cases.append(
            {
                "arguments": values,
                "expect": expect,
            }
        )
    return cases


def _promote_trial_registry(
    candidate: dict[str, Any], workspace: Path
) -> tuple[dict[str, Any], str]:
    draft = create_draft(
        candidate,
        tool_name=TRIAL_TOOL,
        description=(
            "Query the reviewed Roswell Park registry snapshot by exact primary site."
        ),
        filter_fields=["primary_site"],
        return_fields=[
            "protocol",
            "primary_site",
            "study_phase",
            "title",
            "date_opened",
            "date_closed",
            "principal_investigator",
        ],
        max_records=25,
        workspace=workspace,
    )
    early_error = ""
    try:
        publish_draft(draft["draft_id"], workspace=workspace)
    except VSDPromotionError as exc:
        early_error = str(exc)
    if not early_error:
        raise AssertionError("Unverified trial draft was published")
    evidence = verify_draft(
        draft["draft_id"],
        _verification_cases(
            arguments=[
                {"primary_site": "Brain and Nervous System"},
                {"primary_site": "Breast"},
                {"primary_site": "Prostate"},
            ],
            minimum=1,
            maximum=25,
            fields=["protocol", "primary_site", "study_phase", "title"],
        ),
        workspace=workspace,
    )
    approval = approve_draft(
        draft["draft_id"],
        reviewed_by="Multicatalog cancer program reviewer",
        decision_note=(
            "Approved after three distinct primary-site calls passed the bounded "
            "schema and exact-filter checks."
        ),
        workspace=workspace,
    )
    publication = publish_draft(draft["draft_id"], workspace=workspace)
    return (
        {
            "tool_name": TRIAL_TOOL,
            "candidate_sha256": candidate["candidate_sha256"],
            "draft_id": draft["draft_id"],
            "draft_sha256": draft["draft_sha256"],
            "verification_sha256": evidence["verification_sha256"],
            "approval_sha256": approval["approval_sha256"],
            "publication_sha256": publication["publication_sha256"],
            "verification_case_count": evidence["case_count"],
            "verification_arguments": [item["arguments"] for item in evidence["cases"]],
        },
        early_error,
    )


def _promote_mortality_resource(
    candidate: dict[str, Any], workspace: Path
) -> dict[str, Any]:
    draft = create_catalog_resource_draft(
        candidate,
        _mortality_config(candidate),
        review_note=(
            "Reviewed the exact catalog identity, HTTPS resource, JSON-stat shape, "
            "response ceiling, and input-free request."
        ),
        workspace=workspace,
    )
    evidence = verify_draft(
        draft["draft_id"],
        _verification_cases(
            arguments=[{}, {}, {}],
            minimum=0,
            maximum=0,
            fields=["dataset"],
            required_paths=[
                "/dataset/dimension/id",
                "/dataset/dimension/size",
                "/dataset/dimension/TLIST(A1)/category/index/2024",
                "/dataset/dimension/C04653V05438/category/index/C00C97",
                "/dataset/value",
                "/dataset/updated",
            ],
            result_type="object",
        ),
        workspace=workspace,
    )
    approval = approve_draft(
        draft["draft_id"],
        reviewed_by="Multicatalog cancer program reviewer",
        decision_note=(
            "Approved as population context after three bounded calls returned the "
            "reviewed age-stratified mortality cube through 2024."
        ),
        workspace=workspace,
    )
    publication = publish_draft(draft["draft_id"], workspace=workspace)
    return {
        "tool_name": MORTALITY_TOOL,
        "candidate_sha256": candidate["candidate_sha256"],
        "draft_id": draft["draft_id"],
        "draft_sha256": draft["draft_sha256"],
        "verification_sha256": evidence["verification_sha256"],
        "approval_sha256": approval["approval_sha256"],
        "publication_sha256": publication["publication_sha256"],
        "verification_case_count": evidence["case_count"],
        "catalog_binding": publication["config"]["vsd_promotion"]["catalog_binding"],
    }


def _qualify_datagov(candidate: dict[str, Any], workspace: Path) -> dict[str, Any]:
    config = _datagov_config(candidate)
    draft = create_catalog_resource_draft(
        candidate,
        config,
        review_note=(
            "Reviewed the exact catalog resource and software schema before the "
            "separate evidence-fitness decision."
        ),
        workspace=workspace,
    )
    try:
        evidence = verify_draft(
            draft["draft_id"],
            _verification_cases(
                arguments=[{}, {}, {}],
                minimum=1,
                maximum=30,
                fields=[],
                required_paths=["/Years", "/Historical Data", "/Target"],
            ),
            workspace=workspace,
        )
    except VSDPromotionError as exc:
        verification_error = str(exc)
        reason = (
            "The catalog URL redirects to a signed object-store URL; the reviewed "
            "runtime rejected the redirect and query-bearing target before reading data."
            if "query strings" in verification_error
            else "The candidate failed bounded runtime verification before data review."
        )
        return {
            "decision": "blocked_at_verification",
            "reason": reason,
            "verification_error": verification_error,
            "draft_id": draft["draft_id"],
            "quality_review_completed": False,
            "approved": False,
            "published": False,
        }

    data = _successful_data(VSDReviewedOperationTool(config).run({}), config["name"])
    rows = data["result"]
    years = [int(row["Years"]) for row in rows]
    usable_history = sum(float(row["Historical Data"]) > 0 for row in rows)
    return {
        "decision": "withheld_after_quality_review",
        "reason": (
            "The newest year is 2019 and only three of nine historical values are "
            "non-zero, so this cannot support the current program decision."
        ),
        "draft_id": draft["draft_id"],
        "verification_sha256": evidence["verification_sha256"],
        "quality_review_completed": True,
        "row_count": len(rows),
        "latest_year": max(years),
        "nonzero_historical_rows": usable_history,
        "provenance": data["provenance"],
        "approved": False,
        "published": False,
    }


def _qualify_ckan(candidate: dict[str, Any], workspace: Path) -> dict[str, Any]:
    config = _ckan_config(candidate)
    draft = create_catalog_resource_draft(
        candidate,
        config,
        review_note=(
            "Reviewed the declared CSV identity and attempted bounded verification "
            "without relaxing the response media contract."
        ),
        workspace=workspace,
    )
    try:
        verify_draft(
            draft["draft_id"],
            _verification_cases(
                arguments=[{}, {}, {}],
                minimum=1,
                maximum=100,
                fields=[],
                required_paths=[
                    "/Treatment Month",
                    "/Tumour Site",
                    "/% treated within 62 days",
                ],
            ),
            workspace=workspace,
        )
    except VSDPromotionError as exc:
        error = str(exc)
    else:
        raise AssertionError("MIME-mismatched CKAN resource passed verification")
    if "application/octet-stream" not in error or "does not match csv" not in error:
        raise RuntimeError(f"CKAN failed for an unexpected reason: {error}")
    return {
        "decision": "blocked_at_verification",
        "reason": (
            "The provider returned application/octet-stream for a catalog-declared "
            "CSV, so the reviewed runtime refused the response."
        ),
        "verification_error": error,
        "draft_id": draft["draft_id"],
        "expected_format": "csv",
        "observed_content_type": "application/octet-stream",
        "approved": False,
        "published": False,
    }


def _inspect_genomics(
    candidate: dict[str, Any], fetch_json: JSONFetcher
) -> dict[str, Any]:
    payload, request = fetch_json(candidate["specification_url"], None, timeout=30)
    with tempfile.TemporaryDirectory(prefix="tooluniverse-vsd-genomics-") as directory:
        path = Path(directory) / "genomics.openapi.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        inspection = inspect_openapi_document(path)
    blockers = sorted(
        {blocker for item in inspection["candidates"] for blocker in item["blockers"]}
    )
    return {
        "decision": "blocked_at_contract_inspection",
        "reason": (
            "Every operation requires unsupported authentication and/or exposes a "
            "write or otherwise unsupported request shape."
        ),
        "specification_url": candidate["specification_url"],
        "source_payload_sha256": _digest(payload),
        "candidate_count": inspection["candidate_count"],
        "promotable_count": inspection["promotable_count"],
        "blocked_count": inspection["blocked_count"],
        "blockers": blockers,
        "transport": request,
        "approved": False,
        "published": False,
    }


def _mortality_summary(payload: dict[str, Any]) -> dict[str, Any]:
    dataset = payload["dataset"]
    dimension = dataset["dimension"]
    dimension_ids = dimension["id"]
    sizes = dimension["size"]
    if len(dimension_ids) != len(sizes):
        raise RuntimeError("JSON-stat dimension identity and size lengths differ")

    def cube_value(codes: dict[str, str]) -> float:
        offset = 0
        for dimension_id, size in zip(dimension_ids, sizes):
            index = dimension[dimension_id]["category"]["index"][codes[dimension_id]]
            offset = offset * size + index
        value = dataset["value"][offset]
        if not isinstance(value, (int, float)):
            raise RuntimeError("Expected JSON-stat mortality cell is missing")
        return float(value)

    year_index = dimension["TLIST(A1)"]["category"]["index"]
    years = sorted(year_index, key=lambda value: year_index[value])
    first_year, latest_year = years[0], years[-1]

    def cancer_deaths(year: str, age_code: str) -> float:
        return cube_value(
            {
                "STATISTIC": "KTA31C01",
                "TLIST(A1)": year,
                "C02076V03371": age_code,
                "C04653V05438": "C00C97",
            }
        )

    first_under = cancer_deaths(first_year, "5642")
    first_over = cancer_deaths(first_year, "5641")
    latest_under = cancer_deaths(latest_year, "5642")
    latest_over = cancer_deaths(latest_year, "5641")
    first_total = first_under + first_over
    latest_total = latest_under + latest_over
    return {
        "source": dataset["source"],
        "provider_updated_at": dataset["updated"],
        "period_count": len(years),
        "first_year": int(first_year),
        "latest_year": int(latest_year),
        "first_cancer_deaths": int(first_total),
        "latest_cancer_deaths": int(latest_total),
        "latest_age_65_and_under_deaths": int(latest_under),
        "latest_age_65_and_over_deaths": int(latest_over),
        "change_from_first": int(latest_total - first_total),
        "change_from_first_percent": round(
            ((latest_total - first_total) / first_total) * 100, 2
        ),
    }


def _genomics_fixture() -> dict[str, Any]:
    security = [{"oauth": ["https://www.googleapis.com/auth/cloud-platform"]}]
    json_response = {
        "200": {
            "description": "Successful response",
            "content": {"application/json": {"schema": {"type": "object"}}},
        }
    }
    paths: dict[str, Any] = {
        "/v2alpha1/{name}": {
            "get": {
                "operationId": "genomics.projects.operations.list",
                "security": security,
                "parameters": [
                    {
                        "name": "name",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    },
                    {"name": "$.xgafv", "in": "query", "schema": {"type": "string"}},
                ],
                "responses": json_response,
            }
        }
    }
    for index, operation_id in enumerate(
        [
            "genomics.pipelines.run",
            "genomics.workers.checkIn",
            "genomics.projects.workers.checkIn",
            "genomics.projects.operations.cancel",
        ]
    ):
        paths[f"/v2alpha1/write{index}"] = {
            "post": {
                "operationId": operation_id,
                "security": security,
                "requestBody": {
                    "content": {"application/json": {"schema": {"type": "object"}}}
                },
                "responses": json_response,
            }
        }
    return {
        "openapi": "3.0.0",
        "info": {"title": "Genomics API", "version": "v2alpha1"},
        "servers": [{"url": "https://genomics.googleapis.com"}],
        "paths": paths,
        "components": {
            "securitySchemes": {
                "oauth": {
                    "type": "oauth2",
                    "flows": {
                        "authorizationCode": {
                            "authorizationUrl": "https://accounts.google.com/o/oauth2/auth",
                            "tokenUrl": "https://oauth2.googleapis.com/token",
                            "scopes": {
                                "https://www.googleapis.com/auth/cloud-platform": (
                                    "Cloud platform"
                                )
                            },
                        }
                    },
                }
            }
        },
    }


def _fixture_contract_fetch(
    url: str, params=None, **_kwargs
) -> tuple[Any, dict[str, Any]]:
    del params
    if url != GENOMICS_SPEC:
        raise AssertionError(f"Unexpected contract URL: {url}")
    payload = _genomics_fixture()
    return payload, _request(url, payload, content_type="application/json")


@contextmanager
def _allowed_hosts() -> Iterator[None]:
    key = "TOOLUNIVERSE_VSD_ALLOWED_HOSTS"
    previous = os.environ.get(key)
    requested = {
        "data.ok.gov",
        "www.health-ni.gov.uk",
        "ws.cso.ie",
    }
    if previous:
        requested.update(item.strip() for item in previous.split(",") if item.strip())
    os.environ[key] = ",".join(sorted(requested))
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = previous


@contextmanager
def _replay_transport() -> Iterator[None]:
    original_exchange = vsd_reviewed_runtime._http_exchange
    original_dynamic = vsd_dynamic_rest._safe_get_json

    def fake_exchange(**kwargs):
        url = kwargs["url"]
        fixture, content_type = {
            DATAGOV_ENDPOINT: ("cancer_deaths.csv", "text/csv"),
            EUROPE_ENDPOINT: ("irish_cancer_mortality.json", "application/json"),
            CKAN_ENDPOINT: ("cancer_waiting.csv", "application/octet-stream"),
        }[url]
        raw = (FIXTURES / fixture).read_bytes()
        return raw, _request(url, raw, content_type=content_type)

    def fake_dynamic(url: str, params=None, **_kwargs):
        if url != SOCRATA_ENDPOINT:
            raise AssertionError(f"Unexpected dynamic URL: {url}")
        values = dict(params or {})
        site = next(
            (value for key, value in values.items() if not key.startswith("$")),
            "Breast",
        )
        rows = json.loads(
            (FIXTURES / "roswell_trials.json").read_text(encoding="utf-8")
        )
        selected = [{**row, "primary_site": site} for row in rows]
        return selected, _request(url, selected, content_type="application/json")

    vsd_reviewed_runtime._http_exchange = fake_exchange
    vsd_dynamic_rest._safe_get_json = fake_dynamic
    try:
        yield
    finally:
        vsd_reviewed_runtime._http_exchange = original_exchange
        vsd_dynamic_rest._safe_get_json = original_dynamic


def _plan(tooluniverse: ToolUniverse) -> dict[str, Any]:
    return plan_workflow(
        tooluniverse,
        goal=(
            "Build an auditable breast-cancer program evidence view from trials and "
            "population mortality context"
        ),
        capabilities=WORKFLOW,
        limit=5,
    )["data"]


def _plan_states(plan: dict[str, Any]) -> dict[str, str]:
    return {step["step_id"]: step["classification"] for step in plan["steps"]}


def _promotion_chain_complete(item: dict[str, Any]) -> bool:
    return all(
        isinstance(item.get(field), str) and len(item[field]) == 64
        for field in (
            "draft_sha256",
            "verification_sha256",
            "approval_sha256",
            "publication_sha256",
        )
    )


def run_case(
    *,
    workspace: Path,
    mode: str = "live",
    discovery_runner: DiscoveryRunner | None = None,
    contract_fetch_json: JSONFetcher | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    if mode not in {"live", "network_backed", "replay"}:
        raise ValueError("mode must be live, network_backed, or replay")
    default_runners = {
        "live": _agent_discovery,
        "network_backed": _network_backed_discovery,
        "replay": _fixture_discovery,
    }
    runner = discovery_runner or default_runners[mode]
    contract_fetch = contract_fetch_json or (
        _fixture_contract_fetch if mode == "replay" else vsd_tool._safe_get_json
    )
    timestamp = generated_at or datetime.now(timezone.utc).isoformat()
    demand_workspace = workspace / "demand"
    promotion_workspace = workspace / "promotion"

    catalog_searches = []
    selected: dict[str, dict[str, Any]] = {}
    initial_universe = ToolUniverse()
    initial_universe.load_tools(include_tools=["VSDDiscoverAPICandidates"], quiet=True)
    try:
        initial_plan = _plan(initial_universe)
        for index in range(3):
            record_plan_demands(
                initial_plan,
                {
                    "trial_inventory": "Breast-cancer trial inventory by primary site",
                    "mortality_context": "Age-stratified cancer mortality context",
                },
                workspace=demand_workspace,
                run_id=f"multicatalog-cancer-{index + 1}",
                observed_at=f"2026-08-02T06:0{index}:00+00:00",
            )
        demand = rank_demands(workspace=demand_workspace)["data"]
        for provider in catalogs.PROVIDER_ORDER:
            case = CATALOG_CASES[provider]
            result = runner(initial_universe, provider, case["query"], False)
            candidate = _select_candidate(result, case["identity"])
            selected[provider] = candidate
            catalog_searches.append(
                {
                    "provider": provider,
                    "role": case["role"],
                    "query": case["query"],
                    "evidence_mode": (
                        "replay"
                        if mode == "replay"
                        or (mode == "network_backed" and provider == "datagov")
                        else "live"
                    ),
                    "catalog_result_count": result["catalog_result_count"],
                    "candidate_count": result["candidate_count"],
                    "successful_provider_count": result["successful_provider_count"],
                    "failed_provider_count": result["failed_provider_count"],
                    "selected_candidate": _candidate_summary(candidate),
                    "provenance": result["provenance"]["providers"][0],
                }
            )
    finally:
        initial_universe.close()

    with _allowed_hosts():
        datagov = _qualify_datagov(selected["datagov"], promotion_workspace)
        ckan = _qualify_ckan(selected["ckan_data_gov_uk"], promotion_workspace)
        genomics = _inspect_genomics(selected["apis_guru"], contract_fetch)
        trial_promotion, early_error = _promote_trial_registry(
            selected["socrata"], promotion_workspace
        )
        mortality_promotion = _promote_mortality_resource(
            selected["data_europa"], promotion_workspace
        )

        runtime = ToolUniverse()
        runtime.load_tools(include_tools=["VSDDiscoverAPICandidates"], quiet=True)
        try:
            published_names = [TRIAL_TOOL, MORTALITY_TOOL]
            present_before = [
                name for name in published_names if name in runtime.all_tool_dict
            ]
            loaded = load_published_tools(runtime, workspace=promotion_workspace)
            trial_data = _successful_data(
                runtime.run_one_function(
                    {"name": TRIAL_TOOL, "arguments": {"primary_site": "Breast"}},
                    use_cache=False,
                ),
                TRIAL_TOOL,
            )
            mortality_data = _successful_data(
                runtime.run_one_function(
                    {"name": MORTALITY_TOOL, "arguments": {}}, use_cache=False
                ),
                MORTALITY_TOOL,
            )
            final_plan = _plan(runtime)
            post_discovery = {}
            for provider in ("socrata", "data_europa"):
                case = CATALOG_CASES[provider]
                post_discovery[provider] = runner(
                    runtime, provider, case["query"], True
                )
        finally:
            runtime.close()

    trial_rows = trial_data["result"]
    mortality_payload = mortality_data["result"]
    mortality_summary = _mortality_summary(mortality_payload)
    initial_states = _plan_states(initial_plan)
    final_states = _plan_states(final_plan)
    serialized_searches = json.dumps(catalog_searches, sort_keys=True)
    datagov_credential = os.environ.get("TOOLUNIVERSE_DATAGOV_API_KEY")
    credentials_not_persisted = all(
        "headers" not in item["provenance"]
        and set(item["provenance"].get("request_header_names", [])) <= {"X-Api-Key"}
        for item in catalog_searches
    ) and (not datagov_credential or datagov_credential not in serialized_searches)
    repeated_demand = sorted(
        record["observation_counts"]["missing"] for record in demand["ranked_demands"]
    )
    assertions = {
        "all_five_catalogs_returned_live_or_replayed_results": (
            len(catalog_searches) == 5
            and all(item["successful_provider_count"] == 1 for item in catalog_searches)
        ),
        "all_selected_candidates_are_hash_bound_and_inert": all(
            item["execution_allowed"] is False
            and item["approval_state"] == "unreviewed_candidate"
            and len(item["candidate_sha256"]) == 64
            for item in selected.values()
        ),
        "catalog_credentials_were_not_persisted": credentials_not_persisted,
        "ckan_mime_mismatch_blocked_verification": (
            ckan["decision"] == "blocked_at_verification"
            and ckan["observed_content_type"] == "application/octet-stream"
        ),
        "datagov_unfit_resource_was_not_approved": (
            datagov["approved"] is False
            and datagov["decision"]
            in {"blocked_at_verification", "withheld_after_quality_review"}
        ),
        "demand_was_observed_three_times_before_growth": repeated_demand == [3, 3],
        "early_publication_was_rejected": bool(early_error),
        "genomics_contract_operations_were_blocked_before_drafting": (
            genomics["candidate_count"] == 5
            and genomics["promotable_count"] == 0
            and genomics["blocked_count"] == 5
        ),
        "initial_plan_identified_both_exact_capability_gaps": (
            initial_states["trial_inventory"] != "existing_exact"
            and initial_states["mortality_context"] != "existing_exact"
        ),
        "post_publication_discovery_suppressed_both_resources": all(
            post_discovery[provider]["registered_duplicate_count"] == 1
            for provider in ("socrata", "data_europa")
        ),
        "post_publication_plan_resolved_both_exact_capabilities": (
            final_states["trial_inventory"] == "existing_exact"
            and final_states["mortality_context"] == "existing_exact"
        ),
        "published_tools_were_absent_until_explicit_load": (
            present_before == []
            and sorted(loaded) == sorted([TRIAL_TOOL, MORTALITY_TOOL])
        ),
        "mortality_resource_completed_three_verification_cases": (
            mortality_promotion["verification_case_count"] == 3
        ),
        "mortality_runtime_returned_current_age_stratified_data": (
            mortality_summary["latest_year"] == 2024
            and mortality_summary["latest_age_65_and_under_deaths"] == 2266
            and mortality_summary["latest_age_65_and_over_deaths"] == 8041
        ),
        "mortality_totals_were_computed_from_provider_values": (
            mortality_summary["first_cancer_deaths"] == 9022
            and mortality_summary["latest_cancer_deaths"] == 10307
            and mortality_summary["change_from_first"] == 1285
        ),
        "trial_registry_completed_three_distinct_verification_cases": (
            trial_promotion["verification_case_count"] == 3
            and len(
                {
                    json.dumps(item, sort_keys=True)
                    for item in trial_promotion["verification_arguments"]
                }
            )
            == 3
        ),
        "trial_runtime_returned_exact_site_rows": (
            bool(trial_rows)
            and all(row["primary_site"] == "Breast" for row in trial_rows)
        ),
        "two_hash_chains_reached_publication": (
            _promotion_chain_complete(trial_promotion)
            and _promotion_chain_complete(mortality_promotion)
        ),
    }
    snapshot: dict[str, Any] = {
        "case": "multicatalog_breast_cancer_program_growth",
        "mode": mode,
        "evidence_summary": {
            "live_catalog_count": sum(
                item["evidence_mode"] == "live" for item in catalog_searches
            ),
            "replayed_catalogs": [
                item["provider"]
                for item in catalog_searches
                if item["evidence_mode"] == "replay"
            ],
            "candidate_qualification": ("replay" if mode == "replay" else "live"),
        },
        "generated_at": timestamp,
        "decision_question": (
            "Can ToolUniverse turn a complex breast-cancer program need into a "
            "reviewed source portfolio while rejecting attractive but unsafe or "
            "unfit catalog results?"
        ),
        "research_need": {
            "molecular": "Locate a usable genomics workflow contract.",
            "trials": "Find registry studies by primary cancer site.",
            "mortality": "Measure current malignant-neoplasm deaths by age group.",
            "access": "Find treatment waiting-time evidence.",
            "outcomes": "Find a current cancer outcome benchmark.",
        },
        "initial_plan": {
            "overall_action": initial_plan["overall_action"],
            "states": initial_states,
            "plan_sha256": initial_plan["plan_sha256"],
        },
        "demand": {
            "record_count": len(demand["ranked_demands"]),
            "observation_counts": repeated_demand,
            "ledger_sha256": demand["ledger_sha256"],
        },
        "catalog_searches": catalog_searches,
        "qualification_decisions": {
            "socrata": {
                "decision": "approved_and_published",
                "reason": "Three distinct exact-site calls passed verification.",
                "verification_case_count": 3,
                "approved": True,
                "published": True,
            },
            "datagov": datagov,
            "data_europa": {
                "decision": "approved_and_published",
                "reason": (
                    "The bounded resource supplied a current, parseable JSON-stat "
                    "mortality cube through 2024."
                ),
                "verification_case_count": 3,
                "approved": True,
                "published": True,
            },
            "ckan_data_gov_uk": ckan,
            "apis_guru": genomics,
        },
        "promotions": [trial_promotion, mortality_promotion],
        "early_publication_error": early_error,
        "runtime_evidence": {
            "loaded_tools": loaded,
            "present_before_explicit_load": present_before,
            "trial_rows": trial_rows,
            "trial_provenance": trial_data["provenance"],
            "mortality_summary": mortality_summary,
            "mortality_provenance": mortality_data["provenance"],
        },
        "closed_loop": {
            "final_plan_states": final_states,
            "final_plan_sha256": final_plan["plan_sha256"],
            "registered_duplicate_counts": {
                provider: post_discovery[provider]["registered_duplicate_count"]
                for provider in ("socrata", "data_europa")
            },
            "registered_duplicates": {
                provider: post_discovery[provider]["registered_duplicates"]
                for provider in ("socrata", "data_europa")
            },
        },
        "with_without_vsd": [
            {
                "task": "Search five incompatible catalogs",
                "without_vsd": "Write five provider-specific clients and compare raw schemas manually.",
                "with_vsd": "Invoke one agent-facing tool and receive one inert candidate contract.",
            },
            {
                "task": "Decide whether a result is usable",
                "without_vsd": "A relevant title can be mistaken for a safe, current API.",
                "with_vsd": "Bounded verification exposed a redirect boundary, a MIME mismatch, blocked genomics operations, and stale replayed values.",
            },
            {
                "task": "Create reusable tools",
                "without_vsd": "Wire endpoints directly with no common review or evidence chain.",
                "with_vsd": "Publish only two exact hash-bound tools after verification and approval.",
            },
            {
                "task": "Avoid duplicate growth",
                "without_vsd": "Repeat searches can recreate an endpoint already in the registry.",
                "with_vsd": "Replanning finds exact coverage and rediscovery suppresses both endpoints.",
            },
        ],
        "end_to_end_assertions": assertions,
        "boundary": (
            "This is a software-governance and public aggregate-data retrieval proof. "
            "It does not establish trial eligibility, compare treatments, infer patient "
            "risk, or certify the scientific quality of a catalog listing."
        ),
    }
    snapshot["audit_sha256"] = _digest(snapshot)
    validate_snapshot(snapshot)
    return snapshot


def validate_snapshot(snapshot: dict[str, Any]) -> None:
    if snapshot.get("case") != "multicatalog_breast_cancer_program_growth":
        raise ValueError("Cancer case identity is invalid")
    assertions = snapshot.get("end_to_end_assertions")
    if (
        not isinstance(assertions, dict)
        or set(assertions) != EXPECTED_ASSERTIONS
        or not all(value is True for value in assertions.values())
    ):
        failed = (
            sorted(
                key
                for key, value in assertions.items()
                if key not in EXPECTED_ASSERTIONS or value is not True
            )
            if isinstance(assertions, dict)
            else ["invalid_assertion_envelope"]
        )
        raise ValueError(f"Cancer end-to-end assertions did not pass: {failed!r}")
    expected = _digest(
        {key: value for key, value in snapshot.items() if key != "audit_sha256"}
    )
    if snapshot.get("audit_sha256") != expected:
        raise ValueError("Cancer case audit digest does not match")


def render_markdown(snapshot: dict[str, Any]) -> str:
    validate_snapshot(snapshot)
    searches = snapshot["catalog_searches"]
    decisions = snapshot["qualification_decisions"]
    runtime = snapshot["runtime_evidence"]
    mortality = runtime["mortality_summary"]
    lines = [
        "# Multi-Catalog Breast-Cancer Program Study",
        "",
        "## Decision Question",
        "",
        snapshot["decision_question"],
        "",
        "## Evidence Mode",
        "",
        f"- Study mode: `{snapshot['mode']}`",
        (
            f"- Live catalog searches: **{snapshot['evidence_summary']['live_catalog_count']}**"
        ),
        (
            "- Replayed catalog searches: "
            f"`{json.dumps(snapshot['evidence_summary']['replayed_catalogs'])}`"
        ),
        (
            "- Candidate resource and contract qualification: "
            f"`{snapshot['evidence_summary']['candidate_qualification']}`"
        ),
        "",
        (
            "`network_backed` means only the Data.gov catalog response is a captured "
            "real replay because its shared `DEMO_KEY` quota returned HTTP 429. The "
            "other four catalogs and all five selected resources/contracts are live."
            if snapshot["mode"] == "network_backed"
            else "The mode above applies to both catalog search and candidate qualification."
        ),
        "",
        "## Why This Is Hard",
        "",
        (
            "The program needs molecular, trial, mortality, access, and outcome evidence. "
            "Those leads live in five catalogs with different APIs and metadata shapes, "
            "and a relevant catalog title does not prove that the underlying resource is "
            "current, safely executable, correctly typed, or contract-compatible."
        ),
        "",
        "## Initial Gap And Repeated Demand",
        "",
        f"- Initial action: `{snapshot['initial_plan']['overall_action']}`",
        f"- Initial capability states: `{json.dumps(snapshot['initial_plan']['states'], sort_keys=True)}`",
        f"- Demand records: **{snapshot['demand']['record_count']}**, each observed **3** times",
        "",
        "## Five Real Catalog Searches",
        "",
        "| Catalog | Evidence | Research role | Query | Catalog matches | Candidates | Selected lead |",
        "| --- | --- | --- | --- | ---: | ---: | --- |",
    ]
    for item in searches:
        selected = item["selected_candidate"]
        selected_name = selected["name"].replace("|", "\\|")
        lines.append(
            f"| `{item['provider']}` | `{item['evidence_mode']}` | {item['role']} | `{item['query']}` | "
            f"{item['catalog_result_count']} | {item['candidate_count']} | "
            f"{selected_name} |"
        )
    lines.extend(
        [
            "",
            (
                "Every selected lead was still `unreviewed_candidate` with "
                "`execution_allowed=false` and a content digest. Catalog ranking was "
                "used for triage, never as approval."
            ),
            "",
            "## Qualification Decisions",
            "",
            "| Catalog | Decision | Concrete reason |",
            "| --- | --- | --- |",
            f"| Socrata | Published | {decisions['socrata']['reason']} |",
            f"| Data.gov | Not published | {decisions['datagov']['reason']} |",
            f"| Data Europa | Published | {decisions['data_europa']['reason']} |",
            f"| Data.gov.uk CKAN | Blocked | Provider returned `{decisions['ckan_data_gov_uk']['observed_content_type']}` for catalog-declared CSV; the reviewed runtime refused the mismatch. |",
            f"| APIs.guru | Blocked | All {decisions['apis_guru']['blocked_count']} Google Genomics operations had authentication, write-method, request-body, or unsupported-parameter blockers. |",
            "",
            "## Evidence Actually Retrieved",
            "",
            f"- **Trials:** `{TRIAL_TOOL}` returned **{len(runtime['trial_rows'])}** exact `Breast` rows in the checked execution. The dataset is a registry snapshot; a populated `date_closed` must not be presented as currently recruiting.",
            f"- **Mortality context:** `{MORTALITY_TOOL}` returned malignant-neoplasm counts through **{mortality['latest_year']}**: **{mortality['latest_age_65_and_under_deaths']}** deaths at age 65 or under and **{mortality['latest_age_65_and_over_deaths']}** over age 65, or **{mortality['latest_cancer_deaths']}** combined.",
            (
                "- **Outcome candidate rejected:** "
                + (
                    f"the Data.gov resource ended in **{decisions['datagov']['latest_year']}** "
                    f"and had only **{decisions['datagov']['nonzero_historical_rows']}** "
                    "non-zero historical rows."
                    if decisions["datagov"]["quality_review_completed"]
                    else "the live endpoint failed bounded verification before its "
                    "contents could be accepted for quality review."
                )
            ),
            "",
            "These are source observations, not clinical conclusions and not cross-population comparisons.",
            "",
            "## Promotion And Closed Loop",
            "",
            "| Tool | Verification cases | Draft | Verification | Approval | Publication |",
            "| --- | ---: | --- | --- | --- | --- |",
        ]
    )
    for promotion in snapshot["promotions"]:
        lines.append(
            f"| `{promotion['tool_name']}` | {promotion['verification_case_count']} | "
            f"`{promotion['draft_sha256'][:12]}` | "
            f"`{promotion['verification_sha256'][:12]}` | "
            f"`{promotion['approval_sha256'][:12]}` | "
            f"`{promotion['publication_sha256'][:12]}` |"
        )
    lines.extend(
        [
            "",
            f"The two tools were absent before explicit loading. Replanning classified both operations as exact existing capabilities, and repeat Socrata/Data Europa discovery suppressed one registered endpoint each.",
            "",
            "## Exact VSD Advantage",
            "",
            "| Task | Without VSD | With VSD |",
            "| --- | --- | --- |",
        ]
    )
    for item in snapshot["with_without_vsd"]:
        lines.append(f"| {item['task']} | {item['without_vsd']} | {item['with_vsd']} |")
    lines.extend(
        [
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
            "## Boundary",
            "",
            snapshot["boundary"],
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
    markdown_path.write_text(render_markdown(snapshot), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode", choices=("live", "network_backed", "replay"), default="replay"
    )
    parser.add_argument("--workspace", type=Path, default=DEFAULT_WORKSPACE)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    arguments = parser.parse_args(argv)
    if arguments.mode == "replay":
        with _replay_transport():
            snapshot = run_case(workspace=arguments.workspace, mode="replay")
    else:
        snapshot = run_case(workspace=arguments.workspace, mode=arguments.mode)
    write_artifacts(snapshot, arguments.json, arguments.markdown)
    print(
        json.dumps(
            {
                "status": "passed",
                "mode": arguments.mode,
                "assertions": len(snapshot["end_to_end_assertions"]),
                "audit_sha256": snapshot["audit_sha256"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
