from __future__ import annotations

import base64
import hashlib
import hmac
import json
from copy import deepcopy

import pytest
from google.protobuf import descriptor_pb2

from tooluniverse import ToolUniverse
from tooluniverse import vsd_reviewed_runtime as runtime
from tooluniverse.vsd_reviewed_runtime import (
    VSDReviewedOperationTool,
    VSDReviewedRuntimeError,
    operation_digest,
)

pytestmark = pytest.mark.unit


def _metadata(content_type: str, raw: bytes, *, headers=None):
    return {
        "url": "https://provider.example.org/data",
        "status_code": 200,
        "content_type": content_type,
        "response_bytes": len(raw),
        "headers": headers or {},
        "peer_ip": "203.0.113.10",
        "redirects": 0,
    }


def _http_config(
    *,
    response_format="json",
    response_schema=None,
    properties=None,
    required=None,
    request=None,
    pagination=None,
    auth=None,
    protocol="rest",
):
    properties = properties or {"disease": {"type": "string"}}
    request = request or {
        "method": "GET",
        "path_arguments": {},
        "query_arguments": {"disease": "q"},
        "fixed_query": {},
        "body": {"mode": "none"},
    }
    response = {
        "format": response_format,
        "schema": response_schema or {},
        "max_bytes": 100_000,
    }
    if response_format == "csv":
        response["delimiter"] = ","
    if response_format == "sse":
        response["max_events"] = 5
    return {
        "name": "ReviewedDiseaseEvidence",
        "type": "VSDReviewedOperationTool",
        "description": "Retrieve reviewed disease evidence from a bounded provider operation.",
        "category": "special_tools",
        "cacheable": False,
        "mcp_annotations": {"readOnlyHint": True, "destructiveHint": False},
        "parameter": {
            "type": "object",
            "properties": properties,
            "required": required if required is not None else list(properties),
            "additionalProperties": False,
        },
        "return_schema": {"type": "object"},
        "vsd_reviewed_operation": {
            "version": 1,
            "transport": "http",
            "protocol": protocol,
            "endpoint": "https://provider.example.org/data",
            "timeout_seconds": 20,
            "auth": auth or {"type": "none"},
            "request": request,
            "response": response,
            "pagination": pagination or {"type": "none"},
        },
    }


def _run(config, arguments):
    response = VSDReviewedOperationTool(config).run(arguments)
    assert response["status"] == "success"
    return response["data"]


def test_json_get_has_reviewed_query_and_provenance(monkeypatch):
    calls = []

    def exchange(**kwargs):
        calls.append(kwargs)
        raw = json.dumps({"disease": "ALS", "genes": ["SOD1", "C9orf72"]}).encode()
        return raw, _metadata("application/json", raw)

    monkeypatch.setattr(runtime, "_http_exchange", exchange)
    config = _http_config(
        response_schema={
            "type": "object",
            "required": ["disease", "genes"],
            "properties": {
                "disease": {"type": "string"},
                "genes": {"type": "array", "items": {"type": "string"}},
            },
        }
    )
    data = _run(config, {"disease": "ALS"})
    assert data["result"]["genes"] == ["SOD1", "C9orf72"]
    assert calls[0]["method"] == "GET"
    assert calls[0]["params"] == {"q": "ALS"}
    assert calls[0]["body"] is None
    assert data["provenance"]["operation_sha256"] == operation_digest(config)
    assert data["provenance"]["page_count"] == 1


