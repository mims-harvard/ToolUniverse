"""Reviewed multi-protocol execution for VSD publications.

This runtime accepts only exact administrator-reviewed configurations. It does
not discover providers or convert unreviewed contract metadata into tools.
"""

from __future__ import annotations

import base64
import copy
import csv
import hashlib
import hmac
import io
import ipaddress
import json
import math
import os
import re
import time
from datetime import datetime, timezone
from html import escape
from typing import Any, Iterator
from urllib.parse import parse_qsl, quote, urlencode, urljoin, urlsplit, urlunsplit

import requests
from bs4 import BeautifulSoup
from graphql import OperationType, parse as parse_graphql
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError
from lxml import etree
from urllib3.util import Timeout as Urllib3Timeout

from .base_tool import BaseTool
from .tool_registry import register_tool
from .vsd_dynamic_rest import (
    VSDDynamicRESTError,
    _contains_secret,
    _credential_headers,
    _schema_validator,
    _validated_auth,
)
from .vsd_tool import (
    VSDPolicyError,
    _PinnedHTTPSAdapter,
    _peer_address,
    _require_global_ip,
    _response_chunks,
    _validated_params,
    _validated_source_target,
)

_TOOL_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{2,127}$")
_ARGUMENT_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,63}$")
_PROVIDER_NAME_RE = re.compile(r"^[A-Za-z0-9_.\[\]-]{1,128}$")
_HEADER_RE = re.compile(r"^[!#$%&'*+.^_`|~0-9A-Za-z-]{1,128}$")
_ENV_RE = re.compile(r"^TOOLUNIVERSE_VSD_[A-Z0-9_]{1,108}$")
_POINTER_RE = re.compile(r"^(?:/(?:[^~/]|~[01])*)*$")
_MAX_RESPONSE_BYTES = 1_000_000
_MAX_REQUEST_BYTES = 512_000
_MAX_PAGES = 10
_MAX_ITEMS = 1_000
_FORBIDDEN_FIXED_HEADERS = {
    "authorization",
    "connection",
    "content-length",
    "content-type",
    "cookie",
    "host",
    "origin",
    "proxy-authorization",
    "referer",
    "transfer-encoding",
    "user-agent",
}


class VSDReviewedRuntimeError(VSDDynamicRESTError):
    """Raised when a reviewed runtime contract or result violates policy."""


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise VSDReviewedRuntimeError("Value is not finite JSON") from exc


def _pointer(value: Any, pointer: str) -> Any:
    if not isinstance(pointer, str) or not _POINTER_RE.fullmatch(pointer):
        raise VSDReviewedRuntimeError("JSON pointer is invalid")
    current = value
    if not pointer:
        return current
    for raw in pointer.split("/")[1:]:
        token = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(current, dict) and token in current:
            current = current[token]
        elif (
            isinstance(current, list) and token.isdigit() and int(token) < len(current)
        ):
            current = current[int(token)]
        else:
            return None
    return current


def _validated_endpoint(value: Any, *, field: str = "endpoint") -> str:
    if not isinstance(value, str) or not value:
        raise VSDReviewedRuntimeError(f"{field} must be a non-empty HTTPS URL")
    parsed = urlsplit(value)
    if (
        parsed.scheme.casefold() != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.fragment
    ):
        raise VSDReviewedRuntimeError(
            f"{field} must be an HTTPS URL without credentials"
        )
    return value


def _validated_fixed_headers(value: Any) -> dict[str, str]:
    if value is None:
        return {}
    if not isinstance(value, dict) or len(value) > 6:
        raise VSDReviewedRuntimeError("fixed_headers must contain at most six entries")
    result: dict[str, str] = {}
    for name, header_value in value.items():
        if (
            not isinstance(name, str)
            or not _HEADER_RE.fullmatch(name)
            or name.casefold() in _FORBIDDEN_FIXED_HEADERS
            or name.casefold().startswith(("proxy-", "sec-", "x-forwarded-"))
        ):
            raise VSDReviewedRuntimeError(f"Fixed header {name!r} is prohibited")
        if (
            not isinstance(header_value, str)
            or not 1 <= len(header_value) <= 4096
            or any(
                ord(character) < 32 or ord(character) > 126
                for character in header_value
            )
        ):
            raise VSDReviewedRuntimeError(f"Fixed header {name!r} is invalid")
        result[name] = header_value
    return result


def _validated_extended_auth(value: Any) -> dict[str, Any]:
    if (
        not isinstance(value, dict)
        or value.get("type") != "oauth2_client_credentials_env"
    ):
        try:
            return _validated_auth(value)
        except VSDDynamicRESTError as exc:
            raise VSDReviewedRuntimeError(str(exc)) from exc
    required = {"type", "token_url", "client_id_env", "client_secret_env"}
    optional = {"scope", "audience"}
    if set(value) - required - optional or not required <= set(value):
        raise VSDReviewedRuntimeError(
            "OAuth client-credentials configuration is invalid"
        )
    result: dict[str, Any] = {
        "type": value["type"],
        "token_url": _validated_endpoint(value["token_url"], field="OAuth token_url"),
    }
    for field in ("client_id_env", "client_secret_env"):
        env_name = value[field]
        if not isinstance(env_name, str) or not _ENV_RE.fullmatch(env_name):
            raise VSDReviewedRuntimeError(
                f"OAuth {field} must be a VSD environment name"
            )
        result[field] = env_name
    for field in optional:
        if field in value:
            item = value[field]
            if (
                not isinstance(item, str)
                or not 1 <= len(item) <= 1000
                or any(
                    ord(character) < 32 or ord(character) > 126 for character in item
                )
            ):
                raise VSDReviewedRuntimeError(f"OAuth {field} is invalid")
            result[field] = item
    return result


def _validated_mapping(
    value: Any, properties: dict[str, Any], *, field: str
) -> dict[str, str]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise VSDReviewedRuntimeError(f"{field} must be an object")
    result: dict[str, str] = {}
    for argument, provider in value.items():
        if (
            not isinstance(argument, str)
            or not _ARGUMENT_RE.fullmatch(argument)
            or argument not in properties
            or not isinstance(provider, str)
            or not _PROVIDER_NAME_RE.fullmatch(provider)
        ):
            raise VSDReviewedRuntimeError(
                f"{field} contains an invalid argument mapping"
            )
        result[argument] = provider
    if len(set(result.values())) != len(result):
        raise VSDReviewedRuntimeError(f"{field} provider names must be unique")
    return result


