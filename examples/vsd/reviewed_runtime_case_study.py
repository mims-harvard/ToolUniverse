"""Deterministic reviewed multi-protocol runtime and promotion portfolio."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from google.protobuf import descriptor_pb2

from tooluniverse import ToolUniverse
from tooluniverse import vsd_lifecycle, vsd_promotion
from tooluniverse import vsd_reviewed_runtime as runtime
from tooluniverse.vsd_contracts import inspect_contract_document
from tooluniverse.vsd_reviewed_runtime import VSDReviewedOperationTool

ARTIFACT_DIR = Path(__file__).with_name("artifacts")
JSON_ARTIFACT = ARTIFACT_DIR / "reviewed_runtime_snapshot.json"
MARKDOWN_ARTIFACT = ARTIFACT_DIR / "reviewed_runtime_snapshot.md"
FIXED_TIME = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)


class _FixedDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        return FIXED_TIME if tz is not None else FIXED_TIME.replace(tzinfo=None)


def _metadata(
    url: str, content_type: str, raw: bytes, *, headers=None
) -> dict[str, Any]:
    return {
        "url": url,
        "status_code": 200,
        "content_type": content_type,
        "response_bytes": len(raw),
        "headers": headers or {},
        "peer_ip": "203.0.113.20",
        "redirects": 0,
    }


def _http_config(
    name: str,
    description: str,
    endpoint: str,
    *,
    protocol: str = "rest",
    properties: dict[str, Any],
    request: dict[str, Any],
    response: dict[str, Any],
    pagination: dict[str, Any] | None = None,
    auth: dict[str, Any] | None = None,
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
            "required": list(properties),
            "additionalProperties": False,
        },
        "return_schema": {"type": "object"},
        "vsd_reviewed_operation": {
            "version": 1,
            "transport": "http",
            "protocol": protocol,
            "endpoint": endpoint,
            "timeout_seconds": 20,
            "auth": auth or {"type": "none"},
            "request": request,
            "response": response,
            "pagination": pagination or {"type": "none"},
        },
    }


def _json_response(schema: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"format": "json", "schema": schema or {}, "max_bytes": 100_000}


def _descriptor_set() -> str:
    descriptor = descriptor_pb2.FileDescriptorProto(
        name="variant.proto", package="variants.v1", syntax="proto3"
    )
    request = descriptor.message_type.add(name="VariantRequest")
    request.field.add(
        name="hgvs",
        number=1,
        label=descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL,
        type=descriptor_pb2.FieldDescriptorProto.TYPE_STRING,
    )
    response = descriptor.message_type.add(name="VariantEvidence")
    response.field.add(
        name="classification",
        number=1,
        label=descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL,
        type=descriptor_pb2.FieldDescriptorProto.TYPE_STRING,
    )
    service = descriptor.service.add(name="VariantService")
    service.method.add(
        name="GetEvidence",
        input_type=".variants.v1.VariantRequest",
        output_type=".variants.v1.VariantEvidence",
    )
    return base64.b64encode(
        descriptor_pb2.FileDescriptorSet(file=[descriptor]).SerializeToString()
    ).decode()


def _configs() -> list[tuple[str, str, dict[str, Any], dict[str, Any]]]:
    graphql_query = "query Disease($id: ID!) { disease(id: $id) { id genes trials } }"
    graphql = _http_config(
        "ReviewedRareDiseaseGraphQL",
        "Retrieve one rare-disease evidence record through a reviewed GraphQL query.",
        "https://provider.example.org/graphql",
        protocol="graphql",
        properties={"disease_id": {"type": "string"}},
        request={
            "method": "POST",
            "reviewed_read_only": True,
            "body": {
                "mode": "graphql",
                "query": graphql_query,
                "operation_name": "Disease",
                "arguments": {"disease_id": "id"},
            },
        },
        response=_json_response(),
        auth={
            "type": "oauth2_client_credentials_env",
            "token_url": "https://provider.example.org/oauth/token",
            "client_id_env": "TOOLUNIVERSE_VSD_CASE_CLIENT_ID",
            "client_secret_env": "TOOLUNIVERSE_VSD_CASE_CLIENT_SECRET",
            "scope": "rare-disease.read",
        },
    )
    csv_cohort = _http_config(
        "ReviewedSMACohortCSV",
        "Retrieve bounded longitudinal SMA motor scores from a reviewed CSV export.",
        "https://provider.example.org/cohort.csv",
        properties={"cohort": {"type": "string"}},
        request={
            "method": "GET",
            "query_arguments": {"cohort": "cohort"},
            "body": {"mode": "none"},
        },
        response={
            "format": "csv",
            "delimiter": ",",
            "schema": {"type": "array", "items": {"type": "object"}},
            "max_bytes": 100_000,
        },
        pagination={
            "type": "page",
            "parameter": "page",
            "start": 1,
            "step": 1,
            "max_pages": 4,
            "max_items": 20,
            "items_pointer": "",
        },
    )
    soap = _http_config(
        "ReviewedSMNPanelSOAP",
        "Retrieve one existing SMN molecular panel from a reviewed SOAP operation.",
        "https://provider.example.org/soap",
        protocol="soap",
        properties={"sample_id": {"type": "string"}},
        request={
            "method": "POST",
            "reviewed_read_only": True,
            "fixed_headers": {"SOAPAction": "urn:GetSMNPanel"},
            "body": {
                "mode": "soap",
                "envelope": "<Envelope><Body><GetSMNPanel><sample>{sample_id}</sample></GetSMNPanel></Body></Envelope>",
                "arguments": {"sample_id": "sample"},
            },
        },
        response={"format": "xml", "schema": {"type": "object"}},
    )
    html = _http_config(
        "ReviewedTrialTableHTML",
        "Extract a bounded clinical-trial table from reviewed provider HTML.",
        "https://provider.example.org/trials.html",
        properties={"disease": {"type": "string"}},
        request={
            "method": "GET",
            "query_arguments": {"disease": "condition"},
            "body": {"mode": "none"},
        },
        response={"format": "html", "schema": {"type": "object"}},
    )
    binary = _http_config(
        "ReviewedEvidenceDownload",
        "Download one bounded reviewed evidence report with exact binary provenance.",
        "https://provider.example.org/report.pdf",
        properties={"report_id": {"type": "string"}},
        request={
            "method": "GET",
            "query_arguments": {"report_id": "id"},
            "body": {"mode": "none"},
        },
        response={"format": "binary", "schema": {"type": "object"}},
    )
    sse = _http_config(
        "ReviewedSafetySSE",
        "Capture a bounded server-sent safety-event stream from a reviewed endpoint.",
        "https://provider.example.org/safety-stream",
        properties={"drug": {"type": "string"}},
        request={
            "method": "GET",
            "query_arguments": {"drug": "drug"},
            "body": {"mode": "none"},
        },
        response={
            "format": "sse",
            "max_events": 10,
            "schema": {"type": "array"},
        },
    )
    multipart = _http_config(
        "ReviewedCohortFileAnalysis",
        "Analyze one bounded in-memory cohort file without exposing a local path.",
        "https://provider.example.org/analyze",
        properties={
            "study": {"type": "string"},
            "file_base64": {"type": "string"},
        },
        request={
            "method": "POST",
            "reviewed_read_only": True,
            "body": {
                "mode": "multipart",
                "arguments": {"study": "study"},
                "files": {
                    "file_base64": {
                        "field": "cohort_file",
                        "filename": "cohort.csv",
                        "content_type": "text/csv",
                    }
                },
            },
        },
        response=_json_response(),
    )
    grpc = {
        "name": "ReviewedVariantGRPC",
        "type": "VSDReviewedOperationTool",
        "description": "Retrieve one bounded reviewed SMN1 variant classification through gRPC.",
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
            "endpoint": "provider.example.org:443",
            "method": "/variants.v1.VariantService/GetEvidence",
            "descriptor_set_base64": _descriptor_set(),
            "request_type": "variants.v1.VariantRequest",
            "response_type": "variants.v1.VariantEvidence",
            "streaming": "unary",
            "max_messages": 1,
            "auth": {"type": "none"},
            "response": {"format": "json", "schema": {"type": "object"}},
        },
    }
    mcp = {
        "name": "ReviewedLiteratureMCP",
        "type": "VSDReviewedOperationTool",
        "description": "Run one pinned reviewed MCP literature-synthesis operation.",
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
            "endpoint": "https://provider.example.org/mcp",
            "tool_name": "search_sma_trials",
            "auth": {"type": "none"},
            "response": {"format": "json", "schema": {"type": "object"}},
        },
    }
    event = {
        "name": "ReviewedSignedSafetyEvent",
        "type": "VSDReviewedOperationTool",
        "description": "Validate one signed reviewed neuromuscular safety webhook event.",
        "parameter": {
            "type": "object",
            "properties": {
                "event": {"type": "object"},
                "signature": {"type": "string"},
            },
            "required": ["event", "signature"],
            "additionalProperties": False,
        },
        "vsd_reviewed_operation": {
            "version": 1,
            "transport": "event",
            "protocol": "webhook",
            "channel": "neuromuscular/safety",
            "event_argument": "event",
            "signature_argument": "signature",
            "event_schema": {
                "type": "object",
                "properties": {
                    "drug": {"type": "string"},
                    "event": {"type": "string"},
                    "case_count": {"type": "integer"},
                },
                "required": ["drug", "event", "case_count"],
                "additionalProperties": False,
            },
            "auth": {
                "type": "api_key_header_env",
                "env_var": "TOOLUNIVERSE_VSD_CASE_EVENT_SECRET",
                "header": "X-Signature",
            },
            "response": {"format": "json", "schema": {"type": "object"}},
        },
    }
    safety_event = {
        "drug": "risdiplam",
        "event": "respiratory infection",
        "case_count": 7,
    }
    signature = (
        "sha256="
        + hmac.new(
            b"portfolio-event-secret", runtime._canonical(safety_event), hashlib.sha256
        ).hexdigest()
    )
    return [
        (
            "Rare-disease GraphQL with OAuth",
            "Query ALS genes and trials through a fixed GraphQL document and rotating credential.",
            graphql,
            {"disease_id": "MONDO:0004975"},
        ),
        (
            "Paginated SMA cohort CSV",
            "Aggregate longitudinal motor scores across bounded CSV pages.",
            csv_cohort,
            {"cohort": "SMA-NH-01"},
        ),
        (
            "Legacy molecular panel SOAP",
            "Retrieve one SMN1 copy-number panel with escaped XML input.",
            soap,
            {"sample_id": "S-404"},
        ),
        (
            "Clinical-trial HTML table",
            "Extract structured trial rows while removing executable markup.",
            html,
            {"disease": "spinal muscular atrophy"},
        ),
        (
            "Binary evidence report",
            "Return a bounded base64 report and exact binary digest.",
            binary,
            {"report_id": "RPT-100"},
        ),
        (
            "Bounded safety SSE",
            "Capture two safety events without leaving a stream open.",
            sse,
            {"drug": "risdiplam"},
        ),
        (
            "In-memory multipart analysis",
            "Analyze a cohort CSV without granting provider access to a local file path.",
            multipart,
            {
                "study": "SMA-NH-01",
                "file_base64": base64.b64encode(b"participant,score\nP1,32\n").decode(),
            },
        ),
        (
            "SMN1 variant gRPC",
            "Serialize a descriptor-bound request and normalize the exact response type.",
            grpc,
            {"request": {"hgvs": "NM_000344.4:c.840C>T"}},
        ),
        (
            "Pinned literature MCP",
            "Invoke only the reviewed literature tool rather than exposing arbitrary MCP calls.",
            mcp,
            {"arguments": {"condition": "SMA", "phase": 3}},
        ),
        (
            "Signed safety webhook",
            "Validate schema and HMAC before admitting an externally delivered event.",
            event,
            {"event": safety_event, "signature": signature},
        ),
    ]


def _fake_http(**kwargs):
    url = kwargs["url"]
    if url.endswith("/oauth/token"):
        raw = b'{"access_token":"portfolio-access-token","token_type":"Bearer"}'
        return raw, _metadata(url, "application/json", raw)
    if url.endswith("/graphql"):
        raw = b'{"data":{"disease":{"id":"MONDO:0004975","genes":["SOD1","C9orf72"],"trials":["NCT04194944"]}}}'
        return raw, _metadata(url, "application/json", raw)
    if url.endswith("/cohort.csv"):
        page = int(kwargs["params"]["page"])
        raw = {
            1: b"participant,month,score\nP1,0,32\nP1,6,35\n",
            2: b"participant,month,score\nP2,0,28\n",
        }.get(page, b"participant,month,score\n")
        return raw, _metadata(url, "text/csv", raw)
    if url.endswith("/soap"):
        body = kwargs["body"].decode()
        sample = body.split("<sample>", 1)[1].split("</sample>", 1)[0]
        raw = (
            f"<Envelope><Body><Panel><sample>{sample}</sample>"
            "<gene>SMN1</gene><copyNumber>1</copyNumber></Panel></Body></Envelope>"
        ).encode()
        return raw, _metadata(url, "text/xml", raw)
    if url.endswith("/trials.html"):
        raw = (
            b"<html><head><title>SMA trials</title></head><body><script>remove()</script>"
            b"<table><tr><th>NCT</th><th>Phase</th></tr>"
            b"<tr><td>NCT04194944</td><td>3</td></tr></table></body></html>"
        )
        return raw, _metadata(url, "text/html", raw)
    if url.endswith("/report.pdf"):
        raw = b"%PDF-1.7 reviewed SMA evidence report"
        return raw, _metadata(url, "application/pdf", raw)
    if url.endswith("/safety-stream"):
        raw = (
            b'id: 1\nevent: signal\ndata: {"event":"infection","cases":7}\n\n'
            b'id: 2\nevent: complete\ndata: {"status":"complete"}\n\n'
        )
        return raw, _metadata(url, "text/event-stream", raw)
    if url.endswith("/analyze"):
        raw = b'{"participants":1,"mean_score":32.0}'
        return raw, _metadata(url, "application/json", raw)
    raise AssertionError(url)


def _summary(value: Any) -> dict[str, Any]:
    if isinstance(value, list):
        return {"type": "array", "items": len(value), "sample": value[:2]}
    if isinstance(value, dict):
        compact = {
            key: item
            for key, item in value.items()
            if key not in {"content_base64", "text"}
        }
        if "content_base64" in value:
            compact["content_base64_length"] = len(value["content_base64"])
        if "text" in value:
            compact["text_preview"] = value["text"][:200]
        return {"type": "object", "value": compact}
    return {"type": type(value).__name__, "value": value}


def _promotion_case(root: Path, soap_config: dict[str, Any]) -> dict[str, Any]:
    spec = root / "panel.wsdl"
    spec.write_text(
        """<definitions xmlns="http://schemas.xmlsoap.org/wsdl/"
        xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/">
        <portType name="PanelPort"><operation name="GetSMNPanel">
        <input message="Request"/><output message="Response"/></operation></portType>
        <binding name="PanelBinding" type="PanelPort"><operation name="GetSMNPanel">
        <soap:operation soapAction="urn:GetSMNPanel"/></operation></binding>
        <service name="Lab"><port name="PanelPort" binding="PanelBinding">
        <soap:address location="https://provider.example.org/soap"/>
        </port></service></definitions>""",
        encoding="utf-8",
    )
    candidate = inspect_contract_document(spec)["candidates"][0]
    promoted_config = json.loads(json.dumps(soap_config))
    promoted_config["name"] = "PromotedSMNPanelSOAP"
    draft = vsd_promotion.create_reviewed_operation_draft(
        candidate,
        promoted_config,
        resolved_blockers=candidate["blockers"],
        review_note=(
            "The reviewed SOAP action retrieves an existing panel, the envelope is "
            "fixed, and all candidate blockers are resolved by the bounded runtime."
        ),
        workspace=root,
    )
    cases = [
        {
            "arguments": {"sample_id": sample},
            "expect": {
                "result_type": "object",
                "required_fields": ["Envelope"],
                "equals": {},
                "required_paths": ["/Envelope/Body/Panel/gene"],
                "equals_paths": {"/Envelope/Body/Panel/sample": sample},
            },
        }
        for sample in ("S-101", "S-202", "S-303")
    ]
    evidence = vsd_promotion.verify_draft(draft["draft_id"], cases, workspace=root)
    approval = vsd_promotion.approve_draft(
        draft["draft_id"],
        reviewed_by="Portfolio Reviewer",
        decision_note="Approved after three exact molecular panel retrieval cases passed.",
        workspace=root,
    )
    publication = vsd_promotion.publish_draft(draft["draft_id"], workspace=root)
    universe = ToolUniverse()
    try:
        loaded = vsd_promotion.load_published_tools(universe, workspace=root)
        execution = universe.run_one_function(
            {"name": promoted_config["name"], "arguments": {"sample_id": "S-404"}},
            use_cache=False,
        )
    finally:
        universe.close()
    return {
        "candidate_id": candidate["candidate_id"],
        "candidate_sha256": candidate["candidate_sha256"],
        "draft_id": draft["draft_id"],
        "draft_sha256": draft["draft_sha256"],
        "verification_sha256": evidence["verification_sha256"],
        "approval_sha256": approval["approval_sha256"],
        "publication_sha256": publication["publication_sha256"],
        "loaded_tools": loaded,
        "final_sample": execution["data"]["result"]["Envelope"]["Body"]["Panel"],
    }


def run_case() -> dict[str, Any]:
    original_http = runtime._http_exchange
    original_grpc = runtime._grpc_exchange
    original_mcp = runtime._mcp_exchange
    original_runtime_datetime = runtime.datetime
    original_promotion_datetime = vsd_promotion.datetime
    original_lifecycle_datetime = vsd_lifecycle.datetime
    previous_environment = {
        key: os.environ.get(key)
        for key in (
            "TOOLUNIVERSE_VSD_CASE_CLIENT_ID",
            "TOOLUNIVERSE_VSD_CASE_CLIENT_SECRET",
            "TOOLUNIVERSE_VSD_CASE_EVENT_SECRET",
        )
    }
    runtime._http_exchange = _fake_http
    runtime._grpc_exchange = lambda operation, request: (
        {"classification": "pathogenic", "gene": "SMN1", "hgvs": request["hgvs"]},
        {"messages": 1, "elapsed_seconds": 0.01, "peer": operation["endpoint"]},
    )
    runtime._mcp_exchange = lambda operation, arguments: (
        {
            "content": [
                {
                    "type": "text",
                    "text": f"3 phase-{arguments['phase']} SMA trials with linked evidence",
                }
            ]
        },
        {"tool_name": operation["tool_name"]},
    )
    runtime.datetime = _FixedDateTime
    vsd_promotion.datetime = _FixedDateTime
    vsd_lifecycle.datetime = _FixedDateTime
    os.environ["TOOLUNIVERSE_VSD_CASE_CLIENT_ID"] = "portfolio-client"
    os.environ["TOOLUNIVERSE_VSD_CASE_CLIENT_SECRET"] = "portfolio-client-secret"
    os.environ["TOOLUNIVERSE_VSD_CASE_EVENT_SECRET"] = "portfolio-event-secret"
    try:
        cases = _configs()
        results: list[dict[str, Any]] = []
        assertions: list[dict[str, Any]] = []
        for title, purpose, config, arguments in cases:
            data = VSDReviewedOperationTool(config).run(arguments)["data"]
            provenance = data["provenance"]
            results.append(
                {
                    "title": title,
                    "purpose": purpose,
                    "transport": provenance["transport"],
                    "protocol": provenance["protocol"],
                    "operation_sha256": provenance["operation_sha256"],
                    "payload_sha256": provenance["payload_sha256"],
                    "page_count": provenance["page_count"],
                    "result": _summary(data["result"]),
                }
            )
            rendered = json.dumps(data, sort_keys=True)
            checks = {
                "successful_result": data["result"] is not None,
                "complete_provenance": all(
                    len(provenance[key]) == 64
                    for key in ("operation_sha256", "payload_sha256")
                ),
                "credentials_redacted": all(
                    secret not in rendered
                    for secret in (
                        "portfolio-client-secret",
                        "portfolio-access-token",
                        "portfolio-event-secret",
                    )
                ),
            }
            assertions.extend(
                {
                    "case": title,
                    "assertion": name,
                    "passed": passed,
                }
                for name, passed in checks.items()
            )
        soap_config = next(
            config
            for _, _, config, _ in cases
            if config["name"] == "ReviewedSMNPanelSOAP"
        )
        with tempfile.TemporaryDirectory(
            prefix="tooluniverse-vsd-reviewed-"
        ) as directory:
            promotion = _promotion_case(Path(directory), soap_config)
        promotion_checks = {
            "candidate_bound_to_publication": all(
                len(promotion[key]) == 64
                for key in (
                    "candidate_sha256",
                    "draft_sha256",
                    "verification_sha256",
                    "approval_sha256",
                    "publication_sha256",
                )
            ),
            "fresh_runtime_loaded_exact_tool": promotion["loaded_tools"]
            == ["PromotedSMNPanelSOAP"],
            "published_tool_executed_new_case": promotion["final_sample"]
            == {"sample": "S-404", "gene": "SMN1", "copyNumber": "1"},
        }
        assertions.extend(
            {
                "case": "Promotion pipeline",
                "assertion": name,
                "passed": passed,
            }
            for name, passed in promotion_checks.items()
        )
    finally:
        runtime._http_exchange = original_http
        runtime._grpc_exchange = original_grpc
        runtime._mcp_exchange = original_mcp
        runtime.datetime = original_runtime_datetime
        vsd_promotion.datetime = original_promotion_datetime
        vsd_lifecycle.datetime = original_lifecycle_datetime
        for key, value in previous_environment.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
    if not all(item["passed"] for item in assertions):
        raise AssertionError([item for item in assertions if not item["passed"]])
    body = {
        "format": "vsd_reviewed_runtime_case_v1",
        "case_title": "SMA multi-protocol evidence execution portfolio",
        "clinical_question": (
            "Can ToolUniverse combine rare-disease genes, longitudinal motor scores, "
            "molecular diagnostics, trials, safety signals, literature, and variant "
            "classification when providers use incompatible reviewed protocols and formats?"
        ),
        "conclusion": (
            "Yes. Ten runtime cases exercised reviewed GraphQL, REST, SOAP, gRPC, MCP, "
            "webhook, OAuth, multipart, pagination, JSON, CSV, XML, HTML, binary, and SSE "
            "contracts; an eleventh case completed draft-through-fresh-runtime promotion."
        ),
        "runtime_case_count": len(results),
        "assertion_count": len(assertions),
        "results": results,
        "promotion": promotion,
        "assertions": assertions,
    }
    return {
        **body,
        "case_sha256": hashlib.sha256(
            json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
    }


def _markdown(report: dict[str, Any]) -> str:
    rows = [
        (
            f"| {item['title']} | `{item['transport']}` | `{item['protocol']}` | "
            f"{item['page_count']} | `{item['payload_sha256'][:16]}` |"
        )
        for item in report["results"]
    ]
    promotion = report["promotion"]
    return "\n".join(
        [
            "# Reviewed Multi-protocol Runtime Proof",
            "",
            "## Clinical question",
            "",
            report["clinical_question"],
            "",
            "## Result",
            "",
            report["conclusion"],
            "",
            "| Case | Transport | Protocol | Pages/messages | Payload identity |",
            "| --- | --- | --- | ---: | --- |",
            *rows,
            "",
            "## Promotion proof",
            "",
            f"Candidate `{promotion['candidate_id']}` was bound to draft "
            f"`{promotion['draft_id']}`, verified with three cases, approved, published, "
            "loaded into a fresh ToolUniverse instance, and executed for sample `S-404`.",
            "",
            f"All {report['assertion_count']} assertions passed. Case identity: "
            f"`{report['case_sha256']}`.",
            "",
            "Provider fixtures are deterministic because no provider credentials are "
            "bundled. Contract validation, request construction, response decoding, "
            "schema validation, provenance, promotion, publication, and loading use "
            "production code.",
            "",
        ]
    )


def main() -> None:
    report = run_case()
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    JSON_ARTIFACT.write_text(
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    MARKDOWN_ARTIFACT.write_text(_markdown(report), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "passed",
                "runtime_cases": report["runtime_case_count"],
                "assertions": report["assertion_count"],
                "case_sha256": report["case_sha256"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