def test_graphql_query_post_builds_fixed_document_and_variables(monkeypatch):
    observed = {}

    def exchange(**kwargs):
        observed.update(kwargs)
        raw = b'{"data":{"disease":{"id":"MONDO:0004975","gene":"SOD1"}}}'
        return raw, _metadata("application/json; charset=utf-8", raw)

    monkeypatch.setattr(runtime, "_http_exchange", exchange)
    query = "query Disease($id: ID!) { disease(id: $id) { id gene } }"
    config = _http_config(
        protocol="graphql",
        properties={"disease_id": {"type": "string"}},
        request={
            "method": "POST",
            "reviewed_read_only": True,
            "path_arguments": {},
            "query_arguments": {},
            "body": {
                "mode": "graphql",
                "query": query,
                "operation_name": "Disease",
                "arguments": {"disease_id": "id"},
            },
        },
    )
    data = _run(config, {"disease_id": "MONDO:0004975"})
    body = json.loads(observed["body"])
    assert body == {
        "query": query,
        "variables": {"id": "MONDO:0004975"},
        "operationName": "Disease",
    }
    assert observed["headers"]["Content-Type"] == "application/json"
    assert data["result"]["data"]["disease"]["gene"] == "SOD1"


@pytest.mark.parametrize(
    "query",
    [
        'mutation Curate { curateDisease(id: "x") }',
        "subscription Alerts { diseaseAlert { id } }",
        "query A { ping } query B { pong }",
    ],
)
def test_graphql_runtime_rejects_non_query_or_ambiguous_documents(query):
    config = _http_config(
        protocol="graphql",
        properties={"disease_id": {"type": "string"}},
        request={
            "method": "POST",
            "reviewed_read_only": True,
            "body": {
                "mode": "graphql",
                "query": query,
                "arguments": {"disease_id": "id"},
            },
        },
    )
    with pytest.raises(VSDReviewedRuntimeError, match="exactly one query"):
        VSDReviewedOperationTool(config)


def test_csv_page_pagination_aggregates_and_stops_on_empty_page(monkeypatch):
    pages = [
        b"gene,score\nSOD1,0.98\nC9orf72,0.95\n",
        b"gene,score\nTARDBP,0.88\n",
        b"gene,score\n",
    ]
    calls = []

    def exchange(**kwargs):
        raw = pages[len(calls)]
        calls.append(kwargs)
        return raw, _metadata("text/csv", raw)

    monkeypatch.setattr(runtime, "_http_exchange", exchange)
    config = _http_config(
        response_format="csv",
        response_schema={"type": "array", "items": {"type": "object"}},
        pagination={
            "type": "page",
            "parameter": "page",
            "start": 1,
            "step": 1,
            "max_pages": 5,
            "max_items": 20,
            "items_pointer": "",
        },
    )
    data = _run(config, {"disease": "ALS"})
    assert [item["gene"] for item in data["result"]] == ["SOD1", "C9orf72", "TARDBP"]
    assert [call["params"]["page"] for call in calls] == [1, 2, 3]
    assert data["provenance"]["page_count"] == 3


def test_cursor_and_link_header_pagination_are_bounded(monkeypatch):
    cursor_responses = [
        {"items": [{"id": 1}], "next": "abc"},
        {"items": [{"id": 2}], "next": None},
    ]
    calls = []

    def cursor_exchange(**kwargs):
        payload = cursor_responses[len(calls)]
        calls.append(kwargs)
        raw = json.dumps(payload).encode()
        return raw, _metadata("application/json", raw)

    monkeypatch.setattr(runtime, "_http_exchange", cursor_exchange)
    config = _http_config(
        response_schema={"type": "array"},
        pagination={
            "type": "cursor",
            "parameter": "cursor",
            "next_pointer": "/next",
            "items_pointer": "/items",
            "max_pages": 4,
            "max_items": 10,
        },
    )
    data = _run(config, {"disease": "ALS"})
    assert data["result"] == [{"id": 1}, {"id": 2}]
    assert calls[1]["params"]["cursor"] == "abc"

    link_calls = []

    def link_exchange(**kwargs):
        index = len(link_calls)
        link_calls.append(kwargs)
        raw = json.dumps([{"id": index + 1}]).encode()
        headers = (
            {"link": '<https://provider.example.org/data?page=2>; rel="next"'}
            if index == 0
            else {}
        )
        return raw, _metadata("application/json", raw, headers=headers)

    monkeypatch.setattr(runtime, "_http_exchange", link_exchange)
    link_config = _http_config(
        response_schema={"type": "array"},
        pagination={
            "type": "link_header",
            "items_pointer": "",
            "max_pages": 3,
            "max_items": 10,
        },
    )
    assert _run(link_config, {"disease": "ALS"})["result"] == [{"id": 1}, {"id": 2}]
    assert link_calls[1]["url"] == "https://provider.example.org/data"
    assert link_calls[1]["params"]["page"] == "2"


