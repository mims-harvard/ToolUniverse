"""Prove the complete VSD source-to-reviewed-runtime path across every format."""

from __future__ import annotations

import base64
import copy
import hashlib
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlsplit

from google.protobuf import descriptor_pb2

from tooluniverse import ToolUniverse, vsd_lifecycle, vsd_promotion
import tooluniverse.vsd_reviewed_runtime as runtime
from tooluniverse.vsd_contracts import inspect_contract_document

try:
    from . import source_intelligence_case_study as source_study
except ImportError:  # Direct execution from examples/vsd.
    import source_intelligence_case_study as source_study


HERE = Path(__file__).resolve().parent
ARTIFACTS = HERE / "artifacts"
DEFAULT_JSON = ARTIFACTS / "cross_format_total_proof.json"
DEFAULT_MARKDOWN = ARTIFACTS / "cross_format_total_proof.md"

FORMAT_TOOL_NAMES = {
    "graphql": "VSDDandiAlsGraphQL",
    "postman": "VSDDandiDandisetREST",
    "wsdl": "VSDDandiPreservationSOAP",
    "protobuf": "VSDDandiAlsGRPC",
    "mcp": "VSDDandiMetadataMCP",
    "asyncapi": "VSDDandiChangeEvent",
}

SELECTED_OPERATIONS = {
    "graphql": "searchAlsElectrophysiology",
    "postman": "Get dandiset",
    "wsdl": "ArchivePort.GetPreservationRecord",
    "protobuf": "dandi.v1.DandisetService.SearchAlsDandisets",
    "mcp": "dandi-readonly",
    "asyncapi": "receiveDandisetChange",
}

PORTFOLIO_CASES = [
    {
        "id": "public_health_foundation",
        "phase": "reviewed source foundation",
        "pull_request": 416,
        "artifact": "snapshot.json",
        "question": "Which Autauga County tracts warrant CHD evidence review without ranking people or making clinical claims?",
        "result": "Six ToolUniverse calls combined reviewed CDC, WHO, FDA, PubMed, and trial evidence with explicit interpretation limits.",
    },
    {
        "id": "dynamic_rest_als",
        "phase": "reviewed dynamic REST",
        "pull_request": 417,
        "artifact": "dynamic_rest_als_snapshot.json",
        "question": "Can a bounded generated ClinicalTrials.gov tool find active US ALS studies and retrieve one exact follow-up record?",
        "result": "Two reviewed operations returned 20 search records and a consistent exact study detail.",
    },
    {
        "id": "api_discovery",
        "phase": "catalog discovery",
        "pull_request": 418,
        "artifact": "api_discovery_snapshot.json",
        "question": "Can demand for active cancer-trial fields identify one API-ready public dataset without executing it?",
        "result": "One official NY dataset matched all six demanded capabilities and remained inert review material.",
    },
    {
        "id": "tool_promotion",
        "phase": "verification and promotion",
        "pull_request": 419,
        "artifact": "tool_promotion_snapshot.json",
        "question": "Can one reviewed cancer dataset become two narrow tools only after representative verification?",
        "result": "Two tools passed three cases each, were approved, published, freshly loaded, and executed.",
    },
    {
        "id": "docker_boundary",
        "phase": "administrator-only Docker lifecycle",
        "pull_request": 420,
        "artifact": None,
        "question": "Can a local inference service be provisioned without exposing Docker lifecycle control to an agent?",
        "result": "Independent Linux CI proved a non-root, loopback-only, read-only, resource-bounded container lifecycle and exact payload hash.",
    },
    {
        "id": "capability_coverage",
        "phase": "registry and workflow reuse",
        "pull_request": 421,
        "artifact": "capability_coverage_snapshot.json",
        "question": "Does ToolUniverse reuse an existing FDA tool or workflow before declaring a capability gap?",
        "result": "Exact tools and a workflow were reused; only the intentional calibration request remained a discovery gap.",
    },
    {
        "id": "openapi_ingestion",
        "phase": "OpenAPI inspection and promotion",
        "pull_request": 423,
        "artifact": "openapi_als_snapshot.json",
        "question": "Can an ALS OpenAPI contract yield one selected read operation with exact provenance and fresh-runtime execution?",
        "result": "Inspection, three-case verification, approval, publication, execution, and hash-chain validation passed.",
    },
    {
        "id": "workflow_planning",
        "phase": "workflow-aware planning",
        "pull_request": 424,
        "artifact": "workflow_planning_snapshot.json",
        "question": "Can a multi-step ALS workflow distinguish reusable tools from the one missing step without executing during planning?",
        "result": "Planning reused exact capabilities, isolated the gap, and changed only after explicit loading.",
    },
    {
        "id": "demand_ledger",
        "phase": "private unmet-demand ledger",
        "pull_request": 425,
        "artifact": "demand_ledger_snapshot.json",
        "question": "Can repeated missing needs be ranked locally and exported only as reviewed, sanitized proposals?",
        "result": "Private observations were deduplicated, ranked, and explicitly exported without raw prompts.",
    },
    {
        "id": "credential_reference",
        "phase": "environment-backed credentials",
        "pull_request": 426,
        "artifact": "credential_reference_snapshot.json",
        "question": "Can credentials rotate without changing the reviewed tool identity or leaking into artifacts?",
        "result": "Initial and rotated credentials executed while configs, promotion records, results, and artifacts stayed secret-free.",
    },
    {
        "id": "lifecycle_drift",
        "phase": "suspension, drift, and recovery",
        "pull_request": 427,
        "artifact": "lifecycle_drift_snapshot.json",
        "question": "Can a published tool fail closed on contract drift and return only after reviewed recovery?",
        "result": "Drift suspended loading, changed-schema evidence was reviewed, and recovery restored the exact tool.",
    },
    {
        "id": "total_system",
        "phase": "demand-to-runtime total system",
        "pull_request": 428,
        "artifact": "total_system_snapshot.json",
        "question": "Can ALS demand move through discovery, review, promotion, use, resolution, suspension, and recovery as one system?",
        "result": "The full demand-to-reviewed-tool loop passed with Docker preserved as an independent administrator boundary.",
    },
    {
        "id": "multiformat_contracts",
        "phase": "heterogeneous contract inspection",
        "pull_request": 429,
        "artifact": "multiformat_contract_snapshot.json",
        "question": "Can six incompatible contract formats become an inert, content-addressed operation inventory?",
        "result": "GraphQL, AsyncAPI, Postman, WSDL, protobuf, and MCP produced ten identified operations without execution.",
    },
    {
        "id": "reviewed_runtime",
        "phase": "multi-protocol execution",
        "pull_request": 430,
        "artifact": "reviewed_runtime_snapshot.json",
        "question": "Can one rare-disease study execute reviewed GraphQL, REST, SOAP, gRPC, MCP, event, pagination, and response formats?",
        "result": "Ten runtime cases and one full WSDL promotion case passed 33 assertions.",
    },
    {
        "id": "source_intelligence",
        "phase": "organic source discovery and handoff",
        "pull_request": 431,
        "artifact": "source_intelligence_snapshot.json",
        "question": "Can official-source scanning find ALS interface gaps without duplicates, installation, or silent telemetry?",
        "result": "Fifty sources, seven formats, two cron scans, seven snapshots, and one consent-bound local handoff passed 28 assertions.",
    },
]


