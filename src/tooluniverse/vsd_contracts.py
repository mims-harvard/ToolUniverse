"""Bounded, local-only inspection for API contract formats used by VSD.

Inspection is intentionally separate from execution. Every operation emitted by
this module is inert, content-addressed, and carries explicit blockers that a
later administrator-reviewed promotion step must resolve.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlsplit

import yaml
from graphql import GraphQLSchema, build_client_schema, build_schema
from graphql.type import (
    GraphQLArgument,
    GraphQLEnumType,
    GraphQLInputObjectType,
    GraphQLList,
    GraphQLNonNull,
    GraphQLScalarType,
)
from lxml import etree

from .vsd_openapi import inspect_openapi_document

_VERSION = 1
_MAX_FILE_BYTES = 1_000_000
_MAX_DEPTH = 100
_MAX_NODES = 50_000
_MAX_CANDIDATES = 500
_MAX_TEXT = 2_000
_FORMAT_ALIASES = {
    "gql": "graphql",
    "graphqls": "graphql",
    "yml": "asyncapi",
    "postman_collection": "postman",
    "proto": "protobuf",
    "mcp": "mcp",
    "xml": "wsdl",
}
_FORMAT_SUFFIXES = {
    ".graphql": "graphql",
    ".graphqls": "graphql",
    ".gql": "graphql",
    ".postman_collection.json": "postman",
    ".wsdl": "wsdl",
    ".proto": "protobuf",
    ".mcp.json": "mcp",
}
_PROTO_COMMENT_RE = re.compile(r"//[^\n]*|/\*.*?\*/", re.DOTALL)
_PROTO_SERVICE_RE = re.compile(r"\bservice\s+([A-Za-z_]\w*)\s*\{(.*?)\}", re.DOTALL)
_PROTO_RPC_RE = re.compile(
    r"\brpc\s+([A-Za-z_]\w*)\s*\(\s*(stream\s+)?([.A-Za-z_]\w*)\s*\)"
    r"\s*returns\s*\(\s*(stream\s+)?([.A-Za-z_]\w*)\s*\)\s*"
    r"(?:\{(.*?)\}|;)",
    re.DOTALL,
)
_PROTO_MESSAGE_RE = re.compile(r"\bmessage\s+([A-Za-z_]\w*)\s*\{(.*?)\}", re.DOTALL)
_PROTO_FIELD_RE = re.compile(
    r"\b(?:optional\s+|required\s+|repeated\s+)?"
    r"([.A-Za-z_]\w*(?:\s*<[^;={}]+>)?)\s+([A-Za-z_]\w*)\s*=\s*(\d+)"
)
_CONTRACT_CANDIDATE_KEYS = {
    "format",
    "version",
    "approval_state",
    "execution_allowed",
    "metadata_trust",
    "source_format",
    "source_document_sha256",
    "kind",
    "name",
    "summary",
    "protocol",
    "endpoint",
    "method",
    "input_schema",
    "output_schema",
    "auth",
    "blockers",
    "warnings",
    "contract",
    "candidate_id",
    "candidate_sha256",
}


class VSDContractError(ValueError):
    """Raised when a contract cannot cross the local inspection boundary."""


def _digest(value: Any) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _text(value: Any, *, maximum: int = _MAX_TEXT) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(value.split())[:maximum]


def _walk_bounds(value: Any) -> None:
    stack = [(value, 0)]
    nodes = 0
    while stack:
        current, depth = stack.pop()
        nodes += 1
        if nodes > _MAX_NODES:
            raise VSDContractError("Contract exceeds the node limit")
        if depth > _MAX_DEPTH:
            raise VSDContractError("Contract exceeds the nesting depth limit")
        if isinstance(current, dict):
            for key, child in current.items():
                if not isinstance(key, str):
                    raise VSDContractError("Contract object keys must be strings")
                stack.append((child, depth + 1))
        elif isinstance(current, list):
            stack.extend((child, depth + 1) for child in current)
        elif not isinstance(current, (str, int, float, bool, type(None))):
            raise VSDContractError("Contract contains an unsupported value")


def _read_bytes(path: str | Path) -> tuple[Path, bytes, str]:
    source = Path(path)
    try:
        size = source.stat().st_size
    except OSError as exc:
        raise VSDContractError(f"Cannot read contract: {exc}") from exc
    if size <= 0:
        raise VSDContractError("Contract is empty")
    if size > _MAX_FILE_BYTES:
        raise VSDContractError("Contract exceeds the 1 MB limit")
    try:
        raw = source.read_bytes()
    except OSError as exc:
        raise VSDContractError(f"Cannot read contract: {exc}") from exc
    return source, raw, hashlib.sha256(raw).hexdigest()


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise VSDContractError(f"Duplicate JSON key: {key!r}")
        result[key] = value
    return result


class _StrictSafeLoader(yaml.SafeLoader):
    pass


def _yaml_mapping(loader: _StrictSafeLoader, node: yaml.Node, deep: bool = False):
    pairs = loader.construct_pairs(node, deep=deep)
    return _reject_duplicate_keys(pairs)


_StrictSafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _yaml_mapping
)


def _structured(raw: bytes, *, yaml_allowed: bool) -> dict[str, Any]:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise VSDContractError("Contract must be UTF-8") from exc
    try:
        if yaml_allowed:
            if "&" in text or "*" in text:
                # Anchors and aliases make provenance review needlessly ambiguous.
                for token in yaml.scan(text):
                    if isinstance(token, (yaml.AnchorToken, yaml.AliasToken)):
                        raise VSDContractError(
                            "YAML aliases and anchors are not allowed"
                        )
            value = yaml.load(text, Loader=_StrictSafeLoader)
        else:
            value = json.loads(text, object_pairs_hook=_reject_duplicate_keys)
    except VSDContractError:
        raise
    except (json.JSONDecodeError, yaml.YAMLError) as exc:
        raise VSDContractError(f"Contract is not valid structured data: {exc}") from exc
    if not isinstance(value, dict):
        raise VSDContractError("Contract root must be an object")
    _walk_bounds(value)
    return value


def _https_endpoint(value: Any) -> tuple[str, list[str]]:
    if not isinstance(value, str) or not value.strip():
        return "", ["endpoint_missing"]
    endpoint = value.strip()
    parsed = urlsplit(endpoint)
    if (
        parsed.scheme.casefold() != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.fragment
    ):
        return endpoint, ["endpoint_must_be_https"]
    return endpoint, []


def _candidate(
    *,
    source_format: str,
    document_sha256: str,
    kind: str,
    name: str,
    protocol: str,
    endpoint: str = "",
    method: str = "",
    summary: str = "",
    input_schema: Any = None,
    output_schema: Any = None,
    auth: Any = None,
    blockers: list[str] | None = None,
    warnings: list[str] | None = None,
    contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    body = {
        "format": "vsd_contract_candidate_v1",
        "version": _VERSION,
        "approval_state": "unreviewed_candidate",
        "execution_allowed": False,
        "metadata_trust": "untrusted_contract_metadata",
        "source_format": source_format,
        "source_document_sha256": document_sha256,
        "kind": _text(kind, maximum=100),
        "name": _text(name, maximum=300),
        "summary": _text(summary),
        "protocol": _text(protocol, maximum=100),
        "endpoint": endpoint,
        "method": method.upper(),
        "input_schema": input_schema if isinstance(input_schema, dict) else {},
        "output_schema": output_schema if isinstance(output_schema, dict) else {},
        "auth": auth if isinstance(auth, dict) else {"type": "unspecified"},
        "blockers": sorted(set(blockers or [])),
        "warnings": sorted(set(warnings or [])),
        "contract": contract or {},
    }
    _walk_bounds(body)
    digest = _digest(body)
    return {**body, "candidate_id": digest[:16], "candidate_sha256": digest}


def validate_contract_candidate(candidate: Any) -> dict[str, Any]:
    """Verify origin, integrity, bounds, and inert state of a candidate."""
    if not isinstance(candidate, dict):
        raise VSDContractError("Contract candidate must be an object")
    if set(candidate) != _CONTRACT_CANDIDATE_KEYS:
        raise VSDContractError("Contract candidate fields are invalid")
    if (
        candidate.get("format") != "vsd_contract_candidate_v1"
        or candidate.get("version") != _VERSION
        or candidate.get("approval_state") != "unreviewed_candidate"
        or candidate.get("execution_allowed") is not False
        or candidate.get("metadata_trust") != "untrusted_contract_metadata"
    ):
        raise VSDContractError("Candidate did not come from the contract boundary")
    body = {
        key: value
        for key, value in candidate.items()
        if key not in {"candidate_id", "candidate_sha256"}
    }
    _walk_bounds(body)
    digest = _digest(body)
    if (
        candidate.get("candidate_sha256") != digest
        or candidate.get("candidate_id") != digest[:16]
    ):
        raise VSDContractError("Contract candidate digest does not match its content")
    if candidate.get("source_format") not in {
        "graphql",
        "asyncapi",
        "postman",
        "wsdl",
        "protobuf",
        "mcp",
    }:
        raise VSDContractError("Contract candidate format is unsupported")
    if not re.fullmatch(r"[0-9a-f]{64}", str(candidate.get("source_document_sha256"))):
        raise VSDContractError("Contract candidate source digest is invalid")
    if not isinstance(candidate.get("blockers"), list):
        raise VSDContractError("Contract candidate blockers are invalid")
    return copy.deepcopy(candidate)


def select_contract_candidate(report: Any, candidate_id: str | None) -> dict[str, Any]:
    """Select exactly one candidate from a unified inspection report."""
    if isinstance(report, dict) and report.get("format") == "vsd_contract_candidate_v1":
        if candidate_id is not None and report.get("candidate_id") != candidate_id:
            raise VSDContractError("Requested candidate ID is not present")
        return validate_contract_candidate(report)
    candidates = report.get("candidates") if isinstance(report, dict) else None
    if not isinstance(candidates, list):
        raise VSDContractError("Contract inspection report is invalid")
    matches = [
        item
        for item in candidates
        if candidate_id is None or item.get("candidate_id") == candidate_id
    ]
    if len(matches) != 1:
        raise VSDContractError("Select exactly one contract candidate by candidate ID")
    return validate_contract_candidate(matches[0])


def _report(
    source: Path,
    source_format: str,
    document_sha256: str,
    candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    if not candidates:
        raise VSDContractError("Contract contains no inspectable operations")
    if len(candidates) > _MAX_CANDIDATES:
        raise VSDContractError("Contract exceeds the operation limit")
    return {
        "format": "vsd_contract_inspection_v1",
        "version": _VERSION,
        "source_file": source.name,
        "source_format": source_format,
        "source_document_sha256": document_sha256,
        "candidate_count": len(candidates),
        "reviewable_count": sum(not item["blockers"] for item in candidates),
        "blocked_count": sum(bool(item["blockers"]) for item in candidates),
        "candidates": candidates,
    }


def _graphql_type_schema(value: Any, seen: set[str] | None = None) -> dict[str, Any]:
    required = isinstance(value, GraphQLNonNull)
    current = value.of_type if required else value
    if isinstance(current, GraphQLList):
        schema: dict[str, Any] = {
            "type": "array",
            "items": _graphql_type_schema(current.of_type, seen),
        }
    elif isinstance(current, GraphQLScalarType):
        scalar_type = {
            "Boolean": "boolean",
            "Float": "number",
            "Int": "integer",
        }.get(current.name, "string")
        schema = {"type": scalar_type}
    elif isinstance(current, GraphQLEnumType):
        schema = {"type": "string", "enum": sorted(current.values)}
    elif isinstance(current, GraphQLInputObjectType):
        visited = set(seen or set())
        if current.name in visited:
            return {"type": "object", "additionalProperties": False}
        visited.add(current.name)
        properties = {
            name: _graphql_type_schema(field.type, visited)
            for name, field in current.fields.items()
        }
        required_fields = [
            name
            for name, field in current.fields.items()
            if isinstance(field.type, GraphQLNonNull)
        ]
        schema = {
            "type": "object",
            "properties": properties,
            "additionalProperties": False,
        }
        if required_fields:
            schema["required"] = sorted(required_fields)
    else:
        schema = {"type": "string", "description": f"GraphQL type {current}"}
    if not required:
        schema = {**schema, "nullable": True}
    return schema


def _graphql_arguments(arguments: dict[str, GraphQLArgument]) -> dict[str, Any]:
    properties = {
        name: _graphql_type_schema(argument.type)
        for name, argument in arguments.items()
    }
    required = [
        name
        for name, argument in arguments.items()
        if isinstance(argument.type, GraphQLNonNull)
    ]
    schema: dict[str, Any] = {
        "type": "object",
        "properties": properties,
        "additionalProperties": False,
    }
    if required:
        schema["required"] = sorted(required)
    return schema


def _inspect_graphql(
    source: Path, raw: bytes, document_sha256: str, endpoint_override: str | None
) -> dict[str, Any]:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise VSDContractError("GraphQL contract must be UTF-8") from exc
    try:
        stripped = text.lstrip()
        if stripped.startswith("{"):
            payload = _structured(raw, yaml_allowed=False)
            introspection = payload.get("data", payload)
            if "__schema" not in introspection:
                raise VSDContractError("GraphQL JSON must contain introspection data")
            schema = build_client_schema(introspection)
        else:
            schema = build_schema(text)
    except VSDContractError:
        raise
    except Exception as exc:
        raise VSDContractError(f"GraphQL schema is invalid: {exc}") from exc
    endpoint, endpoint_blockers = _https_endpoint(endpoint_override)
    candidates: list[dict[str, Any]] = []
    roots: list[tuple[str, Any]] = [
        ("query", schema.query_type),
        ("mutation", schema.mutation_type),
        ("subscription", schema.subscription_type),
    ]
    for operation_type, root in roots:
        if root is None:
            continue
        for name, field in sorted(root.fields.items()):
            blockers = list(endpoint_blockers)
            if operation_type != "query":
                blockers.append(f"graphql_{operation_type}_requires_explicit_review")
            output_type = str(field.type)
            candidates.append(
                _candidate(
                    source_format="graphql",
                    document_sha256=document_sha256,
                    kind=f"graphql_{operation_type}",
                    name=name,
                    summary=field.description or name,
                    protocol="graphql",
                    endpoint=endpoint,
                    method="POST",
                    input_schema=_graphql_arguments(field.args),
                    output_schema={"graphql_type": output_type},
                    blockers=blockers,
                    contract={
                        "operation_type": operation_type,
                        "root_type": root.name,
                        "field": name,
                        "deprecated_reason": field.deprecation_reason,
                    },
                    warnings=["deprecated_field"] if field.deprecation_reason else [],
                )
            )
    return _report(source, "graphql", document_sha256, candidates)


def _asyncapi_servers(document: dict[str, Any]) -> dict[str, str]:
    values: dict[str, str] = {}
    for name, server in (document.get("servers") or {}).items():
        if not isinstance(server, dict):
            continue
        host = server.get("host") or server.get("url")
        protocol = _text(server.get("protocol"), maximum=50)
        if isinstance(host, str):
            if "://" not in host and protocol in {"http", "https", "ws", "wss"}:
                host = f"{protocol}://{host}"
            values[str(name)] = host
    return values


def _local_reference(document: dict[str, Any], reference: Any) -> Any:
    if not isinstance(reference, str) or not reference.startswith("#/"):
        return None
    tokens = reference[2:].split("/")
    if not 1 <= len(tokens) <= 20:
        return None
    value: Any = document
    for token in tokens:
        key = token.replace("~1", "/").replace("~0", "~")
        if not isinstance(value, dict) or key not in value:
            return None
        value = value[key]
    return value


def _schema_from_message(
    document: dict[str, Any], message: Any, seen: frozenset[str] = frozenset()
) -> tuple[dict[str, Any], list[str]]:
    if not isinstance(message, dict):
        return {}, []
    reference = message.get("$ref")
    if reference is not None:
        if not isinstance(reference, str) or reference in seen:
            return {}, ["asyncapi_message_reference_requires_local_resolution"]
        resolved = _local_reference(document, reference)
        if not isinstance(resolved, dict):
            return {}, ["asyncapi_message_reference_requires_local_resolution"]
        return _schema_from_message(document, resolved, seen | {reference})
    payload = message.get("payload")
    if isinstance(payload, dict):
        return copy.deepcopy(payload), []
    one_of = message.get("oneOf")
    if isinstance(one_of, list):
        schemas = []
        blockers = []
        for item in one_of:
            schema, item_blockers = _schema_from_message(document, item, seen)
            if schema:
                schemas.append(schema)
            blockers.extend(item_blockers)
        return ({"oneOf": schemas} if schemas else {}), sorted(set(blockers))
    return {}, []


def _inspect_asyncapi(
    source: Path, raw: bytes, document_sha256: str, endpoint_override: str | None
) -> dict[str, Any]:
    document = _structured(raw, yaml_allowed=True)
    version = document.get("asyncapi")
    if not isinstance(version, str) or not version.startswith(("2.", "3.")):
        raise VSDContractError("Only AsyncAPI 2.x and 3.x documents are supported")
    servers = _asyncapi_servers(document)
    channels = document.get("channels")
    if not isinstance(channels, dict) or not channels:
        raise VSDContractError("AsyncAPI channels must be a non-empty object")
    candidates: list[dict[str, Any]] = []
    if version.startswith("3."):
        operations = document.get("operations")
        if not isinstance(operations, dict) or not operations:
            raise VSDContractError("AsyncAPI 3.x operations must be a non-empty object")
        for operation_key, operation in sorted(operations.items()):
            if not isinstance(operation, dict):
                continue
            action = operation.get("action")
            if action not in {"send", "receive"}:
                continue
            channel_reference = operation.get("channel")
            if isinstance(channel_reference, dict) and isinstance(
                channel_reference.get("$ref"), str
            ):
                channel_key = channel_reference["$ref"].split("/")[-1]
                channel = channels.get(channel_key, {})
            elif isinstance(channel_reference, dict):
                channel_key = str(operation_key)
                channel = channel_reference
            else:
                channel_key = str(operation_key)
                channel = {}
            address = (
                channel.get("address", channel_key)
                if isinstance(channel, dict)
                else channel_key
            )
            server_reference = (
                channel.get("servers", [None])[0]
                if isinstance(channel, dict)
                and isinstance(channel.get("servers"), list)
                and channel.get("servers")
                else None
            )
            server_name = (
                server_reference.get("$ref", "").split("/")[-1]
                if isinstance(server_reference, dict)
                else str(server_reference or "")
            )
            raw_endpoint = (
                endpoint_override
                or servers.get(server_name)
                or next(iter(servers.values()), None)
            )
            endpoint, endpoint_blockers = _https_endpoint(raw_endpoint)
            messages = operation.get("messages")
            message: Any = {}
            if isinstance(messages, list) and messages:
                message = messages[0]
            message_schema, message_blockers = _schema_from_message(document, message)
            candidates.append(
                _candidate(
                    source_format="asyncapi",
                    document_sha256=document_sha256,
                    kind=f"asyncapi_{action}",
                    name=operation.get("operationId") or str(operation_key),
                    summary=operation.get("summary") or operation.get("description"),
                    protocol="asyncapi",
                    endpoint=endpoint,
                    input_schema=message_schema,
                    output_schema=message_schema,
                    blockers=[
                        *endpoint_blockers,
                        *message_blockers,
                        f"asyncapi_{action}_requires_bounded_event_runtime",
                    ],
                    contract={
                        "asyncapi_version": version,
                        "action": action,
                        "channel": _text(address, maximum=500),
                    },
                )
            )
        return _report(source, "asyncapi", document_sha256, candidates)

    for channel_name, channel in sorted(channels.items()):
        if not isinstance(channel, dict):
            continue
        address = channel.get("address", channel_name)
        for action in ("publish", "subscribe"):
            operation = channel.get(action)
            if not isinstance(operation, dict):
                continue
            server_names = operation.get("servers") or channel.get("servers") or []
            if isinstance(server_names, list) and server_names:
                server_name = str(server_names[0]).split("/")[-1]
                raw_endpoint = servers.get(server_name)
            else:
                raw_endpoint = endpoint_override or next(iter(servers.values()), None)
            endpoint, endpoint_blockers = _https_endpoint(raw_endpoint)
            message = operation.get("message") or channel.get("messages", {})
            message_schema, message_blockers = _schema_from_message(document, message)
            blockers = [
                *endpoint_blockers,
                *message_blockers,
                f"asyncapi_{action}_requires_bounded_event_runtime",
            ]
            candidates.append(
                _candidate(
                    source_format="asyncapi",
                    document_sha256=document_sha256,
                    kind=f"asyncapi_{action}",
                    name=operation.get("operationId") or f"{action}_{channel_name}",
                    summary=operation.get("summary") or operation.get("description"),
                    protocol="asyncapi",
                    endpoint=endpoint,
                    input_schema=message_schema,
                    output_schema=message_schema,
                    blockers=blockers,
                    contract={
                        "asyncapi_version": version,
                        "action": action,
                        "channel": _text(address, maximum=500),
                    },
                )
            )
    return _report(source, "asyncapi", document_sha256, candidates)


def _postman_variables(document: dict[str, Any]) -> dict[str, str]:
    variables: dict[str, str] = {}
    for item in document.get("variable", []) or []:
        if not isinstance(item, dict) or not isinstance(item.get("key"), str):
            continue
        value = item.get("value")
        if isinstance(value, (str, int, float, bool)):
            variables[item["key"]] = str(value)
    return variables


def _postman_replace(value: str, variables: dict[str, str]) -> tuple[str, list[str]]:
    unresolved: list[str] = []

    def replace(match: re.Match[str]) -> str:
        key = match.group(1).strip()
        if key not in variables:
            unresolved.append(key)
            return match.group(0)
        return variables[key]

    return re.sub(r"\{\{([^{}]+)\}\}", replace, value), unresolved


def _postman_items(items: Any, prefix: str = ""):
    if not isinstance(items, list):
        return
    for item in items:
        if not isinstance(item, dict):
            continue
        name = _text(item.get("name"), maximum=300)
        current = f"{prefix}/{name}".strip("/")
        if isinstance(item.get("item"), list):
            yield from _postman_items(item["item"], current)
        elif isinstance(item.get("request"), dict):
            yield current, item["request"]


def _postman_url(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return str(value.get("raw") or "")
    return ""


def _postman_auth(request: dict[str, Any], document: dict[str, Any]) -> dict[str, Any]:
    auth = request.get("auth", document.get("auth"))
    if auth is None:
        return {"type": "none"}
    if not isinstance(auth, dict):
        return {"type": "invalid"}
    return {"type": _text(auth.get("type"), maximum=80) or "unspecified"}


def _inspect_postman(
    source: Path, raw: bytes, document_sha256: str, endpoint_override: str | None
) -> dict[str, Any]:
    del endpoint_override
    document = _structured(raw, yaml_allowed=False)
    schema = str((document.get("info") or {}).get("schema") or "")
    if "schema.getpostman.com" not in schema:
        raise VSDContractError(
            "Only Postman collection 2.0/2.1 documents are supported"
        )
    variables = _postman_variables(document)
    candidates: list[dict[str, Any]] = []
    for name, request in _postman_items(document.get("item")):
        method = str(request.get("method") or "GET").upper()
        resolved_url, unresolved = _postman_replace(
            _postman_url(request.get("url")), variables
        )
        endpoint, endpoint_blockers = _https_endpoint(resolved_url)
        auth = _postman_auth(request, document)
        blockers = list(endpoint_blockers)
        blockers.extend(f"unresolved_postman_variable:{item}" for item in unresolved)
        if method not in {"GET", "HEAD"}:
            blockers.append("postman_non_read_method_requires_explicit_review")
        body = request.get("body")
        if isinstance(body, dict) and body.get("mode"):
            blockers.append(f"postman_{body['mode']}_body_requires_review")
        if auth["type"] not in {"none", "bearer", "apikey", "oauth2"}:
            blockers.append(f"unsupported_postman_auth:{auth['type']}")
        query_properties: dict[str, Any] = {}
        url_object = request.get("url")
        if isinstance(url_object, dict):
            for query in url_object.get("query", []) or []:
                if isinstance(query, dict) and isinstance(query.get("key"), str):
                    query_properties[query["key"]] = {"type": "string"}
        for variable_name in unresolved:
            query_properties.setdefault(variable_name, {"type": "string"})
        candidates.append(
            _candidate(
                source_format="postman",
                document_sha256=document_sha256,
                kind="postman_request",
                name=name,
                summary=request.get("description")
                if isinstance(request.get("description"), str)
                else name,
                protocol="https",
                endpoint=endpoint,
                method=method,
                input_schema={
                    "type": "object",
                    "properties": query_properties,
                    "additionalProperties": False,
                },
                auth=auth,
                blockers=blockers,
                contract={
                    "collection": _text((document.get("info") or {}).get("name")),
                    "body_mode": body.get("mode") if isinstance(body, dict) else None,
                },
            )
        )
    return _report(source, "postman", document_sha256, candidates)


def _inspect_wsdl(
    source: Path, raw: bytes, document_sha256: str, endpoint_override: str | None
) -> dict[str, Any]:
    if re.search(rb"<!DOCTYPE|<!ENTITY", raw, re.IGNORECASE):
        raise VSDContractError("WSDL DTDs and entities are not allowed")
    parser = etree.XMLParser(
        resolve_entities=False,
        no_network=True,
        load_dtd=False,
        recover=False,
        huge_tree=False,
    )
    try:
        root = etree.fromstring(raw, parser=parser)
    except etree.XMLSyntaxError as exc:
        raise VSDContractError(f"WSDL XML is invalid: {exc}") from exc
    local = etree.QName(root).localname
    if local not in {"definitions", "description"}:
        raise VSDContractError("WSDL root must be definitions or description")
    ns = {key or "wsdl": value for key, value in root.nsmap.items() if value}
    wsdl_uri = etree.QName(root).namespace
    ns["w"] = wsdl_uri
    addresses = root.xpath(
        ".//*[local-name()='service']/*[local-name()='port']/*[local-name()='address']/@location"
    )
    endpoint, endpoint_blockers = _https_endpoint(
        endpoint_override or (addresses[0] if addresses else None)
    )
    actions: dict[str, str] = {}
    for operation in root.xpath(
        ".//*[local-name()='binding']/*[local-name()='operation']"
    ):
        name = operation.get("name")
        action = operation.xpath("./*[local-name()='operation']/@soapAction")
        if name:
            actions[name] = action[0] if action else ""
    candidates: list[dict[str, Any]] = []
    for port_type in root.xpath(
        ".//*[local-name()='portType'] | .//*[local-name()='interface']"
    ):
        interface = port_type.get("name") or "service"
        for operation in port_type.xpath("./*[local-name()='operation']"):
            name = operation.get("name")
            if not name:
                continue
            inputs = operation.xpath("./*[local-name()='input']/@message")
            outputs = operation.xpath("./*[local-name()='output']/@message")
            candidates.append(
                _candidate(
                    source_format="wsdl",
                    document_sha256=document_sha256,
                    kind="soap_operation",
                    name=f"{interface}.{name}",
                    summary=operation.get("documentation") or name,
                    protocol="soap",
                    endpoint=endpoint,
                    method="POST",
                    blockers=[
                        *endpoint_blockers,
                        "soap_operation_requires_explicit_read_only_review",
                    ],
                    contract={
                        "wsdl_version": "2.0" if local == "description" else "1.1",
                        "interface": interface,
                        "operation": name,
                        "soap_action": actions.get(name, ""),
                        "input_message": inputs[0] if inputs else "",
                        "output_message": outputs[0] if outputs else "",
                    },
                )
            )
    return _report(source, "wsdl", document_sha256, candidates)


def _proto_messages(text: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for name, body in _PROTO_MESSAGE_RE.findall(text):
        properties: dict[str, Any] = {}
        for field_type, field_name, field_number in _PROTO_FIELD_RE.findall(body):
            properties[field_name] = {
                "protobuf_type": " ".join(field_type.split()),
                "field_number": int(field_number),
            }
        result[name] = {"type": "object", "properties": properties}
    return result


def _inspect_protobuf(
    source: Path, raw: bytes, document_sha256: str, endpoint_override: str | None
) -> dict[str, Any]:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise VSDContractError("Protobuf source must be UTF-8") from exc
    text = _PROTO_COMMENT_RE.sub("", text)
    if not re.search(r"\bsyntax\s*=\s*['\"]proto[23]['\"]\s*;", text):
        raise VSDContractError("Protobuf source must declare proto2 or proto3 syntax")
    package_match = re.search(
        r"\bpackage\s+([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)\s*;", text
    )
    package = package_match.group(1) if package_match else ""
    messages = _proto_messages(text)
    endpoint, endpoint_blockers = _https_endpoint(endpoint_override)
    candidates: list[dict[str, Any]] = []
    for service, body in _PROTO_SERVICE_RE.findall(text):
        for (
            name,
            client_stream,
            input_type,
            server_stream,
            output_type,
            options,
        ) in _PROTO_RPC_RE.findall(body):
            blockers = [*endpoint_blockers, "grpc_operation_requires_reviewed_channel"]
            if client_stream:
                blockers.append("grpc_client_stream_requires_bounded_runtime")
            if server_stream:
                blockers.append("grpc_server_stream_requires_bounded_runtime")
            full_name = ".".join(part for part in (package, service, name) if part)
            candidates.append(
                _candidate(
                    source_format="protobuf",
                    document_sha256=document_sha256,
                    kind="grpc_rpc",
                    name=full_name,
                    summary=name,
                    protocol="grpc",
                    endpoint=endpoint,
                    method="RPC",
                    input_schema=messages.get(
                        input_type.split(".")[-1], {"protobuf_type": input_type}
                    ),
                    output_schema=messages.get(
                        output_type.split(".")[-1], {"protobuf_type": output_type}
                    ),
                    blockers=blockers,
                    contract={
                        "package": package,
                        "service": service,
                        "rpc": name,
                        "input_type": input_type,
                        "output_type": output_type,
                        "client_streaming": bool(client_stream),
                        "server_streaming": bool(server_stream),
                        "options_sha256": hashlib.sha256(options.encode()).hexdigest(),
                    },
                )
            )
    return _report(source, "protobuf", document_sha256, candidates)


def _mcp_servers(document: dict[str, Any]) -> dict[str, Any]:
    raw = document.get("mcpServers", document.get("servers"))
    if isinstance(raw, dict):
        return raw
    if isinstance(document.get("server"), dict):
        return {"server": document["server"]}
    return {}


def _inspect_mcp(
    source: Path, raw: bytes, document_sha256: str, endpoint_override: str | None
) -> dict[str, Any]:
    document = _structured(raw, yaml_allowed=False)
    servers = _mcp_servers(document)
    captured_tools = document.get("tools")
    if not servers and not isinstance(captured_tools, list):
        raise VSDContractError("MCP manifest must contain servers or captured tools")
    candidates: list[dict[str, Any]] = []
    if isinstance(captured_tools, list):
        endpoint, endpoint_blockers = _https_endpoint(
            endpoint_override or document.get("serverUrl")
        )
        for tool in captured_tools:
            if not isinstance(tool, dict) or not isinstance(tool.get("name"), str):
                continue
            candidates.append(
                _candidate(
                    source_format="mcp",
                    document_sha256=document_sha256,
                    kind="mcp_tool",
                    name=tool["name"],
                    summary=tool.get("description"),
                    protocol="mcp",
                    endpoint=endpoint,
                    method="tools/call",
                    input_schema=tool.get("inputSchema"),
                    output_schema=tool.get("outputSchema"),
                    blockers=[
                        *endpoint_blockers,
                        "mcp_tool_requires_live_identity_verification",
                    ],
                    contract={
                        "server_name": _text(document.get("serverName"), maximum=300)
                    },
                )
            )
    for name, server in sorted(servers.items()):
        if not isinstance(server, dict):
            continue
        endpoint, endpoint_blockers = _https_endpoint(server.get("url"))
        blockers = list(endpoint_blockers)
        if server.get("command") or server.get("args"):
            blockers.append("mcp_local_command_not_allowed")
        if not isinstance(server.get("tools"), list):
            blockers.append("mcp_live_tool_listing_required")
        candidates.append(
            _candidate(
                source_format="mcp",
                document_sha256=document_sha256,
                kind="mcp_server",
                name=str(name),
                summary=server.get("description"),
                protocol="mcp",
                endpoint=endpoint,
                method="tools/list",
                blockers=blockers,
                contract={
                    "transport": _text(server.get("transport") or "http", maximum=50),
                    "declared_tools": [
                        _text(item.get("name"), maximum=300)
                        for item in server.get("tools", [])
                        if isinstance(item, dict)
                    ][:500],
                },
            )
        )
    return _report(source, "mcp", document_sha256, candidates)


def detect_contract_format(path: str | Path, raw: bytes | None = None) -> str:
    """Detect a supported format from an unambiguous suffix or document marker."""
    source = Path(path)
    lower_name = source.name.casefold()
    for suffix, source_format in _FORMAT_SUFFIXES.items():
        if lower_name.endswith(suffix):
            return source_format
    if raw is None:
        _, raw, _ = _read_bytes(source)
    prefix = raw[:100_000].lstrip()
    if prefix.startswith(b"<") and re.search(
        rb"<(?:\w+:)?(?:definitions|description)\b", prefix
    ):
        return "wsdl"
    if re.search(rb"\bsyntax\s*=\s*['\"]proto[23]['\"]", prefix):
        return "protobuf"
    if prefix.startswith(b"{"):
        document = _structured(raw, yaml_allowed=False)
        if "openapi" in document:
            return "openapi"
        if "asyncapi" in document:
            return "asyncapi"
        schema = str((document.get("info") or {}).get("schema") or "")
        if "schema.getpostman.com" in schema:
            return "postman"
        if "__schema" in document or "__schema" in (document.get("data") or {}):
            return "graphql"
        if any(
            key in document for key in ("mcpServers", "server", "serverUrl", "tools")
        ):
            return "mcp"
    try:
        document = _structured(raw, yaml_allowed=True)
    except VSDContractError:
        document = {}
    if "openapi" in document:
        return "openapi"
    if "asyncapi" in document:
        return "asyncapi"
    raise VSDContractError("Contract format could not be detected; pass format_hint")


def inspect_contract_document(
    path: str | Path,
    *,
    format_hint: str | None = None,
    endpoint: str | None = None,
) -> dict[str, Any]:
    """Inspect one local contract without network access or code execution."""
    source, raw, document_sha256 = _read_bytes(path)
    hint = str(format_hint or "").casefold().lstrip(".")
    source_format = (
        _FORMAT_ALIASES.get(hint, hint) if hint else detect_contract_format(source, raw)
    )
    if source_format == "openapi":
        if endpoint is not None:
            raise VSDContractError("OpenAPI endpoints come from the reviewed document")
        return inspect_openapi_document(source)
    handlers: dict[str, Callable[[Path, bytes, str, str | None], dict[str, Any]]] = {
        "graphql": _inspect_graphql,
        "asyncapi": _inspect_asyncapi,
        "postman": _inspect_postman,
        "wsdl": _inspect_wsdl,
        "protobuf": _inspect_protobuf,
        "mcp": _inspect_mcp,
    }
    handler = handlers.get(source_format)
    if handler is None:
        raise VSDContractError(f"Unsupported contract format: {source_format!r}")
    return handler(source, raw, document_sha256, endpoint)