@pytest.mark.parametrize(
    "response_format, content_type, raw, expected",
    [
        (
            "xml",
            "application/xml",
            b"<Disease><id>MONDO:0004975</id><gene>SOD1</gene><gene>TARDBP</gene></Disease>",
            {"Disease": {"id": "MONDO:0004975", "gene": ["SOD1", "TARDBP"]}},
        ),
        (
            "html",
            "text/html",
            b"<html><head><title>SMA Evidence</title></head><body><script>bad()</script><table><tr><th>Gene</th><th>Score</th></tr><tr><td>SMN1</td><td>0.99</td></tr></table><a href='/trial'>Trial</a></body></html>",
            "SMA Evidence",
        ),
        (
            "binary",
            "application/pdf",
            b"%PDF-1.7 reviewed artifact",
            hashlib.sha256(b"%PDF-1.7 reviewed artifact").hexdigest(),
        ),
        (
            "sse",
            "text/event-stream",
            b'id: 1\nevent: evidence\ndata: {"gene":"SMN1"}\n\nid: 2\ndata: complete\n\n',
            2,
        ),
    ],
)
def test_xml_html_binary_and_sse_response_formats(
    monkeypatch, response_format, content_type, raw, expected
):
    monkeypatch.setattr(
        runtime, "_http_exchange", lambda **_: (raw, _metadata(content_type, raw))
    )
    config = _http_config(response_format=response_format)
    result = _run(config, {"disease": "SMA"})["result"]
    if response_format == "html":
        assert result["title"] == expected
        assert "bad()" not in result["text"]
        assert result["tables"][0][1] == ["SMN1", "0.99"]
    elif response_format == "binary":
        assert result["sha256"] == expected
        assert base64.b64decode(result["content_base64"]) == raw
    elif response_format == "sse":
        assert len(result) == expected
        assert result[0]["data"] == {"gene": "SMN1"}
    else:
        assert result == expected


def test_soap_envelope_escapes_values_and_rejects_xml_entities(monkeypatch):
    observed = {}

    def exchange(**kwargs):
        observed.update(kwargs)
        raw = b"<Envelope><Body><Panel><gene>SMN1</gene></Panel></Body></Envelope>"
        return raw, _metadata("text/xml", raw)

    monkeypatch.setattr(runtime, "_http_exchange", exchange)
    config = _http_config(
        protocol="soap",
        response_format="xml",
        properties={"sample_id": {"type": "string"}},
        request={
            "method": "POST",
            "reviewed_read_only": True,
            "fixed_headers": {"SOAPAction": "urn:GetSMNPanel"},
            "body": {
                "mode": "soap",
                "envelope": "<Envelope><Body><GetPanel><sample>{sample_id}</sample></GetPanel></Body></Envelope>",
                "arguments": {"sample_id": "sample"},
            },
        },
    )
    data = _run(config, {"sample_id": "A&B<12>"})
    assert b"A&amp;B&lt;12&gt;" in observed["body"]
    assert data["result"]["Envelope"]["Body"]["Panel"]["gene"] == "SMN1"

    unsafe = deepcopy(config)
    unsafe["vsd_reviewed_operation"]["request"]["body"]["envelope"] = (
        '<!DOCTYPE x [<!ENTITY y SYSTEM "file:///etc/passwd">]>'
        "<Envelope>{sample_id}</Envelope>"
    )
    with pytest.raises(VSDReviewedRuntimeError, match="DTDs or entities"):
        VSDReviewedOperationTool(unsafe)