def _validated_response(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise VSDReviewedRuntimeError("response must be an object")
    response_format = value.get("format")
    if response_format not in {"json", "csv", "xml", "html", "binary", "sse"}:
        raise VSDReviewedRuntimeError("response.format is unsupported")
    maximum = value.get("max_bytes", _MAX_RESPONSE_BYTES)
    if (
        isinstance(maximum, bool)
        or not isinstance(maximum, int)
        or not 1 <= maximum <= _MAX_RESPONSE_BYTES
    ):
        raise VSDReviewedRuntimeError(
            "response.max_bytes must be between 1 and 1,000,000"
        )
    schema = value.get("schema", {})
    _schema_validator(schema, field="response.schema")
    root_pointer = value.get("root_pointer", "")
    if not isinstance(root_pointer, str) or not _POINTER_RE.fullmatch(root_pointer):
        raise VSDReviewedRuntimeError("response.root_pointer is invalid")
    result = {
        "format": response_format,
        "max_bytes": maximum,
        "schema": copy.deepcopy(schema),
        "root_pointer": root_pointer,
    }
    if response_format == "csv":
        result["delimiter"] = value.get("delimiter", ",")
        if result["delimiter"] not in {",", "\t", ";", "|"}:
            raise VSDReviewedRuntimeError("CSV delimiter is unsupported")
    if response_format == "sse":
        max_events = value.get("max_events", 100)
        if (
            isinstance(max_events, bool)
            or not isinstance(max_events, int)
            or not 1 <= max_events <= 500
        ):
            raise VSDReviewedRuntimeError("SSE max_events must be between 1 and 500")
        result["max_events"] = max_events
    return result


def _validated_pagination(value: Any, properties: dict[str, Any]) -> dict[str, Any]:
    if value is None or (isinstance(value, dict) and value.get("type") == "none"):
        return {"type": "none", "max_pages": 1, "max_items": _MAX_ITEMS}
    if not isinstance(value, dict):
        raise VSDReviewedRuntimeError("pagination must be an object")
    kind = value.get("type")
    if kind not in {"page", "offset", "cursor", "link_header"}:
        raise VSDReviewedRuntimeError("pagination.type is unsupported")
    max_pages = value.get("max_pages", 5)
    max_items = value.get("max_items", 500)
    if (
        isinstance(max_pages, bool)
        or not isinstance(max_pages, int)
        or not 1 <= max_pages <= _MAX_PAGES
    ):
        raise VSDReviewedRuntimeError("pagination.max_pages must be between 1 and 10")
    if (
        isinstance(max_items, bool)
        or not isinstance(max_items, int)
        or not 1 <= max_items <= _MAX_ITEMS
    ):
        raise VSDReviewedRuntimeError("pagination.max_items must be between 1 and 1000")
    result: dict[str, Any] = {
        "type": kind,
        "max_pages": max_pages,
        "max_items": max_items,
        "items_pointer": value.get("items_pointer", ""),
    }
    if not isinstance(result["items_pointer"], str) or not _POINTER_RE.fullmatch(
        result["items_pointer"]
    ):
        raise VSDReviewedRuntimeError("pagination.items_pointer is invalid")
    if kind in {"page", "offset", "cursor"}:
        parameter = value.get("parameter")
        if not isinstance(parameter, str) or not _PROVIDER_NAME_RE.fullmatch(parameter):
            raise VSDReviewedRuntimeError("pagination.parameter is invalid")
        result["parameter"] = parameter
    if kind in {"page", "offset"}:
        start = value.get("start", 1 if kind == "page" else 0)
        step = value.get("step", 1 if kind == "page" else 100)
        if (
            any(
                isinstance(item, bool) or not isinstance(item, int) or item < 0
                for item in (start, step)
            )
            or step == 0
        ):
            raise VSDReviewedRuntimeError(
                "pagination start and step must be non-negative integers"
            )
        result.update({"start": start, "step": step})
    if kind == "cursor":
        next_pointer = value.get("next_pointer")
        if (
            not isinstance(next_pointer, str)
            or not next_pointer
            or not _POINTER_RE.fullmatch(next_pointer)
        ):
            raise VSDReviewedRuntimeError("cursor pagination requires next_pointer")
        result["next_pointer"] = next_pointer
    del properties
    return result


def _validated_http_request(
    value: Any, properties: dict[str, Any], protocol: str
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise VSDReviewedRuntimeError("request must be an object")
    method = str(value.get("method") or "GET").upper()
    if method not in {"GET", "POST"}:
        raise VSDReviewedRuntimeError("Reviewed HTTP runtime supports GET and POST")
    if method == "POST" and value.get("reviewed_read_only") is not True:
        raise VSDReviewedRuntimeError("POST requires reviewed_read_only=true")
    path_arguments = _validated_mapping(
        value.get("path_arguments"), properties, field="path_arguments"
    )
    query_arguments = _validated_mapping(
        value.get("query_arguments"), properties, field="query_arguments"
    )
    body = value.get("body", {"mode": "none"})
    if not isinstance(body, dict):
        raise VSDReviewedRuntimeError("request.body must be an object")
    mode = body.get("mode", "none")
    if mode not in {"none", "json", "form", "multipart", "graphql", "soap"}:
        raise VSDReviewedRuntimeError("request.body.mode is unsupported")
    if method == "GET" and mode != "none":
        raise VSDReviewedRuntimeError("GET requests cannot contain a body")
    body_arguments = _validated_mapping(
        body.get("arguments"), properties, field="body.arguments"
    )
    normalized_body: dict[str, Any] = {"mode": mode, "arguments": body_arguments}
    fixed = body.get("fixed", {})
    if not isinstance(fixed, dict):
        raise VSDReviewedRuntimeError("request.body.fixed must be an object")
    _canonical(fixed)
    normalized_body["fixed"] = copy.deepcopy(fixed)
    if set(fixed) & set(body_arguments.values()):
        raise VSDReviewedRuntimeError("Fixed and argument body fields overlap")
    if mode == "graphql":
        query = body.get("query")
        if not isinstance(query, str) or not 1 <= len(query.encode("utf-8")) <= 65_536:
            raise VSDReviewedRuntimeError("GraphQL query must contain 1-65536 bytes")
        try:
            document = parse_graphql(query)
        except Exception as exc:
            raise VSDReviewedRuntimeError(f"GraphQL query is invalid: {exc}") from exc
        operations = [
            item for item in document.definitions if hasattr(item, "operation")
        ]
        if len(operations) != 1 or operations[0].operation is not OperationType.QUERY:
            raise VSDReviewedRuntimeError(
                "GraphQL runtime permits exactly one query operation"
            )
        normalized_body["query"] = query
        normalized_body["operation_name"] = body.get("operation_name")
        if normalized_body["operation_name"] is not None and not isinstance(
            normalized_body["operation_name"], str
        ):
            raise VSDReviewedRuntimeError("GraphQL operation_name is invalid")
    if mode == "soap":
        envelope = body.get("envelope")
        if (
            not isinstance(envelope, str)
            or not 1 <= len(envelope.encode("utf-8")) <= 65_536
        ):
            raise VSDReviewedRuntimeError("SOAP envelope must contain 1-65536 bytes")
        if re.search(r"<!DOCTYPE|<!ENTITY", envelope, re.IGNORECASE):
            raise VSDReviewedRuntimeError(
                "SOAP envelope cannot contain DTDs or entities"
            )
        placeholders = set(re.findall(r"\{([A-Za-z][A-Za-z0-9_]{0,63})\}", envelope))
        if placeholders != set(body_arguments):
            raise VSDReviewedRuntimeError(
                "SOAP placeholders must exactly match body arguments"
            )
        try:
            etree.fromstring(
                re.sub(r"\{[A-Za-z][A-Za-z0-9_]{0,63}\}", "value", envelope).encode(),
                parser=etree.XMLParser(
                    resolve_entities=False, no_network=True, load_dtd=False
                ),
            )
        except etree.XMLSyntaxError as exc:
            raise VSDReviewedRuntimeError(
                "SOAP envelope is not well-formed XML"
            ) from exc
        normalized_body["envelope"] = envelope
    files = body.get("files", {})
    if mode == "multipart":
        if not isinstance(files, dict) or len(files) > 4:
            raise VSDReviewedRuntimeError(
                "multipart files must contain at most four entries"
            )
        normalized_files: dict[str, Any] = {}
        for argument, definition in files.items():
            if argument not in properties or not isinstance(definition, dict):
                raise VSDReviewedRuntimeError("multipart file definition is invalid")
            if set(definition) != {"field", "filename", "content_type"}:
                raise VSDReviewedRuntimeError("multipart file fields are invalid")
            field_name = definition["field"]
            filename = definition["filename"]
            content_type = definition["content_type"]
            if (
                not isinstance(field_name, str)
                or not _PROVIDER_NAME_RE.fullmatch(field_name)
                or not isinstance(filename, str)
                or not re.fullmatch(r"[A-Za-z0-9_.-]{1,128}", filename)
                or not isinstance(content_type, str)
                or not re.fullmatch(r"[a-z0-9.+-]+/[a-z0-9.+-]+", content_type)
            ):
                raise VSDReviewedRuntimeError("multipart file metadata is invalid")
            normalized_files[argument] = copy.deepcopy(definition)
        normalized_body["files"] = normalized_files
    mapped = (
        set(path_arguments)
        | set(query_arguments)
        | set(body_arguments)
        | set(normalized_body.get("files", {}))
    )
    if set(properties) != mapped:
        raise VSDReviewedRuntimeError(
            f"Every input must map exactly once; unmapped: {sorted(set(properties) - mapped)!r}"
        )
    if sum(
        len(group)
        for group in (
            path_arguments,
            query_arguments,
            body_arguments,
            normalized_body.get("files", {}),
        )
    ) != len(mapped):
        raise VSDReviewedRuntimeError(
            "An input cannot map to multiple request locations"
        )
    if protocol == "graphql" and mode != "graphql":
        raise VSDReviewedRuntimeError("GraphQL protocol requires a GraphQL body")
    if protocol == "soap" and mode != "soap":
        raise VSDReviewedRuntimeError("SOAP protocol requires a SOAP body")
    return {
        "method": method,
        "reviewed_read_only": value.get("reviewed_read_only") is True,
        "path_arguments": path_arguments,
        "query_arguments": query_arguments,
        "fixed_query": _validated_params(value.get("fixed_query", {})),
        "fixed_headers": _validated_fixed_headers(value.get("fixed_headers")),
        "body": normalized_body,
    }


def _validated_operation_config(config: Any) -> dict[str, Any]:
    if not isinstance(config, dict):
        raise VSDReviewedRuntimeError("Tool configuration must be an object")
    normalized = copy.deepcopy(config)
    if normalized.get("type") != "VSDReviewedOperationTool":
        raise VSDReviewedRuntimeError("Tool type must be VSDReviewedOperationTool")
    name = normalized.get("name")
    if not isinstance(name, str) or not _TOOL_NAME_RE.fullmatch(name):
        raise VSDReviewedRuntimeError("Tool name must be a stable identifier")
    description = normalized.get("description")
    if (
        not isinstance(description, str)
        or not description.strip()
        or len(description) > 2000
    ):
        raise VSDReviewedRuntimeError("Tool description must contain 1-2000 characters")
    parameter = normalized.get("parameter")
    validator = _schema_validator(parameter, field="parameter")
    del validator
    if (
        parameter.get("type") != "object"
        or parameter.get("additionalProperties") is not False
    ):
        raise VSDReviewedRuntimeError("parameter must be a closed object schema")
    properties = parameter.get("properties")
    if not isinstance(properties, dict) or len(properties) > 64:
        raise VSDReviewedRuntimeError("parameter.properties is invalid")
    operation = normalized.get("vsd_reviewed_operation")
    if not isinstance(operation, dict) or operation.get("version") != 1:
        raise VSDReviewedRuntimeError("vsd_reviewed_operation.version must be 1")
    transport = operation.get("transport")
    protocol = operation.get("protocol")
    if transport not in {"http", "grpc", "mcp", "event"}:
        raise VSDReviewedRuntimeError("Reviewed transport is unsupported")
    if protocol not in {
        "rest",
        "graphql",
        "soap",
        "grpc",
        "mcp",
        "asyncapi",
        "webhook",
    }:
        raise VSDReviewedRuntimeError("Reviewed protocol is unsupported")
    compatible = {
        "http": {"rest", "graphql", "soap"},
        "grpc": {"grpc"},
        "mcp": {"mcp"},
        "event": {"asyncapi", "webhook"},
    }
    if protocol not in compatible[transport]:
        raise VSDReviewedRuntimeError("Transport and protocol are incompatible")
    timeout = operation.get("timeout_seconds", 20)
    if (
        isinstance(timeout, bool)
        or not isinstance(timeout, (int, float))
        or not math.isfinite(timeout)
        or not 1 <= timeout <= 60
    ):
        raise VSDReviewedRuntimeError("timeout_seconds must be between 1 and 60")
    normalized_operation: dict[str, Any] = {
        "version": 1,
        "transport": transport,
        "protocol": protocol,
        "timeout_seconds": timeout,
        "auth": _validated_extended_auth(operation.get("auth", {"type": "none"})),
        "response": _validated_response(
            operation.get("response", {"format": "json", "schema": {}})
        ),
    }
    if transport == "http":
        normalized_operation["endpoint"] = _validated_endpoint(
            operation.get("endpoint")
        )
        normalized_operation["request"] = _validated_http_request(
            operation.get("request"), properties, protocol
        )
        parsed_endpoint = urlsplit(normalized_operation["endpoint"])
        if parsed_endpoint.query:
            raise VSDReviewedRuntimeError(
                "Reviewed endpoint cannot contain a query; use fixed_query"
            )
        path_tokens = set(
            re.findall(r"\{([A-Za-z][A-Za-z0-9_]{0,63})\}", parsed_endpoint.path)
        )
        mapped_tokens = set(normalized_operation["request"]["path_arguments"].values())
        if path_tokens != mapped_tokens:
            raise VSDReviewedRuntimeError(
                "Endpoint path placeholders must exactly match path_arguments"
            )
        fixed_names = set(normalized_operation["request"]["fixed_query"])
        argument_names = set(
            normalized_operation["request"]["query_arguments"].values()
        )
        if fixed_names & argument_names:
            raise VSDReviewedRuntimeError(
                "Fixed and argument query parameters cannot overlap"
            )
        normalized_operation["pagination"] = _validated_pagination(
            operation.get("pagination"), properties
        )
    elif transport == "grpc":
        endpoint = operation.get("endpoint")
        if not isinstance(endpoint, str) or not re.fullmatch(
            r"[A-Za-z0-9.-]+:\d{2,5}", endpoint
        ):
            raise VSDReviewedRuntimeError("gRPC endpoint must be a host:port authority")
        host, port_text = endpoint.rsplit(":", 1)
        if int(port_text) != 443 or host.startswith(".") or host.endswith("."):
            raise VSDReviewedRuntimeError(
                "gRPC endpoints must use a hostname on port 443"
            )
        method = operation.get("method")
        if not isinstance(method, str) or not re.fullmatch(
            r"/[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*/[A-Za-z_]\w*", method
        ):
            raise VSDReviewedRuntimeError("gRPC method path is invalid")
        descriptor = operation.get("descriptor_set_base64")
        if not isinstance(descriptor, str) or not 1 <= len(descriptor) <= 350_000:
            raise VSDReviewedRuntimeError("gRPC descriptor_set_base64 is invalid")
        try:
            descriptor_bytes = base64.b64decode(descriptor, validate=True)
        except ValueError as exc:
            raise VSDReviewedRuntimeError(
                "gRPC descriptor set is not valid base64"
            ) from exc
        if len(descriptor_bytes) > 256_000:
            raise VSDReviewedRuntimeError("gRPC descriptor set exceeds 256 KB")
        streaming = operation.get("streaming", "unary")
        if streaming not in {"unary", "server"}:
            raise VSDReviewedRuntimeError(
                "gRPC runtime supports unary and bounded server streams"
            )
        max_messages = operation.get("max_messages", 100)
        if (
            isinstance(max_messages, bool)
            or not isinstance(max_messages, int)
            or not 1 <= max_messages <= 500
        ):
            raise VSDReviewedRuntimeError("gRPC max_messages must be between 1 and 500")
        normalized_operation.update(
            {
                "endpoint": endpoint,
                "method": method,
                "descriptor_set_base64": descriptor,
                "request_type": str(operation.get("request_type") or ""),
                "response_type": str(operation.get("response_type") or ""),
                "streaming": streaming,
                "max_messages": max_messages,
            }
        )
        if set(properties) != {"request"}:
            raise VSDReviewedRuntimeError(
                "gRPC tools expose exactly one request argument"
            )
        if normalized_operation["auth"]["type"] != "none":
            raise VSDReviewedRuntimeError("gRPC authentication is not yet supported")
        if normalized_operation["response"]["format"] != "json":
            raise VSDReviewedRuntimeError("gRPC responses must use JSON normalization")
    elif transport == "mcp":
        normalized_operation["endpoint"] = _validated_endpoint(
            operation.get("endpoint")
        )
        if urlsplit(normalized_operation["endpoint"]).query:
            raise VSDReviewedRuntimeError("MCP endpoint cannot contain a query")
        tool_name = operation.get("tool_name")
        if not isinstance(tool_name, str) or not re.fullmatch(
            r"[A-Za-z0-9_.:-]{1,128}", tool_name
        ):
            raise VSDReviewedRuntimeError("MCP tool_name is invalid")
        if set(properties) != {"arguments"}:
            raise VSDReviewedRuntimeError(
                "MCP tools expose exactly one arguments object"
            )
        normalized_operation["tool_name"] = tool_name
        if normalized_operation["auth"]["type"] != "none":
            raise VSDReviewedRuntimeError("MCP authentication is not yet supported")
        if normalized_operation["response"]["format"] != "json":
            raise VSDReviewedRuntimeError("MCP responses must use JSON normalization")
    else:
        event_argument = operation.get("event_argument", "event")
        signature_argument = operation.get("signature_argument")
        if event_argument not in properties or not _ARGUMENT_RE.fullmatch(
            str(event_argument)
        ):
            raise VSDReviewedRuntimeError("event_argument is invalid")
        allowed = {event_argument}
        if signature_argument is not None:
            if signature_argument not in properties or not _ARGUMENT_RE.fullmatch(
                str(signature_argument)
            ):
                raise VSDReviewedRuntimeError("signature_argument is invalid")
            allowed.add(signature_argument)
            if normalized_operation["auth"].get("type") != "api_key_header_env":
                raise VSDReviewedRuntimeError(
                    "Signed events require an environment-backed HMAC secret"
                )
        if set(properties) != allowed:
            raise VSDReviewedRuntimeError(
                "Event inputs must match the reviewed event contract"
            )
        normalized_operation.update(
            {
                "channel": str(operation.get("channel") or "")[:500],
                "event_argument": event_argument,
                "signature_argument": signature_argument,
                "event_schema": copy.deepcopy(operation.get("event_schema", {})),
            }
        )
        _schema_validator(normalized_operation["event_schema"], field="event_schema")
        if (
            signature_argument is None
            and normalized_operation["auth"]["type"] != "none"
        ):
            raise VSDReviewedRuntimeError(
                "Unsigned event validation cannot configure credentials"
            )
        if normalized_operation["response"]["format"] != "json":
            raise VSDReviewedRuntimeError("Event responses must use JSON normalization")
    operation.clear()
    operation.update(normalized_operation)
    return normalized


def operation_digest(config: dict[str, Any]) -> str:
    normalized = _validated_operation_config(config)
    return hashlib.sha256(_canonical(normalized)).hexdigest()


def _secret(env_name: str) -> str:
    value = os.environ.get(env_name)
    if (
        value is None
        or not 8 <= len(value) <= 4096
        or value != value.strip()
        or any(ord(character) < 32 or ord(character) > 126 for character in value)
    ):
        raise VSDReviewedRuntimeError(
            f"Credential environment variable {env_name!r} is missing or invalid"
        )
    return value


def _http_exchange(
    *,
    method: str,
    url: str,
    params: dict[str, Any],
    headers: dict[str, str],
    body: bytes | None,
    timeout: float,
    max_bytes: int,
) -> tuple[bytes, dict[str, Any]]:
    """Perform one DNS-pinned HTTPS request and return bounded raw bytes."""
    deadline = time.monotonic() + timeout
    normalized_url, hostname, addresses = _validated_source_target(url)
    pinned_address = addresses[0]
    query = _validated_params(params)
    session = requests.Session()
    session.trust_env = False
    session.mount("https://", _PinnedHTTPSAdapter(hostname, pinned_address))
    try:
        remaining = deadline - time.monotonic()
        response = session.request(
            method,
            normalized_url,
            params=query or None,
            headers={"Accept-Encoding": "identity", **headers},
            data=body,
            timeout=Urllib3Timeout(
                total=remaining, connect=min(5.0, remaining), read=remaining
            ),
            allow_redirects=False,
            stream=True,
        )
        try:
            peer_ip = _peer_address(response)
            _require_global_ip(peer_ip, context="Connected peer")
            if ipaddress.ip_address(peer_ip) != ipaddress.ip_address(pinned_address):
                raise VSDReviewedRuntimeError("Connected peer did not match vetted DNS")
            if response.status_code in {301, 302, 303, 307, 308}:
                location = response.headers.get("Location")
                if location:
                    _validated_source_target(urljoin(normalized_url, location))
                raise VSDReviewedRuntimeError("Provider redirects are not allowed")
            response.raise_for_status()
            encodings = {
                item.strip().casefold()
                for item in response.headers.get("Content-Encoding", "").split(",")
                if item.strip()
            }
            if encodings - {"identity"}:
                raise VSDReviewedRuntimeError(
                    "Compressed provider responses are not allowed"
                )
            declared = response.headers.get("Content-Length")
            if declared is not None and (
                not declared.isdigit() or int(declared) > max_bytes
            ):
                raise VSDReviewedRuntimeError(
                    "Provider Content-Length is invalid or excessive"
                )
            chunks: list[bytes] = []
            total = 0
            for chunk in _response_chunks(response, deadline=deadline):
                total += len(chunk)
                if total > max_bytes:
                    raise VSDReviewedRuntimeError(
                        "Provider response exceeds the reviewed byte limit"
                    )
                chunks.append(chunk)
            return b"".join(chunks), {
                "url": normalized_url,
                "status_code": response.status_code,
                "content_type": response.headers.get("Content-Type", "").casefold(),
                "response_bytes": total,
                "headers": {
                    str(key).casefold(): str(value)
                    for key, value in response.headers.items()
                },
                "peer_ip": peer_ip,
                "redirects": 0,
            }
        finally:
            response.close()
    except requests.Timeout as exc:
        raise VSDReviewedRuntimeError("Provider request exceeded its timeout") from exc
    except requests.RequestException as exc:
        raise VSDReviewedRuntimeError("Provider request failed") from exc
    finally:
        session.close()


def _oauth_headers(
    auth: dict[str, Any], timeout: float
) -> tuple[dict[str, str], list[str]]:
    if auth["type"] != "oauth2_client_credentials_env":
        headers, secret = _credential_headers(auth)
        return headers, [secret] if secret else []
    client_id = _secret(auth["client_id_env"])
    client_secret = _secret(auth["client_secret_env"])
    form: dict[str, str] = {"grant_type": "client_credentials"}
    if auth.get("scope"):
        form["scope"] = auth["scope"]
    if auth.get("audience"):
        form["audience"] = auth["audience"]
    basic = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    raw, metadata = _http_exchange(
        method="POST",
        url=auth["token_url"],
        params={},
        headers={
            "Accept": "application/json",
            "Authorization": f"Basic {basic}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        body=urlencode(form).encode(),
        timeout=timeout,
        max_bytes=65_536,
    )
    if metadata["status_code"] != 200:
        raise VSDReviewedRuntimeError("OAuth token endpoint did not return 200")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise VSDReviewedRuntimeError("OAuth token response is not JSON") from exc
    token = payload.get("access_token") if isinstance(payload, dict) else None
    token_type = (
        str(payload.get("token_type") or "Bearer") if isinstance(payload, dict) else ""
    )
    if (
        not isinstance(token, str)
        or not 8 <= len(token) <= 4096
        or token_type.casefold() != "bearer"
    ):
        raise VSDReviewedRuntimeError(
            "OAuth token response does not contain a bounded bearer token"
        )
    return {"Authorization": f"Bearer {token}"}, [client_id, client_secret, token]


def _request_parts(
    request: dict[str, Any], arguments: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, str], bytes | None]:
    query = copy.deepcopy(request["fixed_query"])
    for argument, provider in request["query_arguments"].items():
        query[provider] = arguments[argument]
    headers = copy.deepcopy(request["fixed_headers"])
    body_config = request["body"]
    mode = body_config["mode"]
    values = copy.deepcopy(body_config["fixed"])
    for argument, provider in body_config["arguments"].items():
        values[provider] = arguments[argument]
    body: bytes | None = None
    if mode == "json":
        body = _canonical(values)
        headers["Content-Type"] = "application/json"
    elif mode == "form":
        body = urlencode(values, doseq=True).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    elif mode == "graphql":
        body = _canonical(
            {
                "query": body_config["query"],
                "variables": values,
                **(
                    {"operationName": body_config["operation_name"]}
                    if body_config.get("operation_name")
                    else {}
                ),
            }
        )
        headers["Content-Type"] = "application/json"
    elif mode == "soap":
        envelope = body_config["envelope"]
        for argument in body_config["arguments"]:
            envelope = envelope.replace(
                "{" + argument + "}", escape(str(arguments[argument]))
            )
        body = envelope.encode("utf-8")
        headers.setdefault("Content-Type", "text/xml; charset=utf-8")
    elif mode == "multipart":
        boundary = (
            "tooluniverse-vsd-" + hashlib.sha256(_canonical(arguments)).hexdigest()[:24]
        )
        chunks: list[bytes] = []
        for field, value in sorted(values.items()):
            chunks.extend(
                [
                    f"--{boundary}\r\n".encode(),
                    f'Content-Disposition: form-data; name="{field}"\r\n\r\n'.encode(),
                    str(value).encode("utf-8"),
                    b"\r\n",
                ]
            )
        for argument, definition in sorted(body_config.get("files", {}).items()):
            encoded = arguments[argument]
            if not isinstance(encoded, str):
                raise VSDReviewedRuntimeError(
                    "Multipart file arguments must be base64 strings"
                )
            try:
                content = base64.b64decode(encoded, validate=True)
            except ValueError as exc:
                raise VSDReviewedRuntimeError(
                    "Multipart file argument is not valid base64"
                ) from exc
            if len(content) > 256_000:
                raise VSDReviewedRuntimeError("Multipart file exceeds 256 KB")
            chunks.extend(
                [
                    f"--{boundary}\r\n".encode(),
                    (
                        f'Content-Disposition: form-data; name="{definition["field"]}"; '
                        f'filename="{definition["filename"]}"\r\n'
                    ).encode(),
                    f"Content-Type: {definition['content_type']}\r\n\r\n".encode(),
                    content,
                    b"\r\n",
                ]
            )
        chunks.append(f"--{boundary}--\r\n".encode())
        body = b"".join(chunks)
        headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
    if body is not None and len(body) > _MAX_REQUEST_BYTES:
        raise VSDReviewedRuntimeError("Reviewed request body exceeds 512 KB")
    return _validated_params(query), headers, body


def _decode_text(raw: bytes, *, label: str) -> str:
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise VSDReviewedRuntimeError(f"{label} response is not UTF-8") from exc


def _xml_value(element: etree._Element) -> Any:
    children = list(element)
    if not children:
        return (element.text or "").strip()
    result: dict[str, Any] = {}
    for child in children:
        name = etree.QName(child).localname
        value = _xml_value(child)
        if name in result:
            if not isinstance(result[name], list):
                result[name] = [result[name]]
            result[name].append(value)
        else:
            result[name] = value
    return result


def _parse_sse(text: str, max_events: int) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    current: dict[str, Any] = {"data": []}
    for line in text.splitlines() + [""]:
        if not line:
            if current["data"]:
                joined = "\n".join(current["data"])
                try:
                    data: Any = json.loads(joined)
                except json.JSONDecodeError:
                    data = joined
                events.append(
                    {
                        **{
                            key: value
                            for key, value in current.items()
                            if key != "data"
                        },
                        "data": data,
                    }
                )
                if len(events) > max_events:
                    raise VSDReviewedRuntimeError("SSE response exceeds max_events")
            current = {"data": []}
            continue
        if line.startswith(":"):
            continue
        field, _, value = line.partition(":")
        value = value[1:] if value.startswith(" ") else value
        if field == "data":
            current["data"].append(value)
        elif field in {"event", "id", "retry"}:
            current[field] = value
    return events


def _parse_response(
    raw: bytes, metadata: dict[str, Any], config: dict[str, Any]
) -> Any:
    response_format = config["format"]
    content_type = metadata.get("content_type", "").split(";", 1)[0]
    expected_types = {
        "json": lambda item: item == "application/json" or item.endswith("+json"),
        "csv": lambda item: item
        in {"text/csv", "text/tab-separated-values", "application/csv"},
        "xml": lambda item: item
        in {"application/xml", "text/xml", "application/soap+xml"}
        or item.endswith("+xml"),
        "html": lambda item: item in {"text/html", "application/xhtml+xml"},
        "binary": lambda item: bool(item),
        "sse": lambda item: item == "text/event-stream",
    }
    if not expected_types[response_format](content_type):
        raise VSDReviewedRuntimeError(
            f"Provider content type {content_type!r} does not match {response_format}"
        )
    if response_format == "json":
        try:
            value = json.loads(
                _decode_text(raw, label="JSON"),
                parse_constant=lambda item: (_ for _ in ()).throw(ValueError(item)),
            )
        except (json.JSONDecodeError, ValueError) as exc:
            raise VSDReviewedRuntimeError(
                "Provider response is not strict JSON"
            ) from exc
    elif response_format == "csv":
        reader = csv.DictReader(
            io.StringIO(_decode_text(raw, label="CSV")), delimiter=config["delimiter"]
        )
        if (
            not reader.fieldnames
            or len(reader.fieldnames) > 200
            or len(set(reader.fieldnames)) != len(reader.fieldnames)
        ):
            raise VSDReviewedRuntimeError(
                "CSV response has invalid or duplicate headers"
            )
        value = []
        for row in reader:
            if len(value) >= _MAX_ITEMS:
                raise VSDReviewedRuntimeError("CSV response exceeds 1000 rows")
            value.append(dict(row))
    elif response_format == "xml":
        if re.search(rb"<!DOCTYPE|<!ENTITY", raw, re.IGNORECASE):
            raise VSDReviewedRuntimeError("XML response contains a DTD or entity")
        try:
            root = etree.fromstring(
                raw,
                parser=etree.XMLParser(
                    resolve_entities=False,
                    no_network=True,
                    load_dtd=False,
                    huge_tree=False,
                ),
            )
        except etree.XMLSyntaxError as exc:
            raise VSDReviewedRuntimeError("Provider response is not safe XML") from exc
        value = {etree.QName(root).localname: _xml_value(root)}
    elif response_format == "html":
        soup = BeautifulSoup(_decode_text(raw, label="HTML"), "html.parser")
        for item in soup(["script", "style", "noscript", "iframe", "object", "embed"]):
            item.decompose()
        tables = []
        for table in soup.find_all("table")[:20]:
            rows = [
                [
                    cell.get_text(" ", strip=True)[:2000]
                    for cell in row.find_all(["th", "td"])[:100]
                ]
                for row in table.find_all("tr")[:500]
            ]
            tables.append(rows)
        value = {
            "title": soup.title.get_text(" ", strip=True)[:500] if soup.title else "",
            "text": soup.get_text(" ", strip=True)[:100_000],
            "tables": tables,
            "links": [
                {
                    "text": link.get_text(" ", strip=True)[:500],
                    "href": str(link.get("href"))[:2000],
                }
                for link in soup.find_all("a", href=True)[:200]
            ],
        }
    elif response_format == "binary":
        value = {
            "content_base64": base64.b64encode(raw).decode("ascii"),
            "content_type": metadata.get("content_type", ""),
            "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
        }
    else:
        value = _parse_sse(_decode_text(raw, label="SSE"), config["max_events"])
    selected = _pointer(value, config["root_pointer"])
    if config["root_pointer"] and selected is None:
        raise VSDReviewedRuntimeError("Reviewed response root_pointer was not present")
    return selected


def _next_link(header: str, current_host: str) -> str | None:
    for item in header.split(","):
        match = re.match(r'\s*<([^>]+)>\s*;\s*rel="?([^";]+)"?', item)
        if match and match.group(2).casefold() == "next":
            target = _validated_endpoint(match.group(1), field="pagination next link")
            if urlsplit(target).hostname != current_host:
                raise VSDReviewedRuntimeError(
                    "Pagination next link changed provider host"
                )
            return target
    return None


def _http_run(
    operation: dict[str, Any], arguments: dict[str, Any]
) -> tuple[Any, dict[str, Any], list[str]]:
    request = operation["request"]
    endpoint = operation["endpoint"]
    for argument, placeholder in request["path_arguments"].items():
        value = arguments[argument]
        if isinstance(value, (dict, list)) or value is None:
            raise VSDReviewedRuntimeError("Path arguments must be non-null scalars")
        endpoint = endpoint.replace("{" + placeholder + "}", quote(str(value), safe=""))
    params, headers, body = _request_parts(request, arguments)
    auth_headers, secrets = _oauth_headers(
        operation["auth"], float(operation["timeout_seconds"])
    )
    headers.update(auth_headers)
    response = operation["response"]
    accept = {
        "json": "application/json",
        "csv": "text/csv",
        "xml": "application/xml, text/xml, application/soap+xml",
        "html": "text/html",
        "binary": "application/octet-stream",
        "sse": "text/event-stream",
    }[response["format"]]
    headers.setdefault("Accept", accept)
    pagination = operation["pagination"]
    results: list[Any] = []
    page_metadata: list[dict[str, Any]] = []
    next_url: str | None = endpoint
    cursor: Any = None
    for page_index in range(pagination["max_pages"]):
        current_params = copy.deepcopy(params)
        if pagination["type"] in {"page", "offset"}:
            current_params[pagination["parameter"]] = (
                pagination["start"] + page_index * pagination["step"]
            )
        elif pagination["type"] == "cursor" and cursor is not None:
            current_params[pagination["parameter"]] = cursor
        page_url = next_url or endpoint
        parsed_page_url = urlsplit(page_url)
        if parsed_page_url.query:
            link_pairs = parse_qsl(
                parsed_page_url.query,
                keep_blank_values=True,
                strict_parsing=True,
                max_num_fields=50,
            )
            if len({name for name, _ in link_pairs}) != len(link_pairs):
                raise VSDReviewedRuntimeError(
                    "Pagination next link contains duplicate query parameters"
                )
            current_params.update(dict(link_pairs))
            page_url = urlunsplit(
                (
                    parsed_page_url.scheme,
                    parsed_page_url.netloc,
                    parsed_page_url.path,
                    "",
                    "",
                )
            )
        raw, metadata = _http_exchange(
            method=request["method"],
            url=page_url,
            params=current_params,
            headers=headers,
            body=body,
            timeout=float(operation["timeout_seconds"]),
            max_bytes=response["max_bytes"],
        )
        parsed = _parse_response(raw, metadata, response)
        if any(_contains_secret(parsed, secret) for secret in secrets):
            raise VSDReviewedRuntimeError(
                "Provider response reflected credential material"
            )
        page_metadata.append(metadata)
        if pagination["type"] == "none":
            return parsed, {"pages": page_metadata}, secrets
        page_items = _pointer(parsed, pagination["items_pointer"])
        if not isinstance(page_items, list):
            raise VSDReviewedRuntimeError(
                "Paginated response items_pointer is not an array"
            )
        results.extend(page_items)
        if len(results) > pagination["max_items"]:
            results = results[: pagination["max_items"]]
            break
        if pagination["type"] == "cursor":
            cursor = _pointer(parsed, pagination["next_pointer"])
            if cursor in (None, ""):
                break
        elif pagination["type"] == "link_header":
            next_url = _next_link(
                metadata["headers"].get("link", ""), urlsplit(endpoint).hostname or ""
            )
            if next_url is None:
                break
        elif not page_items:
            break
    return results, {"pages": page_metadata}, secrets


def _grpc_classes(operation: dict[str, Any]):
    try:
        from google.protobuf import descriptor_pb2, descriptor_pool, message_factory
    except ImportError as exc:
        raise VSDReviewedRuntimeError("protobuf runtime is not installed") from exc
    descriptor_set = descriptor_pb2.FileDescriptorSet()
    descriptor_set.ParseFromString(base64.b64decode(operation["descriptor_set_base64"]))
    pool = descriptor_pool.DescriptorPool()
    remaining = list(descriptor_set.file)
    while remaining:
        pending = []
        progressed = False
        for descriptor in remaining:
            try:
                pool.Add(descriptor)
                progressed = True
            except Exception:
                pending.append(descriptor)
        if not progressed:
            raise VSDReviewedRuntimeError(
                "gRPC descriptor dependencies cannot be resolved"
            )
        remaining = pending
    try:
        request_descriptor = pool.FindMessageTypeByName(operation["request_type"])
        response_descriptor = pool.FindMessageTypeByName(operation["response_type"])
    except KeyError as exc:
        raise VSDReviewedRuntimeError(
            "gRPC request or response type is absent from descriptors"
        ) from exc
    return message_factory.GetMessageClass(
        request_descriptor
    ), message_factory.GetMessageClass(response_descriptor)


def _grpc_exchange(
    operation: dict[str, Any], request_value: dict[str, Any]
) -> tuple[Any, dict[str, Any]]:
    try:
        import grpc
        from google.protobuf.json_format import MessageToDict, ParseDict
    except ImportError as exc:
        raise VSDReviewedRuntimeError(
            "grpcio and protobuf are required for gRPC execution"
        ) from exc
    request_class, response_class = _grpc_classes(operation)
    request_message = ParseDict(
        request_value, request_class(), ignore_unknown_fields=False
    )
    host, port_text = operation["endpoint"].rsplit(":", 1)
    port = int(port_text)
    from .vsd_tool import _normalize_host, _resolve_public_addresses

    normalized_host = _normalize_host(host)
    address = _resolve_public_addresses(normalized_host, port)[0]
    authority = f"{normalized_host}:{port}"
    channel = grpc.secure_channel(
        f"{address}:{port}",
        grpc.ssl_channel_credentials(),
        options=[
            ("grpc.ssl_target_name_override", normalized_host),
            ("grpc.default_authority", authority),
            ("grpc.max_receive_message_length", _MAX_RESPONSE_BYTES),
            ("grpc.max_send_message_length", _MAX_REQUEST_BYTES),
        ],
    )

    def serializer(item):
        return item.SerializeToString()

    deserializer = response_class.FromString
    started = time.monotonic()
    try:
        if operation["streaming"] == "unary":
            call = channel.unary_unary(
                operation["method"],
                request_serializer=serializer,
                response_deserializer=deserializer,
            )
            response = call(
                request_message, timeout=float(operation["timeout_seconds"])
            )
            value: Any = MessageToDict(response, preserving_proto_field_name=True)
            count = 1
        else:
            call = channel.unary_stream(
                operation["method"],
                request_serializer=serializer,
                response_deserializer=deserializer,
            )
            values = []
            for response in call(
                request_message, timeout=float(operation["timeout_seconds"])
            ):
                values.append(MessageToDict(response, preserving_proto_field_name=True))
                if len(values) >= operation["max_messages"]:
                    break
            value = values
            count = len(values)
    finally:
        channel.close()
    return value, {
        "messages": count,
        "elapsed_seconds": time.monotonic() - started,
        "peer": authority,
    }


def _mcp_exchange(
    operation: dict[str, Any], arguments: dict[str, Any]
) -> tuple[Any, dict[str, Any]]:
    from .mcp_client_tool import BaseMCPClient

    _validated_source_target(operation["endpoint"])

    client = BaseMCPClient(
        operation["endpoint"],
        transport="http",
        timeout=int(operation["timeout_seconds"]),
    )

    async def call():
        return await client._make_mcp_request(
            "tools/call", {"name": operation["tool_name"], "arguments": arguments}
        )

    result = client._run_with_cleanup(call)
    return result, {"tool_name": operation["tool_name"]}


def _event_run(
    operation: dict[str, Any], arguments: dict[str, Any]
) -> tuple[Any, dict[str, Any], list[str]]:
    event = arguments[operation["event_argument"]]
    validator = _schema_validator(operation["event_schema"], field="event_schema")
    try:
        validator.validate(event)
    except ValidationError as exc:
        raise VSDReviewedRuntimeError(
            f"Event failed the reviewed schema: {exc.message}"
        ) from exc
    secrets: list[str] = []
    signature_argument = operation.get("signature_argument")
    if signature_argument:
        secret = _secret(operation["auth"]["env_var"])
        expected = (
            "sha256="
            + hmac.new(secret.encode(), _canonical(event), hashlib.sha256).hexdigest()
        )
        supplied = arguments[signature_argument]
        if not isinstance(supplied, str) or not hmac.compare_digest(expected, supplied):
            raise VSDReviewedRuntimeError(
                "Event signature does not match canonical payload"
            )
        secrets.append(secret)
    return (
        copy.deepcopy(event),
        {
            "channel": operation["channel"],
            "signature_verified": bool(signature_argument),
        },
        secrets,
    )


@register_tool("VSDReviewedOperationTool")
class VSDReviewedOperationTool(BaseTool):
    """Execute one exact reviewed HTTP, gRPC, MCP, or event contract."""

    def __init__(self, tool_config):
        super().__init__(_validated_operation_config(tool_config))
        self._input_validator: Draft202012Validator = _schema_validator(
            self.tool_config["parameter"], field="parameter"
        )
        operation = self.tool_config["vsd_reviewed_operation"]
        self._response_validator = _schema_validator(
            operation["response"]["schema"], field="response.schema"
        )
        self._operation_digest = operation_digest(self.tool_config)

    def run(self, arguments=None, **_: Any):
        values = {} if arguments is None else arguments
        if not isinstance(values, dict):
            raise VSDReviewedRuntimeError("Tool arguments must be an object")
        try:
            self._input_validator.validate(values)
        except ValidationError as exc:
            raise VSDReviewedRuntimeError(
                f"Tool arguments failed the reviewed schema: {exc.message}"
            ) from exc
        operation = self.tool_config["vsd_reviewed_operation"]
        transport = operation["transport"]
        if transport == "http":
            result, request_metadata, secrets = _http_run(operation, values)
            endpoint = operation["endpoint"]
            method = operation["request"]["method"]
        elif transport == "grpc":
            result, request_metadata = _grpc_exchange(operation, values["request"])
            secrets = []
            endpoint = operation["endpoint"]
            method = operation["method"]
        elif transport == "mcp":
            result, request_metadata = _mcp_exchange(operation, values["arguments"])
            secrets = []
            endpoint = operation["endpoint"]
            method = "tools/call"
        else:
            result, request_metadata, secrets = _event_run(operation, values)
            endpoint = operation["channel"]
            method = "validate"
        if any(_contains_secret(result, secret) for secret in secrets):
            raise VSDReviewedRuntimeError("Runtime result contains credential material")
        try:
            self._response_validator.validate(result)
        except ValidationError as exc:
            raise VSDReviewedRuntimeError(
                f"Runtime result failed the reviewed schema: {exc.message}"
            ) from exc
        canonical = _canonical(result)
        pages = request_metadata.get("pages", [])
        last_page = pages[-1] if pages else {}
        return {
            "status": "success",
            "data": {
                "result": result,
                "provenance": {
                    "provider": urlsplit(endpoint).hostname
                    or endpoint.split(":", 1)[0],
                    "endpoint": endpoint,
                    "method": method,
                    "transport": transport,
                    "protocol": operation["protocol"],
                    "retrieved_at": datetime.now(timezone.utc).isoformat(),
                    "http_status": last_page.get("status_code", 200),
                    "content_type": last_page.get("content_type", "application/json"),
                    "response_bytes": sum(
                        page.get("response_bytes", 0) for page in pages
                    )
                    if pages
                    else len(canonical),
                    "redirects": sum(page.get("redirects", 0) for page in pages),
                    "page_count": len(pages) if pages else 1,
                    "payload_sha256": hashlib.sha256(canonical).hexdigest(),
                    "operation_sha256": self._operation_digest,
                    "authentication": {
                        "type": operation["auth"]["type"],
                        "credential_source": "none"
                        if operation["auth"]["type"] == "none"
                        else "environment",
                    },
                    "runtime": request_metadata,
                },
            },
        }


def register_reviewed_operation_tool(tooluniverse, config: dict[str, Any]) -> str:
    normalized = _validated_operation_config(config)
    instance = VSDReviewedOperationTool(normalized)
    return tooluniverse.register_custom_tool(
        tool_class=VSDReviewedOperationTool,
        tool_name=normalized["name"],
        tool_config=normalized,
        tool_instance=instance,
    )


__all__ = [
    "VSDReviewedOperationTool",
    "VSDReviewedRuntimeError",
    "operation_digest",
    "register_reviewed_operation_tool",
]
