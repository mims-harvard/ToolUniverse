"""Bounded OpenAPI ingestion for administrator-reviewed VSD promotion.

The functions in this module inspect a local OpenAPI document and emit inert
operation candidates. They never fetch a specification, execute an operation,
persist a tool, or bypass the existing verification and approval pipeline.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import yaml
from yaml.constructor import ConstructorError
from yaml.events import AliasEvent

from .vsd_dynamic_rest import VSDDynamicRESTError, _schema_validator, _validated_auth

_FORMAT_VERSION = 1
_MAX_DOCUMENT_BYTES = 1_000_000
_MAX_DOCUMENT_DEPTH = 100
_MAX_DOCUMENT_NODES = 100_000
_MAX_PATHS = 250
_MAX_OPERATIONS = 500
_MAX_SERVERS = 20
_MAX_PARAMETERS = 100
_MAX_TEXT = 2_000
_MAX_RESPONSE_SCHEMA_BYTES = 65_536
_HTTP_METHODS = frozenset(
    {"delete", "get", "head", "options", "patch", "post", "put", "trace"}
)
_ARGUMENT_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,63}$")
_PROVIDER_PARAMETER_RE = re.compile(r"^[A-Za-z0-9_.\[\]-]{1,128}$")
_PATH_TOKEN_RE = re.compile(r"\{([^{}]+)\}")
_JSON_TYPES = frozenset(
    {"array", "boolean", "integer", "null", "number", "object", "string"}
)


class VSDOpenAPIError(ValueError):
    """Raised when an OpenAPI document crosses the safe ingestion boundary."""


class _StrictSafeLoader(yaml.SafeLoader):
    """Safe YAML loader that rejects aliases and duplicate mapping keys."""

    def compose_node(self, parent, index):
        if self.check_event(AliasEvent):
            event = self.get_event()
            raise ConstructorError(
                None,
                None,
                f"YAML aliases are not supported: *{event.anchor}",
                event.start_mark,
            )
        return super().compose_node(parent, index)

    def construct_mapping(self, node, deep=False):
        self.flatten_mapping(node)
        mapping: dict[Any, Any] = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            try:
                duplicate = key in mapping
            except TypeError as exc:
                raise ConstructorError(
                    "while constructing a mapping",
                    node.start_mark,
                    "found an unhashable mapping key",
                    key_node.start_mark,
                ) from exc
            if duplicate:
                raise ConstructorError(
                    "while constructing a mapping",
                    node.start_mark,
                    f"found duplicate key {key!r}",
                    key_node.start_mark,
                )
            mapping[key] = self.construct_object(value_node, deep=deep)
        return mapping


def _duplicate_json_key(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise VSDOpenAPIError(f"JSON document contains duplicate key {key!r}")
        result[key] = value
    return result


def _bounded_document(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise VSDOpenAPIError("OpenAPI document root must be an object")
    count = 0
    pending: list[tuple[Any, int]] = [(value, 0)]
    while pending:
        node, depth = pending.pop()
        count += 1
        if count > _MAX_DOCUMENT_NODES:
            raise VSDOpenAPIError("OpenAPI document exceeds the node limit")
        if depth > _MAX_DOCUMENT_DEPTH:
            raise VSDOpenAPIError("OpenAPI document exceeds the depth limit")
        if isinstance(node, dict):
            for key, child in node.items():
                if not isinstance(key, str):
                    raise VSDOpenAPIError("OpenAPI object keys must be strings")
                pending.append((child, depth + 1))
        elif isinstance(node, list):
            pending.extend((child, depth + 1) for child in node)
        elif isinstance(node, float) and not math.isfinite(node):
            raise VSDOpenAPIError("OpenAPI document must contain finite JSON values")
        elif node is not None and not isinstance(node, (str, int, float, bool)):
            raise VSDOpenAPIError("OpenAPI document contains a non-JSON value")
    return value


def load_openapi_document(path: str | Path) -> tuple[dict[str, Any], str]:
    """Load one bounded local JSON or YAML document and return it with its hash."""
    source = Path(path)
    try:
        size = source.stat().st_size
        if size > _MAX_DOCUMENT_BYTES:
            raise VSDOpenAPIError("OpenAPI document exceeds the 1 MB limit")
        raw = source.read_bytes()
    except OSError as exc:
        raise VSDOpenAPIError(f"Could not read OpenAPI document {source}") from exc
    if len(raw) > _MAX_DOCUMENT_BYTES:
        raise VSDOpenAPIError("OpenAPI document exceeds the 1 MB limit")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise VSDOpenAPIError("OpenAPI document must be UTF-8") from exc

    try:
        if source.suffix.casefold() == ".json" or text.lstrip().startswith(("{", "[")):
            value = json.loads(
                text,
                object_pairs_hook=_duplicate_json_key,
                parse_constant=lambda value: (_ for _ in ()).throw(
                    VSDOpenAPIError(f"Non-finite JSON value {value!r} is prohibited")
                ),
            )
        else:
            value = yaml.load(text, Loader=_StrictSafeLoader)
    except VSDOpenAPIError:
        raise
    except json.JSONDecodeError as exc:
        raise VSDOpenAPIError(
            "OpenAPI document is not valid JSON or safe YAML"
        ) from exc
    except yaml.YAMLError as exc:
        detail = str(getattr(exc, "problem", None) or exc).splitlines()[0]
        raise VSDOpenAPIError(f"OpenAPI YAML rejected: {detail}") from exc
    return _bounded_document(value), hashlib.sha256(raw).hexdigest()


def _text(value: Any, *, fallback: str = "") -> str:
    if not isinstance(value, str):
        return fallback
    normalized = " ".join(value.split())
    return normalized[:_MAX_TEXT]


def _pointer(document: dict[str, Any], reference: str) -> Any:
    if not reference.startswith("#/"):
        raise VSDOpenAPIError("external_reference")
    current: Any = document
    for raw_token in reference[2:].split("/"):
        token = raw_token.replace("~1", "/").replace("~0", "~")
        if not isinstance(current, dict) or token not in current:
            raise VSDOpenAPIError("unresolved_local_reference")
        current = current[token]
    return current


def _resolved_object(
    value: Any, document: dict[str, Any], *, kind: str
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise VSDOpenAPIError(f"{kind}_not_object")
    reference = value.get("$ref")
    if reference is None:
        return value
    if not isinstance(reference, str):
        raise VSDOpenAPIError("invalid_reference")
    target = _pointer(document, reference)
    if not isinstance(target, dict):
        raise VSDOpenAPIError(f"referenced_{kind}_not_object")
    merged = copy.deepcopy(target)
    merged.update({key: child for key, child in value.items() if key != "$ref"})
    return merged


def _schema_closure(schema: Any, document: dict[str, Any]) -> dict[str, Any]:
    """Convert an OpenAPI schema into a self-contained JSON Schema."""
    if schema is True:
        return {}
    if schema is False:
        return {"not": {}}
    if not isinstance(schema, dict):
        raise VSDOpenAPIError("response_schema_missing")
    definitions: dict[str, Any] = {}
    active: set[str] = set()

    def convert(node: Any) -> Any:
        if isinstance(node, list):
            return [convert(child) for child in node]
        if not isinstance(node, dict):
            return copy.deepcopy(node)
        reference = node.get("$ref")
        converted: dict[str, Any] = {}
        if reference is not None:
            if not isinstance(reference, str) or not reference.startswith(
                "#/components/schemas/"
            ):
                raise VSDOpenAPIError("external_or_unsupported_schema_reference")
            name = reference.removeprefix("#/components/schemas/")
            if not name or "/" in name:
                raise VSDOpenAPIError("unsupported_schema_reference")
            converted["$ref"] = f"#/$defs/{name}"
            if name not in definitions and name not in active:
                active.add(name)
                target = _pointer(document, reference)
                definitions[name] = convert(target)
                active.remove(name)

        for key, child in node.items():
            if key in {"$ref", "discriminator", "example", "externalDocs", "xml"}:
                continue
            if key == "nullable":
                continue
            converted[key] = convert(child)

        if node.get("nullable") is True:
            schema_type = converted.get("type")
            if isinstance(schema_type, str) and schema_type in _JSON_TYPES:
                converted["type"] = [schema_type, "null"]
            elif isinstance(schema_type, list) and "null" not in schema_type:
                converted["type"] = [*schema_type, "null"]
            else:
                converted = {"anyOf": [converted, {"type": "null"}]}
        if node.get("exclusiveMinimum") is True and isinstance(
            node.get("minimum"), (int, float)
        ):
            converted["exclusiveMinimum"] = node["minimum"]
            converted.pop("minimum", None)
        if node.get("exclusiveMaximum") is True and isinstance(
            node.get("maximum"), (int, float)
        ):
            converted["exclusiveMaximum"] = node["maximum"]
            converted.pop("maximum", None)
        return converted

    root = convert(schema)
    if definitions:
        root["$defs"] = definitions
    try:
        _schema_validator(root, field="OpenAPI schema")
    except VSDDynamicRESTError as exc:
        raise VSDOpenAPIError(str(exc)) from exc
    return root


def _server_url(
    operation: dict[str, Any],
    path_item: dict[str, Any],
    document: dict[str, Any],
    *,
    server_index: int,
    server_url_override: str | None = None,
) -> str:
    if server_url_override is not None:
        return _plain_https_server_url(server_url_override)
    servers = operation.get(
        "servers", path_item.get("servers", document.get("servers"))
    )
    if not isinstance(servers, list) or not servers:
        raise VSDOpenAPIError("server_missing")
    if len(servers) > _MAX_SERVERS:
        raise VSDOpenAPIError("too_many_servers")
    if not 0 <= server_index < len(servers):
        raise VSDOpenAPIError("server_index_out_of_range")
    server = servers[server_index]
    if not isinstance(server, dict) or not isinstance(server.get("url"), str):
        raise VSDOpenAPIError("server_invalid")
    url = server["url"]
    variables = server.get("variables", {})
    if not isinstance(variables, dict):
        raise VSDOpenAPIError("server_variables_invalid")
    for name in _PATH_TOKEN_RE.findall(url):
        definition = variables.get(name)
        default = definition.get("default") if isinstance(definition, dict) else None
        if not isinstance(default, (str, int, float, bool)):
            raise VSDOpenAPIError("server_variable_default_missing")
        url = url.replace("{" + name + "}", str(default))
    return _plain_https_server_url(url)


def _plain_https_server_url(value: Any) -> str:
    if not isinstance(value, str):
        raise VSDOpenAPIError("server_must_be_plain_https")
    parsed = urlsplit(value)
    if (
        parsed.scheme.casefold() != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise VSDOpenAPIError("server_must_be_plain_https")
    return value.rstrip("/")


def _argument_name(provider_name: str, location: str, used: set[str]) -> str:
    base = re.sub(r"[^A-Za-z0-9_]+", "_", provider_name).strip("_")
    if not base or not base[0].isalpha():
        base = f"param_{base}"
    base = base[:64]
    if not _ARGUMENT_RE.fullmatch(base):
        base = f"parameter_{hashlib.sha256(provider_name.encode()).hexdigest()[:8]}"
    candidate = base
    if candidate in used:
        suffix = hashlib.sha256(f"{location}:{provider_name}".encode()).hexdigest()[:8]
        candidate = f"{base[:55]}_{suffix}"
    if candidate in used:
        raise VSDOpenAPIError("parameter_name_collision")
    used.add(candidate)
    return candidate


def _parameters(
    operation: dict[str, Any], path_item: dict[str, Any], document: dict[str, Any]
) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    raw_parameters = [
        *(path_item.get("parameters", []) or []),
        *(operation.get("parameters", []) or []),
    ]
    if not isinstance(raw_parameters, list) or len(raw_parameters) > _MAX_PARAMETERS:
        raise VSDOpenAPIError("parameters_invalid_or_excessive")
    by_identity: dict[tuple[str, str], dict[str, Any]] = {}
    blockers: list[str] = []
    warnings: list[str] = []
    for raw in raw_parameters:
        try:
            parameter = _resolved_object(raw, document, kind="parameter")
        except VSDOpenAPIError as exc:
            blockers.append(str(exc))
            continue
        name, location = parameter.get("name"), parameter.get("in")
        if (
            not isinstance(name, str)
            or not name
            or location
            not in {
                "cookie",
                "header",
                "path",
                "query",
            }
        ):
            blockers.append("parameter_identity_invalid")
            continue
        if not _PROVIDER_PARAMETER_RE.fullmatch(name):
            blockers.append(f"unsupported_parameter_name:{location}:{name}")
            continue
        if location == "path" and not _ARGUMENT_RE.fullmatch(name):
            blockers.append(f"unsupported_path_parameter_name:{name}")
            continue
        by_identity[(location, name)] = parameter

    used: set[str] = set()
    normalized: list[dict[str, Any]] = []
    for (location, name), parameter in by_identity.items():
        required = parameter.get("required") is True or location == "path"
        if location not in {"path", "query"}:
            message = f"unsupported_{location}_parameter:{name}"
            (blockers if required else warnings).append(message)
            continue
        raw_schema = parameter.get("schema")
        try:
            schema = _schema_closure(raw_schema, document)
        except VSDOpenAPIError as exc:
            blockers.append(f"parameter_schema:{name}:{exc}")
            continue
        schema_type = schema.get("type")
        if schema_type == "object" or (schema_type == "array" and location == "path"):
            blockers.append(f"unsupported_parameter_shape:{location}:{name}")
            continue
        style = parameter.get("style", "simple" if location == "path" else "form")
        explode = parameter.get("explode", style == "form")
        if location == "query" and style not in {
            "form",
            "pipeDelimited",
            "spaceDelimited",
        }:
            blockers.append(f"unsupported_query_style:{name}:{style}")
            continue
        normalized.append(
            {
                "argument_name": _argument_name(name, location, used),
                "provider_name": name,
                "location": location,
                "required": required,
                "description": _text(parameter.get("description")),
                "style": style,
                "explode": bool(explode),
                "schema": schema,
            }
        )
    return normalized, sorted(set(blockers)), sorted(set(warnings))


def _response_schema(
    operation: dict[str, Any], document: dict[str, Any]
) -> tuple[dict[str, Any] | None, str | None, list[str]]:
    responses = operation.get("responses")
    if not isinstance(responses, dict):
        return None, None, ["responses_missing"]
    success_keys = sorted(
        str(key) for key in responses if re.fullmatch(r"2[0-9][0-9]", str(key))
    )
    if not success_keys:
        return None, None, ["success_response_missing"]
    try:
        response = _resolved_object(
            responses[success_keys[0]], document, kind="response"
        )
    except VSDOpenAPIError as exc:
        return None, None, [str(exc)]
    content = response.get("content")
    if not isinstance(content, dict):
        return None, None, ["json_response_missing"]
    media_type = next(
        (item for item in content if item.casefold() == "application/json"),
        None,
    )
    if media_type is None:
        media_type = next(
            (
                item
                for item in content
                if item.casefold().startswith("application/")
                and item.casefold().endswith("+json")
            ),
            None,
        )
    if media_type is None or not isinstance(content.get(media_type), dict):
        return None, None, ["json_response_missing"]
    try:
        schema = _schema_closure(content[media_type].get("schema"), document)
    except VSDOpenAPIError as exc:
        return None, media_type, [f"response_schema:{exc}"]
    encoded = json.dumps(schema, separators=(",", ":"), ensure_ascii=True)
    if len(encoded.encode("utf-8")) > _MAX_RESPONSE_SCHEMA_BYTES:
        return None, media_type, ["response_schema_too_large"]
    return schema, media_type, []


def _authentication_descriptor(
    operation: dict[str, Any], document: dict[str, Any]
) -> tuple[dict[str, str] | None, list[str]]:
    security = operation.get("security", document.get("security", []))
    if security in (None, []):
        return None, []
    blockers = ["authentication_required"]
    if not isinstance(security, list) or not 1 <= len(security) <= 20:
        return None, [*blockers, "authentication_requirements_invalid"]
    if any(requirement == {} for requirement in security):
        return None, []
    if len(security) != 1 or not isinstance(security[0], dict) or len(security[0]) != 1:
        return None, [*blockers, "authentication_alternatives_unsupported"]
    scheme_name, scopes = next(iter(security[0].items()))
    if not isinstance(scheme_name, str) or not scheme_name or scopes != []:
        return None, [*blockers, "authentication_scopes_unsupported"]
    components = document.get("components")
    schemes = (
        components.get("securitySchemes") if isinstance(components, dict) else None
    )
    raw_scheme = schemes.get(scheme_name) if isinstance(schemes, dict) else None
    try:
        scheme = _resolved_object(raw_scheme, document, kind="security_scheme")
    except VSDOpenAPIError as exc:
        return None, [*blockers, f"authentication_scheme:{exc}"]
    scheme_type = str(scheme.get("type") or "").casefold()
    if scheme_type == "apikey" and str(scheme.get("in") or "").casefold() == "header":
        header = scheme.get("name")
        try:
            normalized = _validated_auth(
                {
                    "type": "api_key_header_env",
                    "env_var": "TOOLUNIVERSE_VSD_INSPECTION_PLACEHOLDER",
                    "header": header,
                }
            )
        except VSDDynamicRESTError as exc:
            return None, [*blockers, f"authentication_scheme:{exc}"]
        return {
            "type": "api_key_header",
            "scheme_name": _text(scheme_name),
            "header": normalized["header"],
        }, []
    if scheme_type == "http" and str(scheme.get("scheme") or "").casefold() == "bearer":
        return {
            "type": "bearer",
            "scheme_name": _text(scheme_name),
        }, []
    return None, [*blockers, "authentication_scheme_unsupported"]


def _validate_auth_descriptor(value: Any) -> None:
    if value is None:
        return
    if not isinstance(value, dict):
        raise VSDOpenAPIError("OpenAPI candidate authentication is invalid")
    auth_type = value.get("type")
    scheme_name = value.get("scheme_name")
    if not isinstance(scheme_name, str) or not scheme_name or len(scheme_name) > 2000:
        raise VSDOpenAPIError("OpenAPI candidate authentication is invalid")
    try:
        if auth_type == "api_key_header" and set(value) == {
            "type",
            "scheme_name",
            "header",
        }:
            _validated_auth(
                {
                    "type": "api_key_header_env",
                    "env_var": "TOOLUNIVERSE_VSD_INSPECTION_PLACEHOLDER",
                    "header": value.get("header"),
                }
            )
            return
        if auth_type == "bearer" and set(value) == {"type", "scheme_name"}:
            return
    except VSDDynamicRESTError as exc:
        raise VSDOpenAPIError("OpenAPI candidate authentication is invalid") from exc
    raise VSDOpenAPIError("OpenAPI candidate authentication is invalid")


def _candidate_digest(body: dict[str, Any]) -> str:
    encoded = json.dumps(
        body, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def inspect_openapi_document(
    path: str | Path,
    *,
    server_index: int = 0,
    server_url_override: str | None = None,
) -> dict[str, Any]:
    """Inspect a local OpenAPI document and return inert operation candidates."""
    if server_url_override is not None:
        server_url_override = _plain_https_server_url(server_url_override)
    document, document_sha256 = load_openapi_document(path)
    version = document.get("openapi")
    if not isinstance(version, str) or not re.fullmatch(
        r"3\.(?:0|1)(?:\.[0-9]+)?", version
    ):
        raise VSDOpenAPIError("Only OpenAPI 3.0 and 3.1 documents are supported")
    info = document.get("info")
    if (
        not isinstance(info, dict)
        or not isinstance(info.get("title"), str)
        or not info["title"].strip()
        or not isinstance(info.get("version"), str)
        or not info["version"].strip()
    ):
        raise VSDOpenAPIError("OpenAPI info.title and info.version are required")
    paths = document.get("paths")
    if not isinstance(paths, dict) or not paths or len(paths) > _MAX_PATHS:
        raise VSDOpenAPIError("OpenAPI paths must contain 1-250 entries")

    candidates: list[dict[str, Any]] = []
    for path_name, raw_path_item in sorted(paths.items()):
        if not isinstance(path_name, str) or not path_name.startswith("/"):
            raise VSDOpenAPIError("OpenAPI path keys must start with '/'")
        try:
            path_item = _resolved_object(raw_path_item, document, kind="path_item")
        except VSDOpenAPIError as exc:
            raise VSDOpenAPIError(f"Path {path_name!r} is invalid: {exc}") from exc
        for method in sorted(set(path_item) & _HTTP_METHODS):
            if len(candidates) >= _MAX_OPERATIONS:
                raise VSDOpenAPIError("OpenAPI document exceeds the operation limit")
            raw_operation = path_item[method]
            blockers: list[str] = []
            warnings: list[str] = []
            if not isinstance(raw_operation, dict):
                blockers.append("operation_not_object")
                operation: dict[str, Any] = {}
            else:
                operation = raw_operation
            if method != "get":
                blockers.append("method_not_read_only")
            if operation.get("deprecated") is True:
                blockers.append("operation_deprecated")
            if "requestBody" in operation:
                blockers.append("request_body_not_supported")
            if "callbacks" in operation:
                blockers.append("callbacks_not_supported")
            auth, authentication_blockers = _authentication_descriptor(
                operation, document
            )
            blockers.extend(authentication_blockers)
            try:
                server_url = _server_url(
                    operation,
                    path_item,
                    document,
                    server_index=server_index,
                    server_url_override=server_url_override,
                )
            except VSDOpenAPIError as exc:
                server_url = ""
                blockers.append(str(exc))
            parameters, parameter_blockers, parameter_warnings = _parameters(
                operation, path_item, document
            )
            blockers.extend(parameter_blockers)
            warnings.extend(parameter_warnings)
            tokens = _PATH_TOKEN_RE.findall(path_name)
            mapped_tokens = {
                item["provider_name"]
                for item in parameters
                if item["location"] == "path"
            }
            if len(tokens) != len(set(tokens)) or set(tokens) != mapped_tokens:
                blockers.append("path_parameters_do_not_match_template")
            response_schema, response_media_type, response_blockers = _response_schema(
                operation, document
            )
            blockers.extend(response_blockers)
            if server_url_override is not None:
                warnings.append("server_url_override_applied")
            operation_id = operation.get("operationId")
            if not isinstance(operation_id, str) or not operation_id.strip():
                operation_id = f"{method}_{path_name}"
                warnings.append("operation_id_missing")
            candidate_body = {
                "format": "vsd_openapi_operation_v1",
                "version": _FORMAT_VERSION,
                "approval_state": "unreviewed_candidate",
                "execution_allowed": False,
                "metadata_trust": "untrusted_openapi_metadata",
                "source_document_sha256": document_sha256,
                "openapi_version": version,
                "api_title": _text(info["title"]),
                "api_version": _text(info["version"]),
                "server_url": server_url,
                "path": path_name,
                "method": method.upper(),
                "operation_id": _text(operation_id),
                "summary": _text(operation.get("summary"), fallback=operation_id),
                "description": _text(operation.get("description")),
                "tags": [
                    _text(tag)
                    for tag in operation.get("tags", [])
                    if isinstance(tag, str)
                ][:20],
                "parameters": parameters,
                "auth": auth,
                "response_media_type": response_media_type,
                "response_schema": response_schema,
                "blockers": sorted(set(blockers)),
                "warnings": sorted(set(warnings)),
            }
            digest = _candidate_digest(candidate_body)
            candidates.append(
                {
                    **candidate_body,
                    "candidate_id": digest[:16],
                    "candidate_sha256": digest,
                }
            )
    return {
        "format": "vsd_openapi_inspection_v1",
        "version": _FORMAT_VERSION,
        "source_file": Path(path).name,
        "source_document_sha256": document_sha256,
        "openapi_version": version,
        "api_title": _text(info["title"]),
        "api_version": _text(info["version"]),
        "candidate_count": len(candidates),
        "promotable_count": sum(not item["blockers"] for item in candidates),
        "blocked_count": sum(bool(item["blockers"]) for item in candidates),
        "candidates": candidates,
    }


def validate_openapi_candidate(
    candidate: Any, *, permit_missing_json_response: bool = False
) -> dict[str, Any]:
    """Validate the integrity and inert state of one inspection candidate.

    ``permit_missing_json_response`` is reserved for the reviewed promotion
    path. It accepts only the single, narrow case where an otherwise safe GET
    operation omitted its JSON response contract; it never makes the candidate
    directly promotable.
    """
    if not isinstance(candidate, dict):
        raise VSDOpenAPIError("OpenAPI candidate must be an object")
    if (
        candidate.get("format") != "vsd_openapi_operation_v1"
        or candidate.get("version") != _FORMAT_VERSION
        or candidate.get("approval_state") != "unreviewed_candidate"
        or candidate.get("execution_allowed") is not False
        or candidate.get("metadata_trust") != "untrusted_openapi_metadata"
    ):
        raise VSDOpenAPIError("Candidate did not come from the OpenAPI boundary")
    body = {
        key: value
        for key, value in candidate.items()
        if key not in {"candidate_id", "candidate_sha256"}
    }
    digest = _candidate_digest(body)
    if (
        candidate.get("candidate_sha256") != digest
        or candidate.get("candidate_id") != digest[:16]
    ):
        raise VSDOpenAPIError("OpenAPI candidate digest does not match its content")
    blockers = candidate.get("blockers")
    if (
        not isinstance(blockers, list)
        or any(not isinstance(item, str) or not item for item in blockers)
        or blockers != sorted(set(blockers))
    ):
        raise VSDOpenAPIError("OpenAPI candidate blockers are invalid")
    missing_json_response = blockers == ["json_response_missing"]
    if blockers and not (permit_missing_json_response and missing_json_response):
        raise VSDOpenAPIError(f"OpenAPI candidate is not promotable: {blockers!r}")
    parameters = candidate.get("parameters")
    if not isinstance(parameters, list) or len(parameters) > _MAX_PARAMETERS:
        raise VSDOpenAPIError("OpenAPI candidate parameters are invalid")
    _validate_auth_descriptor(candidate.get("auth"))
    argument_names: set[str] = set()
    path_names: set[str] = set()
    for parameter in parameters:
        if not isinstance(parameter, dict):
            raise VSDOpenAPIError("OpenAPI candidate parameter is invalid")
        argument = parameter.get("argument_name")
        provider = parameter.get("provider_name")
        location = parameter.get("location")
        style = parameter.get("style")
        explode = parameter.get("explode")
        if (
            not isinstance(argument, str)
            or not _ARGUMENT_RE.fullmatch(argument)
            or argument in argument_names
            or not isinstance(provider, str)
            or not _PROVIDER_PARAMETER_RE.fullmatch(provider)
            or location not in {"path", "query"}
            or type(parameter.get("required")) is not bool
            or type(explode) is not bool
            or (location == "path" and style != "simple")
            or (
                location == "query"
                and style not in {"form", "pipeDelimited", "spaceDelimited"}
            )
            or (style != "form" and explode)
        ):
            raise VSDOpenAPIError("OpenAPI candidate parameter contract is invalid")
        try:
            _schema_validator(parameter.get("schema"), field=f"parameter {argument}")
        except VSDDynamicRESTError as exc:
            raise VSDOpenAPIError(
                f"OpenAPI candidate parameter {argument!r} has an invalid schema"
            ) from exc
        argument_names.add(argument)
        if location == "path":
            path_names.add(provider)
    try:
        parsed = urlsplit(candidate["server_url"])
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or candidate.get("method") != "GET"
            or not isinstance(candidate.get("path"), str)
            or not candidate["path"].startswith("/")
            or set(_PATH_TOKEN_RE.findall(candidate["path"])) != path_names
            or not re.fullmatch(
                r"[0-9a-f]{64}", str(candidate.get("source_document_sha256", ""))
            )
        ):
            raise KeyError
        if missing_json_response:
            if (
                candidate.get("response_media_type") is not None
                or candidate.get("response_schema") is not None
            ):
                raise KeyError
        else:
            response_media_type = candidate.get("response_media_type")
            if not isinstance(response_media_type, str) or not (
                response_media_type.casefold() == "application/json"
                or response_media_type.casefold().endswith("+json")
            ):
                raise KeyError
            _schema_validator(candidate.get("response_schema"), field="response_schema")
    except (KeyError, TypeError, VSDDynamicRESTError) as exc:
        raise VSDOpenAPIError("OpenAPI candidate operation is invalid") from exc
    return copy.deepcopy(candidate)


def select_openapi_candidate(
    report: Any,
    candidate_id: str | None,
    *,
    permit_missing_json_response: bool = False,
) -> dict[str, Any]:
    """Select exactly one operation from an inspection report or direct candidate."""
    if isinstance(report, dict) and report.get("format") == "vsd_openapi_operation_v1":
        if candidate_id is not None and report.get("candidate_id") != candidate_id:
            raise VSDOpenAPIError("Requested candidate ID is not present")
        return validate_openapi_candidate(
            report, permit_missing_json_response=permit_missing_json_response
        )
    candidates = report.get("candidates") if isinstance(report, dict) else None
    if not isinstance(candidates, list):
        raise VSDOpenAPIError("OpenAPI inspection report is invalid")
    matches = [
        item
        for item in candidates
        if candidate_id is None or item.get("candidate_id") == candidate_id
    ]
    if len(matches) != 1:
        raise VSDOpenAPIError("Select exactly one OpenAPI candidate by candidate ID")
    return validate_openapi_candidate(
        matches[0], permit_missing_json_response=permit_missing_json_response
    )


__all__ = [
    "VSDOpenAPIError",
    "inspect_openapi_document",
    "load_openapi_document",
    "select_openapi_candidate",
    "validate_openapi_candidate",
]