def test_multipart_accepts_only_bounded_base64_content(monkeypatch):
    observed = {}

    def exchange(**kwargs):
        observed.update(kwargs)
        raw = b'{"accepted":true}'
        return raw, _metadata("application/json", raw)

    monkeypatch.setattr(runtime, "_http_exchange", exchange)
    config = _http_config(
        properties={
            "metadata": {"type": "string"},
            "document": {"type": "string"},
        },
        request={
            "method": "POST",
            "reviewed_read_only": True,
            "body": {
                "mode": "multipart",
                "arguments": {"metadata": "study"},
                "files": {
                    "document": {
                        "field": "evidence_file",
                        "filename": "evidence.csv",
                        "content_type": "text/csv",
                    }
                },
            },
        },
    )
    data = _run(
        config,
        {
            "metadata": "SMA cohort",
            "document": base64.b64encode(b"gene,score\nSMN1,1\n").decode(),
        },
    )
    assert data["result"] == {"accepted": True}
    assert b'filename="evidence.csv"' in observed["body"]
    assert b"gene,score" in observed["body"]
    with pytest.raises(VSDReviewedRuntimeError, match="base64"):
        _run(
            config, {"metadata": "SMA cohort", "document": "C:\\private\\evidence.csv"}
        )


def test_oauth_client_credentials_are_rotatable_and_redacted(monkeypatch):
    calls = []

    def exchange(**kwargs):
        calls.append(kwargs)
        if kwargs["url"].endswith("/oauth/token"):
            raw = b'{"access_token":"rotating-access-token","token_type":"Bearer"}'
            return raw, _metadata("application/json", raw)
        raw = b'{"disease":"ALS"}'
        return raw, _metadata("application/json", raw)

    monkeypatch.setattr(runtime, "_http_exchange", exchange)
    monkeypatch.setenv("TOOLUNIVERSE_VSD_CLIENT_ID", "reviewed-client")
    monkeypatch.setenv("TOOLUNIVERSE_VSD_CLIENT_SECRET", "reviewed-secret")
    config = _http_config(
        auth={
            "type": "oauth2_client_credentials_env",
            "token_url": "https://provider.example.org/oauth/token",
            "client_id_env": "TOOLUNIVERSE_VSD_CLIENT_ID",
            "client_secret_env": "TOOLUNIVERSE_VSD_CLIENT_SECRET",
            "scope": "disease.read",
        }
    )
    data = _run(config, {"disease": "ALS"})
    assert len(calls) == 2
    token_form = calls[0]["body"].decode()
    assert "grant_type=client_credentials" in token_form
    assert "scope=disease.read" in token_form
    assert calls[1]["headers"]["Authorization"] == "Bearer rotating-access-token"
    rendered = json.dumps(data)
    assert "reviewed-secret" not in rendered
    assert "rotating-access-token" not in rendered
    assert data["provenance"]["authentication"] == {
        "type": "oauth2_client_credentials_env",
        "credential_source": "environment",
    }


def test_signed_webhook_and_asyncapi_events_validate_without_opening_listener(
    monkeypatch,
):
    secret = "event-signature-secret"
    monkeypatch.setenv("TOOLUNIVERSE_VSD_EVENT_SECRET", secret)
    config = {
        "name": "ReviewedSafetyEvent",
        "type": "VSDReviewedOperationTool",
        "description": "Validate one signed post-market neuromuscular safety event.",
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
                    "case_count": {"type": "integer", "minimum": 1},
                },
                "required": ["drug", "event", "case_count"],
                "additionalProperties": False,
            },
            "auth": {
                "type": "api_key_header_env",
                "env_var": "TOOLUNIVERSE_VSD_EVENT_SECRET",
                "header": "X-Event-Signature",
            },
            "response": {"format": "json", "schema": {"type": "object"}},
        },
    }
    event = {"drug": "risdiplam", "event": "respiratory infection", "case_count": 7}
    signature = (
        "sha256="
        + hmac.new(
            secret.encode(), runtime._canonical(event), hashlib.sha256
        ).hexdigest()
    )
    data = _run(config, {"event": event, "signature": signature})
    assert data["result"] == event
    assert data["provenance"]["runtime"]["signature_verified"] is True
    assert secret not in json.dumps(data)
    with pytest.raises(VSDReviewedRuntimeError, match="signature"):
        _run(config, {"event": event, "signature": "sha256=" + "0" * 64})


