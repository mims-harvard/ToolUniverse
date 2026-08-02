"""Validated runtime execution for explicitly reviewed public JSON operations.

This module intentionally does not discover, persist, approve, or automatically
load tools. It provides the execution boundary used after an administrator has
reviewed an operation definition. Only HTTPS GET operations are supported.
Optional header credentials are read from narrowly named environment variables
at execution time and are never embedded in the operation contract or result.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote, urlsplit

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError

from .base_tool import BaseTool
from .tool_registry import register_tool
from .vsd_tool import VSDPolicyError, _safe_get_json, _validated_params

_TOOL_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{2,127}$")
_ARGUMENT_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,63}$")
_PATH_TOKEN_RE = re.compile(r"\{([A-Za-z][A-Za-z0-9_]{0,63})\}")
_QUERY_NAME_RE = re.compile(r"^[A-Za-z0-9_.\[\]-]{1,128}$")
_HEADER_NAME_RE = re.compile(r"^[!#$%&'*+.^_`|~0-9A-Za-z-]{1,128}$")
_ENV_NAME_RE = re.compile(r"^TOOLUNIVERSE_VSD_[A-Z0-9_]{1,108}$")
_FORBIDDEN_AUTH_HEADERS = {
    "accept",
    "accept-encoding",
    "connection",
    "content-length",
    "content-type",
    "cookie",
    "host",
    "origin",
    "referer",
    "transfer-encoding",
    "user-agent",
}


class VSDDynamicRESTError(VSDPolicyError):
    """Raised when an operation or provider result violates its reviewed contract."""


def _validated_auth(value: Any) -> dict[str, str]:
    if value in (None, {"type": "none"}):
        return {"type": "none"}
    if not isinstance(value, dict):
        raise VSDDynamicRESTError("auth must be a reviewed environment reference")
    auth_type = value.get("type")
    if auth_type == "bearer_env":
        if set(value) != {"type", "env_var"}:
            raise VSDDynamicRESTError("bearer_env auth has unsupported fields")
        header = "Authorization"
    elif auth_type == "api_key_header_env":
        if set(value) != {"type", "env_var", "header"}:
            raise VSDDynamicRESTError("api_key_header_env auth has unsupported fields")
        header = value.get("header")
        if not isinstance(header, str) or not _HEADER_NAME_RE.fullmatch(header):
            raise VSDDynamicRESTError("API-key header must be a stable HTTP token")
        normalized_header = header.casefold()
        if (
            normalized_header == "authorization"
            or normalized_header in _FORBIDDEN_AUTH_HEADERS
            or normalized_header.startswith(
                ("proxy-", "sec-", "x-forwarded-", "content-")
            )
        ):
            raise VSDDynamicRESTError("API-key header is prohibited")
    else:
        raise VSDDynamicRESTError(
            "auth supports only none, bearer_env, or api_key_header_env"
        )
    env_var = value.get("env_var")
    if not isinstance(env_var, str) or not _ENV_NAME_RE.fullmatch(env_var):
        raise VSDDynamicRESTError(
            "credential env_var must start with TOOLUNIVERSE_VSD_"
        )
    return {
        "type": auth_type,
        "env_var": env_var,
        **({"header": header} if auth_type == "api_key_header_env" else {}),
    }


def _credential_headers(auth: dict[str, str]) -> tuple[dict[str, str], str | None]:
    if auth["type"] == "none":
        return {}, None
    env_var = auth["env_var"]
    secret = os.environ.get(env_var)
    if secret is None:
        raise VSDDynamicRESTError(
            f"Required credential environment variable {env_var!r} is not set"
        )
    if (
        not 8 <= len(secret) <= 4096
        or secret != secret.strip()
        or any(ord(character) < 32 or ord(character) > 126 for character in secret)
    ):
        raise VSDDynamicRESTError(
            f"Credential environment variable {env_var!r} is not a valid bounded value"
        )
    if auth["type"] == "bearer_env":
        if any(character.isspace() for character in secret):
            raise VSDDynamicRESTError(
                f"Credential environment variable {env_var!r} is not a bearer token"
            )
        return {"Authorization": f"Bearer {secret}"}, secret
    return {auth["header"]: secret}, secret


def _contains_secret(value: Any, secret: str) -> bool:
    pending = [value]
    while pending:
        item = pending.pop()
        if isinstance(item, str) and secret in item:
            return True
        if isinstance(item, dict):
            pending.extend(item.keys())
            pending.extend(item.values())
        elif isinstance(item, list):
            pending.extend(item)
    return False


def _schema_validator(schema: Any, *, field: str) -> Draft202012Validator:
    if not isinstance(schema, dict):
        raise VSDDynamicRESTError(f"{field} must be a JSON Schema object")
    try:
        encoded = json.dumps(schema, allow_nan=False, ensure_ascii=True)
    except (TypeError, ValueError) as exc:
        raise VSDDynamicRESTError(f"{field} must be finite JSON") from exc
    if len(encoded.encode("utf-8")) > 65_536:
        raise VSDDynamicRESTError(f"{field} exceeds the 64 KiB schema limit")

    pending: list[Any] = [schema]
    while pending:
        node = pending.pop()
        if isinstance(node, dict):
            reference = node.get("$ref")
            if isinstance(reference, str) and not reference.startswith("#/"):
                raise VSDDynamicRESTError(
                    f"{field} cannot resolve an external JSON Schema reference"
                )
            pending.extend(node.values())
        elif isinstance(node, list):
            pending.extend(node)
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as exc:
        raise VSDDynamicRESTError(f"{field} is not a valid JSON Schema") from exc
    return Draft202012Validator(schema)


def _validated_operation_config(config: Any) -> dict[str, Any]:
    if not isinstance(config, dict):
        raise VSDDynamicRESTError("Tool configuration must be an object")
    normalized = copy.deepcopy(config)
    name = normalized.get("name")
    if not isinstance(name, str) or not _TOOL_NAME_RE.fullmatch(name):
        raise VSDDynamicRESTError("Tool name must be a stable identifier")
    description = normalized.get("description")
    if (
        not isinstance(description, str)
        or not description.strip()
        or len(description) > 2000
    ):
        raise VSDDynamicRESTError("Tool description must contain 1-2000 characters")
    if normalized.get("type") != "VSDDynamicRESTTool":
        raise VSDDynamicRESTError("Tool type must be VSDDynamicRESTTool")

    input_schema = normalized.get("parameter")
    _schema_validator(input_schema, field="parameter")
    if input_schema.get("type") != "object":
        raise VSDDynamicRESTError("parameter must describe an object")
    if input_schema.get("additionalProperties") is not False:
        raise VSDDynamicRESTError("parameter must reject additional properties")

    operation = normalized.get("vsd_operation")
    if not isinstance(operation, dict):
        raise VSDDynamicRESTError("vsd_operation must be an object")
    if operation.get("version") != 1:
        raise VSDDynamicRESTError("vsd_operation.version must be 1")
    if operation.get("method") != "GET":
        raise VSDDynamicRESTError(
            "Dynamic VSD operations are read-only HTTPS GET calls"
        )
    endpoint = operation.get("endpoint")
    if not isinstance(endpoint, str) or not endpoint:
        raise VSDDynamicRESTError("vsd_operation.endpoint must be a non-empty string")
    parsed = urlsplit(endpoint)
    if parsed.scheme.lower() != "https" or not parsed.hostname:
        raise VSDDynamicRESTError("vsd_operation.endpoint must be an HTTPS URL")
    if parsed.query or parsed.fragment or parsed.username or parsed.password:
        raise VSDDynamicRESTError(
            "vsd_operation.endpoint cannot contain credentials, a query, or a fragment"
        )

    properties = input_schema.get("properties")
    if not isinstance(properties, dict):
        raise VSDDynamicRESTError("parameter.properties must be an object")
    path_arguments = operation.get("path_arguments", {})
    query_arguments = operation.get("query_arguments", {})
    has_query_serialization = "query_serialization" in operation
    query_serialization = operation.get("query_serialization", {})
    fixed_query = operation.get("fixed_query", {})
    if (
        not isinstance(path_arguments, dict)
        or not isinstance(query_arguments, dict)
        or not isinstance(query_serialization, dict)
    ):
        raise VSDDynamicRESTError("Argument mappings must be objects")
    for argument, target in (*path_arguments.items(), *query_arguments.items()):
        if (
            not isinstance(argument, str)
            or not _ARGUMENT_NAME_RE.fullmatch(argument)
            or argument not in properties
        ):
            raise VSDDynamicRESTError(
                f"Mapped argument {argument!r} is not declared by parameter.properties"
            )
        if not isinstance(target, str) or not _QUERY_NAME_RE.fullmatch(target):
            raise VSDDynamicRESTError(
                f"Invalid provider parameter name for {argument!r}"
            )
    overlap = set(path_arguments) & set(query_arguments)
    if overlap:
        raise VSDDynamicRESTError(
            f"Arguments cannot be both path and query values: {sorted(overlap)!r}"
        )
    tokens = _PATH_TOKEN_RE.findall(parsed.path)
    if len(tokens) != len(set(tokens)) or set(tokens) != set(path_arguments.values()):
        raise VSDDynamicRESTError(
            "Endpoint path placeholders must exactly match path_arguments targets"
        )
    mapped_arguments = set(path_arguments) | set(query_arguments)
    unmapped = set(properties) - mapped_arguments
    if unmapped:
        raise VSDDynamicRESTError(
            f"Every input must map to the request; unmapped inputs: {sorted(unmapped)!r}"
        )
    unknown_serialization = set(query_serialization) - set(query_arguments)
    if unknown_serialization:
        raise VSDDynamicRESTError(
            "Query serialization references unmapped arguments: "
            f"{sorted(unknown_serialization)!r}"
        )
    normalized_serialization: dict[str, dict[str, Any]] = {}
    for argument in query_arguments:
        rule = query_serialization.get(argument, {"style": "form", "explode": True})
        if not isinstance(rule, dict) or set(rule) - {"style", "explode"}:
            raise VSDDynamicRESTError(
                f"Query serialization for {argument!r} is invalid"
            )
        style = rule.get("style", "form")
        explode = rule.get("explode", style == "form")
        if style not in {"form", "pipeDelimited", "spaceDelimited"}:
            raise VSDDynamicRESTError(
                f"Query serialization style for {argument!r} is unsupported"
            )
        if type(explode) is not bool:
            raise VSDDynamicRESTError(
                f"Query serialization explode for {argument!r} must be boolean"
            )
        if style != "form" and explode:
            raise VSDDynamicRESTError(
                f"Query serialization style {style!r} cannot explode values"
            )
        normalized_serialization[argument] = {
            "style": style,
            "explode": explode,
        }
    if has_query_serialization:
        operation["query_serialization"] = normalized_serialization
    if not isinstance(fixed_query, dict):
        raise VSDDynamicRESTError("fixed_query must be an object")
    try:
        fixed_query = _validated_params(fixed_query)
    except VSDPolicyError as exc:
        raise VSDDynamicRESTError(str(exc)) from exc
    conflicting = set(fixed_query) & set(query_arguments.values())
    if conflicting:
        raise VSDDynamicRESTError(
            f"Fixed and argument query parameters overlap: {sorted(conflicting)!r}"
        )
    operation["fixed_query"] = fixed_query
    operation["timeout_seconds"] = operation.get("timeout_seconds", 20)
    timeout = operation["timeout_seconds"]
    if (
        isinstance(timeout, bool)
        or not isinstance(timeout, (int, float))
        or not 1 <= timeout <= 60
    ):
        raise VSDDynamicRESTError("timeout_seconds must be between 1 and 60")
    operation["response_schema"] = operation.get("response_schema", {})
    _schema_validator(operation["response_schema"], field="response_schema")
    operation["auth"] = _validated_auth(operation.get("auth"))
    return normalized


def operation_digest(config: dict[str, Any]) -> str:
    """Return the stable review digest for one normalized operation."""
    normalized = _validated_operation_config(config)
    encoded = json.dumps(
        normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _provider_request(
    config: dict[str, Any], arguments: dict[str, Any]
) -> tuple[str, dict[str, Any]]:
    operation = config["vsd_operation"]
    endpoint = operation["endpoint"]
    path_arguments = operation.get("path_arguments", {})
    for argument, placeholder in path_arguments.items():
        value = arguments[argument]
        if isinstance(value, (dict, list)) or value is None:
            raise VSDDynamicRESTError(
                f"Path argument {argument!r} must be a non-null scalar"
            )
        endpoint = endpoint.replace("{" + placeholder + "}", quote(str(value), safe=""))

    query = dict(operation.get("fixed_query", {}))
    for argument, parameter_name in operation.get("query_arguments", {}).items():
        if argument in arguments and arguments[argument] is not None:
            value = arguments[argument]
            serialization = operation.get("query_serialization", {}).get(
                argument, {"style": "form", "explode": True}
            )
            if isinstance(value, list):
                style = serialization["style"]
                if style == "pipeDelimited":
                    value = "|".join(str(item) for item in value)
                elif style == "spaceDelimited":
                    value = " ".join(str(item) for item in value)
                elif not serialization["explode"]:
                    value = ",".join(str(item) for item in value)
            query[parameter_name] = value
    try:
        return endpoint, _validated_params(query)
    except VSDPolicyError as exc:
        raise VSDDynamicRESTError(str(exc)) from exc


@register_tool("VSDDynamicRESTTool")
class VSDDynamicRESTTool(BaseTool):
    """Execute one already-reviewed, read-only JSON API operation."""

    def __init__(self, tool_config):
        super().__init__(_validated_operation_config(tool_config))
        self._input_validator = _schema_validator(
            self.tool_config["parameter"], field="parameter"
        )
        self._response_validator = _schema_validator(
            self.tool_config["vsd_operation"]["response_schema"],
            field="response_schema",
        )
        self._operation_digest = operation_digest(self.tool_config)

    def run(self, arguments=None, **_: Any):
        values = {} if arguments is None else arguments
        if not isinstance(values, dict):
            raise VSDDynamicRESTError("Tool arguments must be an object")
        try:
            self._input_validator.validate(values)
        except ValidationError as exc:
            raise VSDDynamicRESTError(
                f"Tool arguments failed the reviewed schema: {exc.message}"
            ) from exc

        endpoint, query = _provider_request(self.tool_config, values)
        operation = self.tool_config["vsd_operation"]
        headers, secret = _credential_headers(operation["auth"])
        request_kwargs: dict[str, Any] = {
            "timeout": float(operation["timeout_seconds"])
        }
        if headers:
            request_kwargs["headers"] = headers
        payload, request = _safe_get_json(endpoint, query, **request_kwargs)
        if secret is not None and _contains_secret(payload, secret):
            raise VSDDynamicRESTError("Provider response reflected credential material")
        try:
            self._response_validator.validate(payload)
        except ValidationError as exc:
            raise VSDDynamicRESTError(
                f"Provider response failed the reviewed schema: {exc.message}"
            ) from exc
        canonical = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode("utf-8")
        return {
            "status": "success",
            "data": {
                "result": payload,
                "provenance": {
                    "provider": urlsplit(endpoint).hostname,
                    "endpoint": endpoint,
                    "method": "GET",
                    "query_params": query,
                    "retrieved_at": datetime.now(timezone.utc).isoformat(),
                    "http_status": request["status_code"],
                    "content_type": request["content_type"],
                    "response_bytes": request["response_bytes"],
                    "redirects": request["redirects"],
                    "payload_sha256": hashlib.sha256(canonical).hexdigest(),
                    "operation_sha256": self._operation_digest,
                    "authentication": {
                        "type": operation["auth"]["type"],
                        "credential_source": (
                            "none"
                            if operation["auth"]["type"] == "none"
                            else "environment"
                        ),
                    },
                },
            },
        }


def register_reviewed_rest_tool(tooluniverse, config: dict[str, Any]) -> str:
    """Register one reviewed operation into a specific ToolUniverse instance."""
    normalized = _validated_operation_config(config)
    instance = VSDDynamicRESTTool(normalized)
    return tooluniverse.register_custom_tool(
        tool_class=VSDDynamicRESTTool,
        tool_name=normalized["name"],
        tool_config=normalized,
        tool_instance=instance,
    )


__all__ = [
    "VSDDynamicRESTError",
    "VSDDynamicRESTTool",
    "operation_digest",
    "register_reviewed_rest_tool",
]