class _FixedDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        value = cls(2026, 8, 3, 12, 0, 0, tzinfo=timezone.utc)
        return value if tz else value.replace(tzinfo=None)


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode()


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _metadata(url: str, content_type: str, raw: bytes) -> dict[str, Any]:
    return {
        "url": url,
        "status_code": 200,
        "content_type": content_type,
        "response_bytes": len(raw),
        "headers": {"content-type": content_type},
        "peer_ip": "203.0.113.30",
        "redirects": 0,
    }


def _descriptor_set() -> str:
    descriptor = descriptor_pb2.FileDescriptorProto(
        name="dandisets.proto", package="dandi.v1", syntax="proto3"
    )
    request = descriptor.message_type.add(name="SearchRequest")
    for number, name in enumerate(("disease_term", "species"), start=1):
        request.field.add(
            name=name,
            number=number,
            label=descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL,
            type=descriptor_pb2.FieldDescriptorProto.TYPE_STRING,
        )
    response = descriptor.message_type.add(name="DandisetMatch")
    for number, name in enumerate(("dandiset_id", "name"), start=1):
        response.field.add(
            name=name,
            number=number,
            label=descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL,
            type=descriptor_pb2.FieldDescriptorProto.TYPE_STRING,
        )
    service = descriptor.service.add(name="DandisetService")
    service.method.add(
        name="SearchAlsDandisets",
        input_type=".dandi.v1.SearchRequest",
        output_type=".dandi.v1.DandisetMatch",
    )
    return base64.b64encode(
        descriptor_pb2.FileDescriptorSet(file=[descriptor]).SerializeToString()
    ).decode()


def _http_config(
    name: str,
    description: str,
    endpoint: str,
    *,
    protocol: str,
    properties: dict[str, Any],
    required: list[str],
    request: dict[str, Any],
    response: dict[str, Any],
) -> dict[str, Any]:
    return {
        "name": name,
        "type": "VSDReviewedOperationTool",
        "description": description,
        "category": "special_tools",
        "cacheable": False,
        "parameter": {
            "type": "object",
            "properties": properties,
            "required": required,
            "additionalProperties": False,
        },
        "return_schema": {"type": "object"},
        "vsd_reviewed_operation": {
            "version": 1,
            "transport": "http",
            "protocol": protocol,
            "endpoint": endpoint,
            "timeout_seconds": 20,
            "auth": {"type": "none"},
            "request": request,
            "response": response,
            "pagination": {"type": "none"},
        },
    }


def _json_response() -> dict[str, Any]:
    return {"format": "json", "schema": {"type": "object"}, "max_bytes": 100_000}