def _descriptor_set() -> str:
    file_descriptor = descriptor_pb2.FileDescriptorProto(
        name="variant.proto", package="variants.v1", syntax="proto3"
    )
    request = file_descriptor.message_type.add(name="VariantRequest")
    request.field.add(
        name="hgvs",
        number=1,
        label=descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL,
        type=descriptor_pb2.FieldDescriptorProto.TYPE_STRING,
    )
    response = file_descriptor.message_type.add(name="VariantEvidence")
    response.field.add(
        name="classification",
        number=1,
        label=descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL,
        type=descriptor_pb2.FieldDescriptorProto.TYPE_STRING,
    )
    service = file_descriptor.service.add(name="VariantService")
    method = service.method.add(
        name="GetEvidence",
        input_type=".variants.v1.VariantRequest",
        output_type=".variants.v1.VariantEvidence",
    )
    del method
    descriptor_set = descriptor_pb2.FileDescriptorSet(file=[file_descriptor])
    return base64.b64encode(descriptor_set.SerializeToString()).decode()


def test_grpc_descriptor_identity_and_bounded_transport(monkeypatch):
    observed = {}

    def exchange(operation, request):
        observed.update({"operation": operation, "request": request})
        return {"classification": "pathogenic"}, {
            "messages": 1,
            "elapsed_seconds": 0.01,
            "peer": operation["endpoint"],
        }

    monkeypatch.setattr(runtime, "_grpc_exchange", exchange)
    config = {
        "name": "ReviewedVariantEvidence",
        "type": "VSDReviewedOperationTool",
        "description": "Retrieve one reviewed SMN1 variant classification through gRPC.",
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
            "endpoint": "grpc.example.org:443",
            "method": "/variants.v1.VariantService/GetEvidence",
            "descriptor_set_base64": _descriptor_set(),
            "request_type": "variants.v1.VariantRequest",
            "response_type": "variants.v1.VariantEvidence",
            "streaming": "unary",
            "max_messages": 1,
            "auth": {"type": "none"},
            "response": {
                "format": "json",
                "schema": {
                    "type": "object",
                    "properties": {"classification": {"type": "string"}},
                    "required": ["classification"],
                },
            },
        },
    }
    data = _run(config, {"request": {"hgvs": "NM_000344.4:c.840C>T"}})
    assert observed["request"]["hgvs"].endswith("840C>T")
    assert runtime._grpc_classes(config["vsd_reviewed_operation"])[
        0
    ].DESCRIPTOR.full_name == ("variants.v1.VariantRequest")
    assert data["result"] == {"classification": "pathogenic"}


