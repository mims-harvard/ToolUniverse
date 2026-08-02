"""Deterministic registry coverage analysis for VSD capability requests.

Coverage resolution is deliberately local and read-only.  It examines registered
ToolUniverse specifications before VSD searches an external catalog, and it does
not persist the request or report it to a third party.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlsplit

from .base_tool import BaseTool
from .execute_function import read_json_list
from .tool_registry import register_tool

_TEXT_RE = re.compile(r"^[^\x00-\x1f\x7f]{3,500}$")
_FIELD_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{0,63}$")
_OPERATION_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.:/-]{2,127}$")
_TOKEN_RE = re.compile(r"[a-z0-9]+")
_URL_RE = re.compile(r"https://[^\s\"'<>]+", re.IGNORECASE)
_METHODS = {"GET", "HEAD", "OPTIONS", "POST", "PUT", "PATCH", "DELETE"}
_STOP_WORDS = {
    "a",
    "an",
    "and",
    "api",
    "by",
    "data",
    "for",
    "from",
    "get",
    "in",
    "of",
    "on",
    "or",
    "search",
    "the",
    "to",
    "tool",
    "tools",
    "using",
    "with",
}


class VSDCoverageError(ValueError):
    """Raised when a capability request cannot be analyzed safely."""


def _bounded_text(value: Any, *, field: str, required: bool = False) -> str:
    text = str(value or "").strip()
    if not text:
        if required:
            raise VSDCoverageError(f"{field} is required")
        return ""
    if not _TEXT_RE.fullmatch(text):
        raise VSDCoverageError(f"{field} must contain 3-500 printable characters")
    return text


def _field_list(value: Any, *, field: str) -> list[str]:
    if value is None:
        return []
    if (
        not isinstance(value, list)
        or len(value) > 20
        or len(value) != len(set(value))
        or any(
            not isinstance(item, str) or not _FIELD_RE.fullmatch(item) for item in value
        )
    ):
        raise VSDCoverageError(
            f"{field} must contain at most 20 unique stable field names"
        )
    return list(value)


def _normalize_endpoint(value: Any) -> tuple[str, str]:
    if value in (None, ""):
        return "", ""
    if not isinstance(value, str) or len(value) > 1000:
        raise VSDCoverageError("endpoint must be a bounded HTTPS URL")
    parsed = urlsplit(value)
    if (
        parsed.scheme.lower() != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise VSDCoverageError(
            "endpoint must be an HTTPS URL without credentials, query, or fragment"
        )
    host = parsed.hostname.casefold().rstrip(".")
    path = re.sub(r"/+", "/", parsed.path or "/").rstrip("/") or "/"
    return host, path


def _normalize_provider(value: Any) -> str:
    provider = _bounded_text(value, field="provider")
    if not provider:
        return ""
    if "://" in provider:
        host, _ = _normalize_endpoint(provider)
        return host
    return provider.casefold().rstrip(".")


def normalize_capability_request(request: Any) -> dict[str, Any]:
    """Validate and canonicalize one non-sensitive capability description."""
    if not isinstance(request, dict):
        raise VSDCoverageError("Capability request must be an object")
    description = _bounded_text(
        request.get("description"), field="description", required=True
    )
    method = str(request.get("method") or "GET").upper()
    if method not in _METHODS:
        raise VSDCoverageError("method must be a recognized HTTP method")
    operation_id = str(request.get("operation_id") or "").strip()
    if operation_id and not _OPERATION_RE.fullmatch(operation_id):
        raise VSDCoverageError("operation_id must be a stable identifier")
    endpoint_host, endpoint_path = _normalize_endpoint(request.get("endpoint"))
    provider = _normalize_provider(request.get("provider"))
    if endpoint_host and provider and not _provider_matches(provider, endpoint_host):
        raise VSDCoverageError("provider does not match endpoint host")
    if endpoint_host:
        provider = endpoint_host
    return {
        "description": description,
        "provider": provider,
        "method": method,
        "endpoint_host": endpoint_host,
        "endpoint_path": endpoint_path,
        "operation_id": operation_id,
        "required_inputs": _field_list(
            request.get("required_inputs"), field="required_inputs"
        ),
        "output_fields": _field_list(
            request.get("output_fields"), field="output_fields"
        ),
    }


def _tokens(value: str) -> set[str]:
    return {
        token
        for token in _TOKEN_RE.findall(value.casefold().replace("_", " "))
        if token not in _STOP_WORDS and len(token) > 1
    }


def _flatten_strings(value: Any, *, limit: int = 1000) -> list[str]:
    found: list[str] = []
    pending = [value]
    while pending and len(found) < limit:
        item = pending.pop()
        if isinstance(item, str):
            found.append(item[:2000])
        elif isinstance(item, dict):
            pending.extend(reversed(list(item.keys())))
            pending.extend(reversed(list(item.values())))
        elif isinstance(item, list):
            pending.extend(reversed(item[:200]))
    return found


def _tool_hosts(config: dict[str, Any]) -> set[str]:
    hosts: set[str] = set()
    operation = config.get("vsd_operation")
    if isinstance(operation, dict):
        endpoint = operation.get("endpoint")
        if isinstance(endpoint, str):
            parsed = urlsplit(endpoint)
            if parsed.hostname:
                hosts.add(parsed.hostname.casefold().rstrip("."))
    for text in _flatten_strings(config, limit=300):
        for url in _URL_RE.findall(text):
            parsed = urlsplit(url.rstrip(".,);]"))
            if parsed.hostname:
                hosts.add(parsed.hostname.casefold().rstrip("."))
    return hosts


def _provider_terms(config: dict[str, Any]) -> set[str]:
    identity = {
        "name": config.get("name", ""),
        "type": config.get("type", ""),
        "category": config.get("category", ""),
        "provider": config.get("provider", ""),
        "source": config.get("source", ""),
        "vsd_promotion": config.get("vsd_promotion", {}),
    }
    return _tokens(" ".join(_flatten_strings(identity, limit=100)))


def _provider_matches(requested: str, actual: str) -> bool:
    if not requested or not actual:
        return False
    requested = requested.casefold().rstrip(".")
    actual = actual.casefold().rstrip(".")
    if requested == actual:
        return True
    if "." in requested and "." in actual:
        return requested.endswith("." + actual) or actual.endswith("." + requested)
    return requested in _tokens(actual) or actual in _tokens(requested)


def _schema_fields(schema: Any) -> set[str]:
    if not isinstance(schema, dict):
        return set()
    fields: set[str] = set()
    properties = schema.get("properties")
    if isinstance(properties, dict):
        fields.update(str(name).casefold() for name in properties)
        for child in properties.values():
            fields.update(_schema_fields(child))
    items = schema.get("items")
    if isinstance(items, dict):
        fields.update(_schema_fields(items))
    return fields


def _schema_terms(schema: Any) -> set[str]:
    """Return field identifiers plus bounded descriptive terms for alias matching."""
    fields = _schema_fields(schema)
    terms = set(fields)
    for field in fields:
        terms.update(_tokens(field))
        terms.add(re.sub(r"[^a-z0-9]", "", field))
    for text in _flatten_strings(schema, limit=300):
        terms.update(_tokens(text))
    return terms


def _field_recall(requested: Iterable[str], available: set[str]) -> float:
    values = list(requested)
    if not values:
        return 1.0
    matches = 0
    for value in values:
        normalized = value.casefold()
        collapsed = re.sub(r"[^a-z0-9]", "", normalized)
        value_tokens = _tokens(normalized)
        if (
            normalized in available
            or collapsed in available
            or (value_tokens and value_tokens <= available)
        ):
            matches += 1
    return matches / len(values)


def _registry_tools(tooluniverse: Any) -> list[dict[str, Any]]:
    """Read built-in specifications plus runtime registrations without loading tools."""
    from .tool_registry import get_config_registry, get_list_config_registry

    indexed: dict[str, dict[str, Any]] = {}
    tool_files = getattr(tooluniverse, "tool_files", {})
    if isinstance(tool_files, dict):
        for category, file_path in sorted(tool_files.items()):
            try:
                entries = read_json_list(Path(file_path))
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                continue
            if isinstance(entries, dict):
                entries = [entries]
            if not isinstance(entries, list):
                continue
            for entry in entries:
                if isinstance(entry, dict) and isinstance(entry.get("name"), str):
                    record = dict(entry)
                    record.setdefault("category", category)
                    indexed[record["name"]] = record
    if callable(getattr(tooluniverse, "_load_auto_discovered_configs", None)):
        auto_discovered = list(get_config_registry().values())
        auto_discovered.extend(get_list_config_registry())
        for entry in auto_discovered:
            if isinstance(entry, dict) and isinstance(entry.get("name"), str):
                indexed.setdefault(entry["name"], dict(entry))
    for entry in getattr(tooluniverse, "all_tools", []):
        if isinstance(entry, dict) and isinstance(entry.get("name"), str):
            indexed[entry["name"]] = dict(entry)
    return [indexed[name] for name in sorted(indexed, key=str.casefold)]


def _ratio(requested: Iterable[str], available: set[str]) -> float:
    requested_set = {str(value).casefold() for value in requested}
    if not requested_set:
        return 1.0
    return len(requested_set & available) / len(requested_set)


def _operation_identity(config: dict[str, Any]) -> tuple[str, str, str]:
    operation = config.get("vsd_operation")
    if not isinstance(operation, dict):
        return "", "", ""
    endpoint = operation.get("endpoint")
    if not isinstance(endpoint, str):
        return "", "", ""
    parsed = urlsplit(endpoint)
    if not parsed.hostname:
        return "", "", ""
    path = re.sub(r"/+", "/", parsed.path or "/").rstrip("/") or "/"
    return (
        str(operation.get("method") or "GET").upper(),
        parsed.hostname.casefold().rstrip("."),
        path,
    )


def _match_tool(
    request: dict[str, Any], config: dict[str, Any]
) -> dict[str, Any] | None:
    name = str(config.get("name") or "")
    if not name:
        return None
    searchable = " ".join(
        _flatten_strings(
            {
                "name": name,
                "description": config.get("description", ""),
                "category": config.get("category", ""),
                "parameter": config.get("parameter", {}),
                "return_schema": config.get("return_schema", {}),
                "required_tools": config.get("required_tools", []),
                "vsd_capability": config.get("vsd_capability", {}),
            }
        )
    )
    available_tokens = _tokens(searchable)
    requested_tokens = _tokens(request["description"])
    semantic_recall = _ratio(requested_tokens, available_tokens)

    hosts = _tool_hosts(config)
    provider_match = any(_provider_matches(request["provider"], host) for host in hosts)
    if request["provider"] and not provider_match:
        provider_tokens = _tokens(request["provider"])
        provider_match = bool(provider_tokens) and provider_tokens <= _provider_terms(
            config
        )

    parameter_fields = _schema_terms(config.get("parameter"))
    return_fields = _schema_terms(config.get("return_schema"))
    operation = config.get("vsd_operation")
    if isinstance(operation, dict):
        response_schema = operation.get("response_schema")
        return_fields.update(_schema_terms(response_schema))
    input_recall = _field_recall(request["required_inputs"], parameter_fields)
    output_recall = _field_recall(
        request["output_fields"], return_fields | available_tokens
    )

    method, host, path = _operation_identity(config)
    endpoint_match = bool(
        request["endpoint_host"]
        and request["endpoint_path"]
        and request["method"] == method
        and request["endpoint_host"] == host
        and request["endpoint_path"] == path
    )
    capability = config.get("vsd_capability")
    explicit_operation_match = bool(
        request["operation_id"]
        and isinstance(capability, dict)
        and capability.get("operation_id") == request["operation_id"]
    )

    score = (
        semantic_recall * 0.5
        + (0.2 if provider_match else 0.0)
        + input_recall * 0.15
        + output_recall * 0.1
        + (0.05 if endpoint_match or explicit_operation_match else 0.0)
    )
    kind = (
        "workflow"
        if config.get("type") == "ComposeTool"
        or str(config.get("category") or "").casefold() == "compose_tools"
        else "tool"
    )
    exact = bool(
        explicit_operation_match
        or (endpoint_match and input_recall == 1.0 and output_recall >= 0.5)
        or (
            provider_match
            and semantic_recall >= 0.6
            and input_recall == 1.0
            and output_recall >= 0.5
        )
        or (
            kind == "workflow"
            and not request["provider"]
            and semantic_recall >= 0.8
            and input_recall == 1.0
            and output_recall >= 0.5
        )
    )
    plausible = (
        exact or provider_match
        if request["provider"]
        else exact or semantic_recall >= 0.5 or score >= 0.55
    )
    if not plausible:
        return None
    return {
        "name": name,
        "kind": kind,
        "coverage": "exact" if exact else "partial",
        "score": round(score, 4),
        "provider_match": provider_match,
        "operation_match": endpoint_match or explicit_operation_match,
        "semantic_recall": round(semantic_recall, 4),
        "input_recall": round(input_recall, 4),
        "output_recall": round(output_recall, 4),
        "category": str(config.get("category") or ""),
        "description": str(config.get("description") or "")[:500],
    }


def _resolve_normalized_capability(
    normalized: dict[str, Any],
    registry: list[dict[str, Any]],
    *,
    limit: int,
) -> dict[str, Any]:
    """Resolve one validated request against one immutable registry snapshot."""
    matches = [
        match
        for config in registry
        if (match := _match_tool(normalized, config)) is not None
    ]
    matches.sort(
        key=lambda match: (
            match["coverage"] != "exact",
            -match["score"],
            match["kind"] != "tool",
            match["name"].casefold(),
        )
    )
    selected = matches[:limit]
    exact = [match for match in matches if match["coverage"] == "exact"]
    if exact:
        classification = "existing_exact"
        action = "use_existing"
    elif matches:
        classification = "existing_partial"
        action = "review_existing_or_extend_provider"
    else:
        classification = "missing"
        action = "discover_external_candidate"

    registry_summary = [
        {
            "name": config.get("name"),
            "type": config.get("type"),
            "category": config.get("category"),
            "description": config.get("description"),
            "parameter": config.get("parameter"),
            "return_schema": config.get("return_schema"),
            "vsd_operation": config.get("vsd_operation"),
        }
        for config in registry
    ]
    request_digest = hashlib.sha256(
        json.dumps(
            normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode("utf-8")
    ).hexdigest()
    registry_digest = hashlib.sha256(
        json.dumps(
            registry_summary,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()
    return {
        "status": "success",
        "data": {
            "capability_id": request_digest[:16],
            "classification": classification,
            "recommended_action": action,
            "request": normalized,
            "matches": selected,
            "match_count": len(matches),
            "exact_match_count": len(exact),
            "tool_matches": sum(match["kind"] == "tool" for match in matches),
            "workflow_matches": sum(match["kind"] == "workflow" for match in matches),
            "registry_tool_count": len(registry),
            "registry_sha256": registry_digest,
            "privacy": (
                "Coverage resolution is local, read-only, and not persisted or reported."
            ),
        },
    }


def resolve_capability(
    tooluniverse: Any, request: dict[str, Any], *, limit: int = 10
) -> dict[str, Any]:
    """Classify a capability against existing tools and composed workflows."""
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 20:
        raise VSDCoverageError("limit must be an integer between 1 and 20")
    normalized = normalize_capability_request(request)
    return _resolve_normalized_capability(
        normalized,
        _registry_tools(tooluniverse),
        limit=limit,
    )


@register_tool("VSDResolveCapability")
class VSDResolveCapability(BaseTool):
    """Resolve a requested capability against ToolUniverse before API discovery."""

    def __init__(self, tool_config, tooluniverse=None):
        super().__init__(tool_config)
        self.tooluniverse = tooluniverse

    def run(self, arguments=None, **_: Any):
        if self.tooluniverse is None:
            raise VSDCoverageError("ToolUniverse reference is required")
        arguments = arguments or {}
        if not isinstance(arguments, dict):
            raise VSDCoverageError("Tool arguments must be an object")
        limit = arguments.get("limit", 10)
        request = {key: value for key, value in arguments.items() if key != "limit"}
        return resolve_capability(self.tooluniverse, request, limit=limit)


__all__ = [
    "VSDCoverageError",
    "VSDResolveCapability",
    "normalize_capability_request",
    "resolve_capability",
]