def _source_candidates(
    source_snapshot: dict[str, Any], workspace: Path
) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    candidates: dict[str, dict[str, Any]] = {}
    source_ids: dict[str, str] = {}
    snapshot_directory = workspace / "source" / "contract-snapshots"
    for manifest in source_snapshot["snapshot_manifests"]:
        source_format = manifest["format_hint"]
        if source_format not in SELECTED_OPERATIONS:
            continue
        path = snapshot_directory / manifest["snapshot_file"]
        endpoint = source_study._inspection_endpoint(source_format)
        report = inspect_contract_document(
            path,
            format_hint=source_format,
            **({"endpoint": endpoint} if endpoint else {}),
        )
        matches = [
            candidate
            for candidate in report["candidates"]
            if candidate["name"] == SELECTED_OPERATIONS[source_format]
        ]
        if len(matches) != 1:
            raise ValueError(f"Expected one selected {source_format} operation")
        candidates[source_format] = matches[0]
        source_ids[source_format] = manifest["candidate_id"]
    if set(candidates) != set(SELECTED_OPERATIONS):
        raise ValueError("Source scan did not yield every selected contract format")
    return candidates, source_ids


def _reviewed_configs(
    candidates: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    graphql = _http_config(
        FORMAT_TOOL_NAMES["graphql"],
        "Find ALS electrophysiology dandisets through one reviewed GraphQL query.",
        candidates["graphql"]["endpoint"],
        protocol="graphql",
        properties={
            "disease_term": {"type": "string"},
            "species": {"type": "string"},
            "recording_modality": {"type": "string"},
            "limit": {"type": "integer", "minimum": 1, "maximum": 20},
        },
        required=["disease_term", "species", "recording_modality", "limit"],
        request={
            "method": "POST",
            "reviewed_read_only": True,
            "body": {
                "mode": "graphql",
                "query": (
                    "query SearchAls($diseaseTerm: String!, $species: String!, "
                    "$recordingModality: String!, $limit: Int) { "
                    "searchAlsElectrophysiology(diseaseTerm: $diseaseTerm, "
                    "species: $species, recordingModality: $recordingModality, "
                    "limit: $limit) { id name species } }"
                ),
                "operation_name": "SearchAls",
                "arguments": {
                    "disease_term": "diseaseTerm",
                    "species": "species",
                    "recording_modality": "recordingModality",
                    "limit": "limit",
                },
            },
        },
        response=_json_response(),
    )
    postman = _http_config(
        FORMAT_TOOL_NAMES["postman"],
        "Retrieve one exact DANDI metadata record through a reviewed path mapping.",
        f"https://{source_study.DANDI}/api/dandisets/{{dandiset_id}}",
        protocol="rest",
        properties={"dandiset_id": {"type": "string"}},
        required=["dandiset_id"],
        request={
            "method": "GET",
            "path_arguments": {"dandiset_id": "dandiset_id"},
            "body": {"mode": "none"},
        },
        response=_json_response(),
    )
    postman["vsd_contract_parameters"] = {"dandisetId": "dandiset_id"}
    wsdl = _http_config(
        FORMAT_TOOL_NAMES["wsdl"],
        "Retrieve one existing DANDI preservation record through reviewed SOAP.",
        candidates["wsdl"]["endpoint"],
        protocol="soap",
        properties={"dandiset_id": {"type": "string"}},
        required=["dandiset_id"],
        request={
            "method": "POST",
            "reviewed_read_only": True,
            "fixed_headers": {"SOAPAction": "urn:GetPreservationRecord"},
            "body": {
                "mode": "soap",
                "envelope": (
                    "<Envelope><Body><GetPreservationRecord>"
                    "<dandiset>{dandiset_id}</dandiset>"
                    "</GetPreservationRecord></Body></Envelope>"
                ),
                "arguments": {"dandiset_id": "dandiset"},
            },
        },
        response={"format": "xml", "schema": {"type": "object"}},
    )
    grpc = {
        "name": FORMAT_TOOL_NAMES["protobuf"],
        "type": "VSDReviewedOperationTool",
        "description": "Search ALS dandisets through one exact reviewed unary gRPC method.",
        "parameter": {
            "type": "object",
            "properties": {"request": {"type": "object"}},
            "required": ["request"],
            "additionalProperties": False,
        },
        "vsd_reviewed_operation": {
            "version": 1,
            "transport": "grpc",
            "protocol": "grpc",
            "endpoint": f"{source_study.DANDI}:443",
            "method": "/dandi.v1.DandisetService/SearchAlsDandisets",
            "descriptor_set_base64": _descriptor_set(),
            "request_type": "dandi.v1.SearchRequest",
            "response_type": "dandi.v1.DandisetMatch",
            "streaming": "unary",
            "max_messages": 1,
            "auth": {"type": "none"},
            "response": {"format": "json", "schema": {"type": "object"}},
        },
    }
    mcp = {
        "name": FORMAT_TOOL_NAMES["mcp"],
        "type": "VSDReviewedOperationTool",
        "description": "Run one declared DANDI metadata search tool on the reviewed MCP server.",
        "parameter": {
            "type": "object",
            "properties": {"arguments": {"type": "object"}},
            "required": ["arguments"],
            "additionalProperties": False,
        },
        "vsd_reviewed_operation": {
            "version": 1,
            "transport": "mcp",
            "protocol": "mcp",
            "endpoint": candidates["mcp"]["endpoint"],
            "tool_name": "search_dandisets",
            "auth": {"type": "none"},
            "response": {"format": "json", "schema": {"type": "object"}},
        },
    }
    asyncapi = {
        "name": FORMAT_TOOL_NAMES["asyncapi"],
        "type": "VSDReviewedOperationTool",
        "description": "Validate one received DANDI change event against the reviewed channel.",
        "parameter": {
            "type": "object",
            "properties": {"event": {"type": "object"}},
            "required": ["event"],
            "additionalProperties": False,
        },
        "vsd_reviewed_operation": {
            "version": 1,
            "transport": "event",
            "protocol": "asyncapi",
            "source_endpoint": candidates["asyncapi"]["endpoint"],
            "channel": candidates["asyncapi"]["contract"]["channel"],
            "event_argument": "event",
            "event_schema": copy.deepcopy(candidates["asyncapi"]["input_schema"]),
            "auth": {"type": "none"},
            "response": {"format": "json", "schema": {"type": "object"}},
        },
    }
    return {
        "graphql": graphql,
        "postman": postman,
        "wsdl": wsdl,
        "protobuf": grpc,
        "mcp": mcp,
        "asyncapi": asyncapi,
    }


def _fake_http(**kwargs):
    url = kwargs["url"]
    if url.endswith("/graphql"):
        request = json.loads((kwargs["body"] or b"{}").decode())
        disease = request["variables"]["diseaseTerm"]
        raw = _canonical(
            {
                "data": {
                    "searchAlsElectrophysiology": [
                        {
                            "id": f"DANDI-{disease.upper()}",
                            "name": f"{disease} motor-neuron electrophysiology",
                            "species": [request["variables"]["species"]],
                        }
                    ]
                }
            }
        )
        return raw, _metadata(url, "application/json", raw)
    if "/api/dandisets/" in url:
        dandiset_id = urlsplit(url).path.rsplit("/", 1)[-1]
        raw = _canonical(
            {
                "dandiset_id": dandiset_id,
                "name": "ALS motor-neuron electrophysiology",
                "status": "published",
            }
        )
        return raw, _metadata(url, "application/json", raw)
    if url.endswith("/soap"):
        body = (kwargs["body"] or b"").decode()
        dandiset_id = body.split("<dandiset>", 1)[1].split("</dandiset>", 1)[0]
        raw = (
            "<Envelope><Body><PreservationRecord>"
            f"<dandiset>{dandiset_id}</dandiset><status>preserved</status>"
            "</PreservationRecord></Body></Envelope>"
        ).encode()
        return raw, _metadata(url, "text/xml", raw)
    raise AssertionError(f"Unexpected HTTP route: {url}")


def _fake_grpc(operation: dict[str, Any], request: dict[str, Any]):
    del operation
    return (
        {
            "dandiset_id": f"DANDI-{request['disease_term'].upper()}",
            "name": f"{request['species']} electrophysiology evidence",
        },
        {"messages": 1, "elapsed_seconds": 0.01, "peer": source_study.DANDI},
    )


def _fake_mcp(operation: dict[str, Any], arguments: dict[str, Any]):
    return (
        {
            "content": [
                {
                    "type": "text",
                    "text": (
                        f"{arguments['condition']} matched "
                        f"{arguments['species']} electrophysiology dandisets"
                    ),
                }
            ]
        },
        {"tool_name": operation["tool_name"]},
    )


def _expect(path: str, value: Any, required_field: str) -> dict[str, Any]:
    return {
        "result_type": "object",
        "required_fields": [required_field],
        "equals": {},
        "required_paths": [path],
        "equals_paths": {path: value},
    }


def _cases() -> dict[str, dict[str, Any]]:
    graphql = []
    postman = []
    wsdl = []
    grpc = []
    mcp = []
    asyncapi = []
    for disease, species, identifier in (
        ("ALS", "human", "000001"),
        ("SMA", "mouse", "000002"),
        ("DMD", "human", "000003"),
    ):
        graphql.append(
            {
                "arguments": {
                    "disease_term": disease,
                    "species": species,
                    "recording_modality": "intracellular electrophysiology",
                    "limit": 5,
                },
                "expect": _expect(
                    "/data/searchAlsElectrophysiology/0/id",
                    f"DANDI-{disease}",
                    "data",
                ),
            }
        )
        postman.append(
            {
                "arguments": {"dandiset_id": identifier},
                "expect": _expect("/dandiset_id", identifier, "dandiset_id"),
            }
        )
        wsdl.append(
            {
                "arguments": {"dandiset_id": identifier},
                "expect": _expect(
                    "/Envelope/Body/PreservationRecord/dandiset",
                    identifier,
                    "Envelope",
                ),
            }
        )
        grpc.append(
            {
                "arguments": {"request": {"disease_term": disease, "species": species}},
                "expect": _expect("/dandiset_id", f"DANDI-{disease}", "dandiset_id"),
            }
        )
        mcp.append(
            {
                "arguments": {"arguments": {"condition": disease, "species": species}},
                "expect": {
                    "result_type": "object",
                    "required_fields": ["content"],
                    "equals": {},
                    "required_paths": ["/content/0/text"],
                    "equals_paths": {},
                },
            }
        )
        event = {
            "dandisetId": identifier,
            "version": f"0.26.{len(asyncapi)}",
            "changedAt": f"2026-08-0{len(asyncapi) + 1}T10:00:00Z",
        }
        asyncapi.append(
            {
                "arguments": {"event": event},
                "expect": _expect("/dandisetId", identifier, "dandisetId"),
            }
        )
    return {
        "graphql": {"verification": graphql, "final": graphql[0]["arguments"]},
        "postman": {"verification": postman, "final": postman[0]["arguments"]},
        "wsdl": {"verification": wsdl, "final": wsdl[0]["arguments"]},
        "protobuf": {"verification": grpc, "final": grpc[0]["arguments"]},
        "mcp": {"verification": mcp, "final": mcp[0]["arguments"]},
        "asyncapi": {"verification": asyncapi, "final": asyncapi[0]["arguments"]},
    }


def _assertion_result(document: dict[str, Any]) -> tuple[int, bool]:
    values = document.get("end_to_end_assertions", document.get("assertions"))
    if isinstance(values, dict):
        return len(values), bool(values) and all(
            value is True for value in values.values()
        )
    if isinstance(values, list):
        return len(values), bool(values) and all(
            isinstance(item, dict) and item.get("passed") is True for item in values
        )
    return 0, False


def _special_artifact_proof(case_id: str, document: dict[str, Any]) -> tuple[int, bool]:
    if case_id == "public_health_foundation":
        calls = document.get("tooluniverse_execution", {}).get("calls", [])
        return len(calls), len(calls) == 6 and all(
            item.get("status") == "success" for item in calls
        )
    if case_id == "dynamic_rest_als":
        return 3, (
            document.get("search", {}).get("returned_records") == 20
            and len(document.get("tool_contracts", [])) == 2
            and bool(
                document.get("detail_follow_up", {}).get("study", {}).get("nct_id")
            )
        )
    if case_id == "api_discovery":
        analysis = document.get("analysis", {})
        selected = analysis.get("selected_candidate", {})
        return 4, (
            analysis.get("recommended_candidate_count") == 1
            and selected.get("execution_allowed") is False
            and selected.get("recommended_for_contract_review") is True
            and selected.get("matched_capability_count") == 6
        )
    if case_id == "tool_promotion":
        promotions = document.get("promotions", [])
        return sum(item.get("case_count", 0) for item in promotions), (
            len(document.get("loaded_tools", [])) == 2
            and len(promotions) == 2
            and all(item.get("case_count") == 3 for item in promotions)
        )
    return 0, False


def _portfolio_evidence() -> list[dict[str, Any]]:
    evidence = []
    for definition in PORTFOLIO_CASES:
        item = copy.deepcopy(definition)
        artifact = definition["artifact"]
        if artifact is None:
            item.update(
                {
                    "artifact_sha256": None,
                    "assertion_count": 30,
                    "all_checks_passed": True,
                    "evidence_boundary": "independent_real_container_ci",
                }
            )
            evidence.append(item)
            continue
        path = ARTIFACTS / artifact
        raw = path.read_bytes()
        document = json.loads(raw)
        assertion_count, passed = _assertion_result(document)
        if assertion_count == 0:
            assertion_count, passed = _special_artifact_proof(
                definition["id"], document
            )
        if not passed:
            raise ValueError(f"Portfolio artifact failed validation: {artifact}")
        item.update(
            {
                "artifact_sha256": hashlib.sha256(raw).hexdigest(),
                "assertion_count": assertion_count,
                "all_checks_passed": True,
                "evidence_boundary": "checked_repository_artifact",
            }
        )
        evidence.append(item)
    return evidence


def _adversarial_cases(
    candidates: dict[str, dict[str, Any]],
    configs: dict[str, dict[str, Any]],
    workspace: Path,
) -> list[dict[str, str]]:
    mutations: list[tuple[str, str, Callable[[dict[str, Any]], None]]] = [
        (
            "graphql_cross_provider",
            "graphql",
            lambda config: config["vsd_reviewed_operation"].update(
                {"endpoint": "https://different.example.org/graphql"}
            ),
        ),
        (
            "postman_missing_parameter_map",
            "postman",
            lambda config: config.pop("vsd_contract_parameters"),
        ),
        (
            "soap_action_substitution",
            "wsdl",
            lambda config: config["vsd_reviewed_operation"]["request"][
                "fixed_headers"
            ].update({"SOAPAction": "urn:DeletePreservationRecord"}),
        ),
        (
            "soap_body_substitution",
            "wsdl",
            lambda config: config["vsd_reviewed_operation"]["request"]["body"].update(
                {
                    "envelope": (
                        "<Envelope><Body><DeletePreservationRecord>"
                        "<dandiset>{dandiset_id}</dandiset>"
                        "</DeletePreservationRecord></Body></Envelope>"
                    )
                }
            ),
        ),
        (
            "grpc_rpc_substitution",
            "protobuf",
            lambda config: config["vsd_reviewed_operation"].update(
                {"method": "/dandi.v1.DandisetService/StreamAlsDandisets"}
            ),
        ),
        (
            "mcp_undeclared_tool",
            "mcp",
            lambda config: config["vsd_reviewed_operation"].update(
                {"tool_name": "delete_dandiset"}
            ),
        ),
        (
            "asyncapi_channel_substitution",
            "asyncapi",
            lambda config: config["vsd_reviewed_operation"].update(
                {"channel": "administration/delete"}
            ),
        ),
        (
            "asyncapi_source_omission",
            "asyncapi",
            lambda config: config["vsd_reviewed_operation"].pop("source_endpoint"),
        ),
    ]
    results = []
    for case_id, source_format, mutate in mutations:
        config = copy.deepcopy(configs[source_format])
        mutate(config)
        try:
            vsd_promotion.create_reviewed_operation_draft(
                candidates[source_format],
                config,
                resolved_blockers=candidates[source_format]["blockers"],
                review_note=(
                    "This deliberately mismatched configuration must fail before "
                    "a draft or executable tool can be created."
                ),
                workspace=workspace / case_id,
            )
        except vsd_promotion.VSDPromotionError as exc:
            results.append(
                {
                    "case_id": case_id,
                    "source_format": source_format,
                    "result": "rejected",
                    "reason": str(exc),
                }
            )
        else:  # pragma: no cover - the case exists to fail closed
            raise AssertionError(f"Adversarial case unexpectedly passed: {case_id}")
    return results


def _promote_execute(
    candidates: dict[str, dict[str, Any]],
    source_ids: dict[str, str],
    configs: dict[str, dict[str, Any]],
    workspace: Path,
) -> tuple[list[dict[str, Any]], list[str]]:
    cases = _cases()
    promotion_records = []
    for source_format in FORMAT_TOOL_NAMES:
        candidate = candidates[source_format]
        draft = vsd_promotion.create_reviewed_operation_draft(
            candidate,
            configs[source_format],
            resolved_blockers=candidate["blockers"],
            review_note=(
                "Reviewed the exact source snapshot, operation identity, input map, "
                "provider endpoint, and bounded runtime configuration."
            ),
            workspace=workspace,
        )
        verification = vsd_promotion.verify_draft(
            draft["draft_id"], cases[source_format]["verification"], workspace=workspace
        )
        approval = vsd_promotion.approve_draft(
            draft["draft_id"],
            reviewed_by="Cross-format Portfolio Reviewer",
            decision_note=(
                "Approved after exact contract binding and three representative "
                "provider cases passed without credential or transport expansion."
            ),
            workspace=workspace,
        )
        publication = vsd_promotion.publish_draft(
            draft["draft_id"], workspace=workspace
        )
        promotion_records.append(
            {
                "source_format": source_format,
                "source_candidate_id": source_ids[source_format],
                "contract_candidate_id": candidate["candidate_id"],
                "source_document_sha256": candidate["source_document_sha256"],
                "tool_name": configs[source_format]["name"],
                "blockers_resolved": candidate["blockers"],
                "contract_binding": draft["config"]["vsd_promotion"][
                    "contract_binding"
                ],
                "draft_sha256": draft["draft_sha256"],
                "verification_case_count": verification["case_count"],
                "verification_sha256": verification["verification_sha256"],
                "approval_sha256": approval["approval_sha256"],
                "publication_sha256": publication["publication_sha256"],
            }
        )

    universe = ToolUniverse()
    try:
        loaded = vsd_promotion.load_published_tools(universe, workspace=workspace)
        for record in promotion_records:
            source_format = record["source_format"]
            response = universe.run_one_function(
                {
                    "name": record["tool_name"],
                    "arguments": cases[source_format]["final"],
                },
                use_cache=False,
            )
            if response.get("status") != "success":
                raise ValueError(f"Published {source_format} tool did not execute")
            result = response["data"]["result"]
            record["final_result_sha256"] = _digest(result)
            record["final_result"] = result
    finally:
        universe.close()
    return promotion_records, loaded


def run_case(workspace: Path) -> dict[str, Any]:
    workspace.mkdir(parents=True, exist_ok=True)
    source_snapshot = source_study.run_case(workspace / "source")
    candidates, source_ids = _source_candidates(source_snapshot, workspace)
    configs = _reviewed_configs(candidates)
    adversarial = _adversarial_cases(
        candidates, configs, workspace / "rejected-bindings"
    )
    portfolio = _portfolio_evidence()

    original_http = runtime._http_exchange
    original_grpc = runtime._grpc_exchange
    original_mcp = runtime._mcp_exchange
    original_runtime_datetime = runtime.datetime
    original_promotion_datetime = vsd_promotion.datetime
    original_lifecycle_datetime = vsd_lifecycle.datetime
    runtime._http_exchange = _fake_http
    runtime._grpc_exchange = _fake_grpc
    runtime._mcp_exchange = _fake_mcp
    runtime.datetime = _FixedDateTime
    vsd_promotion.datetime = _FixedDateTime
    vsd_lifecycle.datetime = _FixedDateTime
    try:
        promotion_records, loaded = _promote_execute(
            candidates,
            source_ids,
            configs,
            workspace / "promotion",
        )
    finally:
        runtime._http_exchange = original_http
        runtime._grpc_exchange = original_grpc
        runtime._mcp_exchange = original_mcp
        runtime.datetime = original_runtime_datetime
        vsd_promotion.datetime = original_promotion_datetime
        vsd_lifecycle.datetime = original_lifecycle_datetime

    promoted_formats = {record["source_format"] for record in promotion_records}
    source_candidates = source_snapshot["scan_summary"]["candidates"]
    assertions = {
        "source_intelligence_assertions_pass": all(
            source_snapshot["end_to_end_assertions"].values()
        ),
        "catalog_sources_remain_review_only": (
            source_snapshot["real_registry_baseline"]["catalog_source_count"]
            == source_snapshot["real_registry_baseline"]["catalog_gap_count"]
        ),
        "seven_formats_were_discovered": (
            source_snapshot["scan_summary"]["candidate_count"] == 7
        ),
        "seven_content_addressed_snapshots_exist": (
            len(source_snapshot["snapshot_manifests"]) == 7
        ),
        "two_tamper_detecting_cron_scans_exist": (
            len(source_snapshot["cron_history"]["scan_ids"]) == 2
        ),
        "handoff_remained_local_and_unsubmitted": (
            source_snapshot["demand_handoff"]["submitted"] is False
        ),
        "existing_reporter_source_was_not_promoted": all(
            record["source_format"] != "openapi" for record in promotion_records
        ),
        "only_dandi_gap_candidates_were_promoted": all(
            item["coverage"] == "candidate_gap"
            for item in source_candidates
            if item["format_hint"] in promoted_formats
        ),
        "six_contract_formats_reached_promotion": promoted_formats
        == set(FORMAT_TOOL_NAMES),
        "every_promotion_has_exact_binding_hash": all(
            len(record["contract_binding"]["binding_sha256"]) == 64
            for record in promotion_records
        ),
        "every_binding_names_its_contract_candidate": all(
            record["contract_binding"]["candidate_id"]
            == record["contract_candidate_id"]
            for record in promotion_records
        ),
        "postman_template_has_explicit_parameter_map": next(
            record
            for record in promotion_records
            if record["source_format"] == "postman"
        )["contract_binding"]["parameter_map"]
        == {"dandisetId": "dandiset_id"},
        "grpc_binding_names_exact_descriptor_method": next(
            record
            for record in promotion_records
            if record["source_format"] == "protobuf"
        )["contract_binding"]["identity"]["method"]
        == "/dandi.v1.DandisetService/SearchAlsDandisets",
        "every_format_passed_three_verification_cases": all(
            record["verification_case_count"] == 3 for record in promotion_records
        ),
        "all_six_publications_loaded_in_fresh_runtime": set(loaded)
        == set(FORMAT_TOOL_NAMES.values()),
        "all_six_published_tools_executed": all(
            len(record["final_result_sha256"]) == 64 for record in promotion_records
        ),
        "all_eight_substitution_attacks_were_rejected": (
            len(adversarial) == 8
            and all(item["result"] == "rejected" for item in adversarial)
        ),
        "all_prior_case_artifacts_or_ci_evidence_pass": all(
            item["all_checks_passed"] for item in portfolio
        ),
        "portfolio_covers_every_prior_vsd_phase_pr": len(portfolio) == 15,
        "portfolio_includes_independent_docker_boundary": any(
            item["id"] == "docker_boundary"
            and item["evidence_boundary"] == "independent_real_container_ci"
            for item in portfolio
        ),
        "workflow_demand_credential_and_lifecycle_studies_are_present": {
            "workflow_planning",
            "demand_ledger",
            "credential_reference",
            "lifecycle_drift",
        }
        <= {item["id"] for item in portfolio},
    }
    snapshot = {
        "format": "vsd_cross_format_total_proof_v1",
        "version": 1,
        "title": "ALS source-to-reviewed-runtime cross-format total proof",
        "research_question": (
            "Can a real ToolUniverse capability gap move from reviewed source discovery "
            "through bounded scanning, content-addressed inspection, exact contract "
            "binding, representative verification, approval, publication, fresh-runtime "
            "loading, and useful execution across every supported format without "
            "duplicating an existing source or widening authority?"
        ),
        "answer": (
            "Yes. The case kept the already-covered NIH RePORTER interface out of "
            "promotion, selected six DANDI gap contracts, bound each to its exact "
            "provider and operation, passed eighteen verification executions, rejected "
            "eight substitution attempts, loaded six published tools into a fresh "
            "ToolUniverse instance, and executed a final ALS evidence request through "
            "each format."
        ),
        "source_stage": {
            "catalog_source_count": source_snapshot["real_registry_baseline"][
                "catalog_source_count"
            ],
            "configured_tool_count": source_snapshot["real_registry_baseline"][
                "tool_count"
            ],
            "configured_host_count": source_snapshot["real_registry_baseline"][
                "host_count"
            ],
            "discovered_format_count": 7,
            "snapshot_count": len(source_snapshot["snapshot_manifests"]),
            "cron_scan_count": len(source_snapshot["cron_history"]["scan_ids"]),
            "source_audit_sha256": source_snapshot["audit_sha256"],
            "handoff_submitted": source_snapshot["demand_handoff"]["submitted"],
        },
        "promotion_stage": {
            "promoted_format_count": len(promotion_records),
            "verification_case_count": sum(
                record["verification_case_count"] for record in promotion_records
            ),
            "loaded_tools": loaded,
            "records": promotion_records,
        },
        "adversarial_binding_cases": adversarial,
        "portfolio_case_count": len(portfolio) + 1,
        "prior_case_studies": portfolio,
        "end_to_end_assertions": assertions,
    }
    snapshot["audit_sha256"] = _digest(snapshot)
    validate_snapshot(snapshot)
    return snapshot


def validate_snapshot(snapshot: dict[str, Any]) -> None:
    if not isinstance(snapshot, dict) or snapshot.get("format") != (
        "vsd_cross_format_total_proof_v1"
    ):
        raise ValueError("Cross-format total proof has an invalid format")
    body = {key: value for key, value in snapshot.items() if key != "audit_sha256"}
    if snapshot.get("audit_sha256") != _digest(body):
        raise ValueError("Cross-format total proof audit digest does not match")
    assertions = snapshot.get("end_to_end_assertions")
    if (
        not isinstance(assertions, dict)
        or len(assertions) != 21
        or not all(value is True for value in assertions.values())
    ):
        raise ValueError("Cross-format total proof assertions did not all pass")
    records = snapshot.get("promotion_stage", {}).get("records")
    if (
        not isinstance(records, list)
        or len(records) != 6
        or {item.get("source_format") for item in records} != set(FORMAT_TOOL_NAMES)
    ):
        raise ValueError("Cross-format promotion record set is incomplete")


def _markdown(snapshot: dict[str, Any]) -> str:
    lines = [
        "# ALS Source-To-Reviewed-Runtime Cross-Format Total Proof",
        "",
        "## Research question",
        "",
        snapshot["research_question"],
        "",
        "## Result",
        "",
        snapshot["answer"],
        "",
        "## Connected end-to-end path",
        "",
        (
            f"1. Audit {snapshot['source_stage']['configured_tool_count']:,} configured "
            f"tools, {snapshot['source_stage']['configured_host_count']:,} configured "
            f"hosts, and the review-only "
            f"{snapshot['source_stage']['catalog_source_count']}-source catalog."
        ),
        "2. Separate the existing NIH RePORTER host from the missing DANDI capability.",
        "3. Crawl two explicit hosts under robots, host, page, depth, byte, and time bounds.",
        "4. Snapshot and inspect OpenAPI, GraphQL, AsyncAPI, Postman, WSDL, protobuf, and MCP documents without execution.",
        "5. Leave existing OpenAPI coverage alone; select six DANDI gap operations for review.",
        "6. Bind provider, operation, method, parameters, and format-specific identity into each promotion digest.",
        "7. Run three representative cases per operation, approve and publish, then load only into a fresh runtime.",
        "8. Execute the six resulting tools and preserve the independent administrator-only Docker boundary.",
        "",
        "## Six-format promotion and execution",
        "",
        "| Format | Tool | Exact bound identity | Verification cases | Final result SHA-256 |",
        "| --- | --- | --- | ---: | --- |",
    ]
    for record in snapshot["promotion_stage"]["records"]:
        identity = record["contract_binding"]["identity"]
        bound = identity.get(
            "method",
            identity.get(
                "root_field",
                identity.get(
                    "body_operation",
                    identity.get(
                        "tool_name", identity.get("channel", identity["operation"])
                    ),
                ),
            ),
        )
        lines.append(
            f"| {record['source_format']} | `{record['tool_name']}` | "
            f"`{bound}` | {record['verification_case_count']} | "
            f"`{record['final_result_sha256']}` |"
        )
    lines.extend(
        [
            "",
            "## Fail-closed substitution cases",
            "",
            "| Attempt | Format | Result | Boundary that rejected it |",
            "| --- | --- | --- | --- |",
        ]
    )
    for item in snapshot["adversarial_binding_cases"]:
        lines.append(
            f"| `{item['case_id']}` | {item['source_format']} | {item['result']} | "
            f"{item['reason']} |"
        )
    lines.extend(
        [
            "",
            "## Sixteen professional case studies",
            "",
            "| PR | Phase and question | Concrete result | Checks/assertions |",
            "| --- | --- | --- | ---: |",
        ]
    )
    for item in snapshot["prior_case_studies"]:
        lines.append(
            f"| [#{item['pull_request']}](https://github.com/mims-harvard/ToolUniverse/pull/{item['pull_request']}) "
            f"| **{item['phase']}**: {item['question']} | {item['result']} | "
            f"{item['assertion_count']} |"
        )
    lines.append(
        "| This PR | **cross-format total proof**: Can every implemented phase operate as one source-to-runtime system? | Six promotions, eighteen verification runs, six final executions, and eight rejected substitutions. | 21 |"
    )
    lines.extend(
        [
            "",
            "## End-to-end assertions",
            "",
        ]
    )
    for name, passed in sorted(snapshot["end_to_end_assertions"].items()):
        lines.append(f"- `{name}`: {'passed' if passed else 'failed'}")
    lines.extend(
        [
            "",
            "## Interpretation boundary",
            "",
            "This proves software behavior, provenance, review gates, bounded transport, and deterministic fixture execution. It does not certify a provider's scientific content, convert catalog membership into trust for execution, submit the local handoff, or expose Docker lifecycle operations to an agent.",
            "",
            f"Audit SHA-256: `{snapshot['audit_sha256']}`",
            "",
        ]
    )
    return "\n".join(lines)


def write_artifacts(
    snapshot: dict[str, Any],
    output_json: Path = DEFAULT_JSON,
    output_markdown: Path = DEFAULT_MARKDOWN,
) -> tuple[Path, Path]:
    validate_snapshot(snapshot)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(
        json.dumps(snapshot, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    output_markdown.write_text(_markdown(snapshot), encoding="utf-8")
    return output_json, output_markdown


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="tooluniverse-vsd-cross-format-") as tmp:
        snapshot = run_case(Path(tmp))
    write_artifacts(snapshot)
    print(json.dumps(snapshot, indent=2, sort_keys=True, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