def test_production_grpc_exchange_pins_tls_authority_and_serializes_descriptors(
    monkeypatch,
):
    import grpc
    from google.protobuf.json_format import ParseDict

    operation = {
        "endpoint": "grpc.example.org:443",
        "method": "/variants.v1.VariantService/GetEvidence",
        "descriptor_set_base64": _descriptor_set(),
        "request_type": "variants.v1.VariantRequest",
        "response_type": "variants.v1.VariantEvidence",
        "streaming": "unary",
        "max_messages": 1,
        "timeout_seconds": 20,
    }
    _, response_class = runtime._grpc_classes(operation)
    response_message = ParseDict({"classification": "pathogenic"}, response_class())
    observed = {}

    class FakeChannel:
        def unary_unary(self, method, *, request_serializer, response_deserializer):
            observed["method"] = method

            def call(request, *, timeout):
                observed["request_bytes"] = request_serializer(request)
                observed["timeout"] = timeout
                return response_deserializer(response_message.SerializeToString())

            return call

        def close(self):
            observed["closed"] = True

    def secure_channel(target, credentials, *, options):
        observed.update(
            {"target": target, "credentials": credentials, "options": options}
        )
        return FakeChannel()

    monkeypatch.setattr(grpc, "secure_channel", secure_channel)
    monkeypatch.setattr(grpc, "ssl_channel_credentials", lambda: "tls")
    monkeypatch.setattr(
        "tooluniverse.vsd_tool._resolve_public_addresses",
        lambda host, port: ("203.0.113.30",),
    )
    result, metadata = runtime._grpc_exchange(
        operation, {"hgvs": "NM_000344.4:c.840C>T"}
    )
    assert result == {"classification": "pathogenic"}
    assert observed["target"] == "203.0.113.30:443"
    assert ("grpc.ssl_target_name_override", "grpc.example.org") in observed["options"]
    assert observed["method"] == operation["method"]
    assert observed["request_bytes"]
    assert observed["closed"] is True
    assert metadata["peer"] == "grpc.example.org:443"


def test_mcp_wrapper_fixes_remote_tool_identity(monkeypatch):
    monkeypatch.setattr(
        runtime,
        "_mcp_exchange",
        lambda operation, arguments: (
            {"content": [{"type": "text", "text": "three SMA trials"}]},
            {"tool_name": operation["tool_name"]},
        ),
    )
    config = {
        "name": "ReviewedSMATrialSearch",
        "type": "VSDReviewedOperationTool",
        "description": "Run one fixed reviewed MCP literature search tool.",
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
            "endpoint": "https://literature.example.org/mcp",
            "tool_name": "search_sma_trials",
            "auth": {"type": "none"},
            "response": {"format": "json", "schema": {"type": "object"}},
        },
    }
    data = _run(config, {"arguments": {"phase": 3}})
    assert data["result"]["content"][0]["text"] == "three SMA trials"
    assert data["provenance"]["runtime"]["tool_name"] == "search_sma_trials"


def test_config_validation_fails_closed_for_write_post_unmapped_inputs_and_bad_limits():
    write = _http_config(
        request={
            "method": "POST",
            "query_arguments": {"disease": "q"},
            "body": {"mode": "none"},
        }
    )
    with pytest.raises(VSDReviewedRuntimeError, match="reviewed_read_only"):
        VSDReviewedOperationTool(write)

    unmapped = _http_config()
    unmapped["parameter"]["properties"]["unused"] = {"type": "string"}
    unmapped["parameter"]["required"].append("unused")
    with pytest.raises(VSDReviewedRuntimeError, match="unmapped"):
        VSDReviewedOperationTool(unmapped)

    excessive = _http_config()
    excessive["vsd_reviewed_operation"]["response"]["max_bytes"] = 1_000_001
    with pytest.raises(VSDReviewedRuntimeError, match="max_bytes"):
        VSDReviewedOperationTool(excessive)

    external_link = '<https://attacker.example.org/data?page=2>; rel="next"'
    with pytest.raises(VSDReviewedRuntimeError, match="changed provider host"):
        runtime._next_link(external_link, "provider.example.org")


class _FakeSocket:
    def __init__(self, address="203.0.113.10"):
        self.address = address

    def getpeername(self):
        return self.address, 443

    def settimeout(self, value):
        self.timeout = value


class _FakeRaw:
    def __init__(self, content, address="203.0.113.10"):
        self.content = content
        self.offset = 0
        self.decode_content = False
        self._connection = type("Connection", (), {"sock": _FakeSocket(address)})()

    def read(self, size, decode_content=False):
        del decode_content
        chunk = self.content[self.offset : self.offset + size]
        self.offset += len(chunk)
        return chunk


class _FakeResponse:
    def __init__(self, content, *, status=200, headers=None, address="203.0.113.10"):
        self.status_code = status
        self.headers = headers or {"Content-Type": "application/json"}
        self.raw = _FakeRaw(content, address)
        self.closed = False

    def raise_for_status(self):
        if self.status_code >= 400:
            raise runtime.requests.HTTPError("failed")

    def close(self):
        self.closed = True


class _FakeSession:
    def __init__(self, response):
        self.response = response
        self.request_kwargs = None
        self.mounted = None
        self.closed = False

    def mount(self, prefix, adapter):
        self.mounted = (prefix, adapter)

    def request(self, *args, **kwargs):
        self.request_kwargs = (args, kwargs)
        return self.response

    def close(self):
        self.closed = True


def test_low_level_http_exchange_pins_peer_disables_redirects_and_bounds_bytes(
    monkeypatch,
):
    raw = b'{"ok":true}'
    response = _FakeResponse(
        raw,
        headers={
            "Content-Type": "application/json",
            "Content-Length": str(len(raw)),
        },
    )
    session = _FakeSession(response)
    monkeypatch.setattr(runtime.requests, "Session", lambda: session)
    monkeypatch.setattr(
        runtime,
        "_validated_source_target",
        lambda url: (url, "provider.example.org", ("203.0.113.10",)),
    )
    monkeypatch.setattr(runtime, "_require_global_ip", lambda *_, **__: None)
    content, metadata = runtime._http_exchange(
        method="POST",
        url="https://provider.example.org/query",
        params={"disease": "ALS"},
        headers={"Content-Type": "application/json"},
        body=b"{}",
        timeout=10,
        max_bytes=100,
    )
    assert content == raw
    assert metadata["peer_ip"] == "203.0.113.10"
    assert session.mounted[0] == "https://"
    assert session.request_kwargs[1]["allow_redirects"] is False
    assert session.request_kwargs[1]["stream"] is True
    assert session.closed and response.closed


def test_low_level_http_exchange_rejects_a_closed_zero_body_redirect(monkeypatch):
    response = _FakeResponse(
        b"",
        status=302,
        headers={"Location": "https://provider.example.org/moved"},
    )
    response.raw._connection = None
    session = _FakeSession(response)
    monkeypatch.setattr(runtime.requests, "Session", lambda: session)
    monkeypatch.setattr(
        runtime,
        "_validated_source_target",
        lambda url: (url, "provider.example.org", ("203.0.113.10",)),
    )

    with pytest.raises(runtime.VSDReviewedRuntimeError, match="redirects"):
        runtime._http_exchange(
            method="GET",
            url="https://provider.example.org/data.csv",
            params={},
            headers={},
            body=None,
            timeout=10,
            max_bytes=100,
        )

    assert session.closed and response.closed


@pytest.mark.parametrize(
    "response, message",
    [
        (_FakeResponse(b"{}", address="203.0.113.11"), "vetted DNS"),
        (
            _FakeResponse(
                b"{}",
                headers={
                    "Content-Type": "application/json",
                    "Content-Encoding": "gzip",
                },
            ),
            "Compressed",
        ),
        (
            _FakeResponse(
                b"x" * 101,
                headers={"Content-Type": "application/octet-stream"},
            ),
            "byte limit",
        ),
    ],
)
def test_low_level_http_exchange_rejects_peer_encoding_and_overflow(
    monkeypatch, response, message
):
    session = _FakeSession(response)
    monkeypatch.setattr(runtime.requests, "Session", lambda: session)
    monkeypatch.setattr(
        runtime,
        "_validated_source_target",
        lambda url: (url, "provider.example.org", ("203.0.113.10",)),
    )
    monkeypatch.setattr(runtime, "_require_global_ip", lambda *_, **__: None)
    with pytest.raises(VSDReviewedRuntimeError, match=message):
        runtime._http_exchange(
            method="GET",
            url="https://provider.example.org/data",
            params={},
            headers={},
            body=None,
            timeout=10,
            max_bytes=100,
        )
