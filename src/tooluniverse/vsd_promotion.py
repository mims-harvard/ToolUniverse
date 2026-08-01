"""Administrator-reviewed draft, verification, approval, and publication flow."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import tempfile
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import urlsplit

from jsonschema.exceptions import ValidationError

from .execute_function import ToolUniverse
from .vsd_dynamic_rest import (
    VSDDynamicRESTError,
    operation_digest,
    register_reviewed_rest_tool,
)
from .vsd_tool import _acquire_process_lock, _release_process_lock
from .vsd_openapi import VSDOpenAPIError, validate_openapi_candidate

_PROMOTION_VERSION = 1
_GENERATOR_VERSION = 1
_MAX_FILE_BYTES = 1_000_000
_MAX_PUBLISHED_TOOLS = 100
_TOOL_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{2,44}$")
_DRAFT_ID_RE = re.compile(r"^[a-z][a-z0-9_]{2,127}_[0-9a-f]{12}$")
_FIELD_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,63}$")
_DATASET_ID_RE = re.compile(r"^[a-z0-9]{4}-[a-z0-9]{4}$")
_PROMOTION_LOCK = threading.RLock()


class VSDPromotionError(ValueError):
    """Raised when an artifact cannot cross a promotion boundary."""


def _root(workspace: str | Path | None = None) -> Path:
    if workspace is not None:
        root = Path(workspace).expanduser()
    else:
        configured = os.environ.get("TOOLUNIVERSE_VSD_DIR")
        root = (
            Path(configured).expanduser()
            if configured
            else Path.home() / ".tooluniverse" / "vsd"
        )
    root.mkdir(parents=True, exist_ok=True)
    return root


@contextmanager
def _promotion_transaction(root: Path) -> Iterator[None]:
    with _PROMOTION_LOCK:
        lock_path = root / ".promotion.lock"
        with lock_path.open("a+b") as handle:
            if handle.seek(0, os.SEEK_END) == 0:
                handle.write(b"\0")
                handle.flush()
            _acquire_process_lock(handle)
            try:
                yield
            finally:
                _release_process_lock(handle)


def _atomic_write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    if len(encoded.encode("utf-8")) > _MAX_FILE_BYTES:
        raise VSDPromotionError("Promotion artifact exceeds the 1 MB limit")
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.stem}_", suffix=".json", dir=path.parent
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary_path, 0o600)
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def _read_json(path: Path) -> Any:
    try:
        if path.stat().st_size > _MAX_FILE_BYTES:
            raise VSDPromotionError(f"Artifact {path.name!r} exceeds the size limit")
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise VSDPromotionError(
            f"Required artifact {path.name!r} does not exist"
        ) from exc
    except json.JSONDecodeError as exc:
        raise VSDPromotionError(f"Artifact {path.name!r} is not valid JSON") from exc


def _canonical_digest(value: Any) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _draft_id(value: str) -> str:
    if not isinstance(value, str) or not _DRAFT_ID_RE.fullmatch(value):
        raise VSDPromotionError("draft_id is not valid")
    return value


def _tool_name(value: Any) -> str:
    if not isinstance(value, str) or not _TOOL_NAME_RE.fullmatch(value):
        raise VSDPromotionError("tool_name must be a stable identifier")
    return value


def _review_text(value: Any, *, field: str, minimum: int, maximum: int) -> str:
    text = str(value or "").strip()
    if not minimum <= len(text) <= maximum:
        raise VSDPromotionError(f"{field} must contain {minimum}-{maximum} characters")
    if any(ord(character) < 32 for character in text):
        raise VSDPromotionError(f"{field} contains control characters")
    return text


def _candidate_fields(candidate: dict[str, Any]) -> dict[str, dict[str, Any]]:
    fields = candidate.get("fields")
    if not isinstance(fields, list) or not 1 <= len(fields) <= 50:
        raise VSDPromotionError("Candidate must contain 1-50 field definitions")
    indexed: dict[str, dict[str, Any]] = {}
    for field in fields:
        if not isinstance(field, dict):
            raise VSDPromotionError("Candidate field definitions must be objects")
        name = field.get("field")
        if (
            not isinstance(name, str)
            or not _FIELD_RE.fullmatch(name)
            or name in indexed
        ):
            raise VSDPromotionError("Candidate field names must be unique identifiers")
        json_type = field.get("json_type")
        if json_type not in {"boolean", "number", "object", "string"}:
            raise VSDPromotionError(f"Candidate field {name!r} has an unsupported type")
        indexed[name] = field
    return indexed


def _validated_candidate(
    candidate: Any,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    if not isinstance(candidate, dict):
        raise VSDPromotionError("candidate must be an object")
    if (
        candidate.get("approval_state") != "unreviewed_candidate"
        or candidate.get("execution_allowed") is not False
        or candidate.get("metadata_trust") != "untrusted_catalog_metadata"
    ):
        raise VSDPromotionError("candidate did not come from the discovery boundary")
    endpoint = candidate.get("api_endpoint")
    if not isinstance(endpoint, str):
        raise VSDPromotionError("candidate API endpoint is missing")
    parsed = urlsplit(endpoint)
    dataset_id = candidate.get("dataset_id")
    catalog_domain = candidate.get("catalog_domain")
    if (
        parsed.scheme != "https"
        or parsed.query
        or parsed.fragment
        or parsed.username
        or parsed.password
        or parsed.hostname != catalog_domain
        or not isinstance(dataset_id, str)
        or not _DATASET_ID_RE.fullmatch(dataset_id)
        or parsed.path != f"/resource/{dataset_id}.json"
    ):
        raise VSDPromotionError(
            "candidate endpoint does not match its catalog identity"
        )
    candidate_id = candidate.get("candidate_id")
    expected_id = hashlib.sha256(endpoint.encode("utf-8")).hexdigest()[:16]
    if candidate_id != expected_id:
        raise VSDPromotionError("candidate ID does not match its endpoint")
    return candidate, _candidate_fields(candidate)


def _field_schema(field: dict[str, Any]) -> dict[str, Any]:
    provider_type = field.get("provider_type")
    if provider_type in {"Money", "Number"}:
        schema: dict[str, Any] = {
            "type": "string",
            "pattern": r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$",
            "maxLength": 256,
        }
    else:
        schema = {"type": field["json_type"]}
    description = str(field.get("description") or field.get("label") or "").strip()
    if description:
        schema["description"] = description[:300]
    if schema["type"] == "string":
        schema.setdefault("maxLength", 500)
    return schema


def build_socrata_tool_config(
    candidate: dict[str, Any],
    *,
    tool_name: str,
    description: str,
    filter_fields: list[str],
    return_fields: list[str],
    max_records: int = 25,
) -> dict[str, Any]:
    """Generate one narrow, read-only draft from a discovered Socrata dataset."""
    candidate, fields = _validated_candidate(candidate)
    name = _tool_name(tool_name)
    reviewed_description = _review_text(
        description, field="description", minimum=20, maximum=1000
    )
    if (
        not isinstance(filter_fields, list)
        or not 1 <= len(filter_fields) <= 8
        or len(filter_fields) != len(set(filter_fields))
    ):
        raise VSDPromotionError("filter_fields must contain 1-8 unique fields")
    if (
        not isinstance(return_fields, list)
        or not 1 <= len(return_fields) <= 20
        or len(return_fields) != len(set(return_fields))
    ):
        raise VSDPromotionError("return_fields must contain 1-20 unique fields")
    unknown = (set(filter_fields) | set(return_fields)) - set(fields)
    if unknown:
        raise VSDPromotionError(f"Unknown candidate fields: {sorted(unknown)!r}")
    non_scalar_filters = [
        field for field in filter_fields if fields[field]["json_type"] == "object"
    ]
    if non_scalar_filters:
        raise VSDPromotionError(
            f"Object-valued fields cannot be direct filters: {non_scalar_filters!r}"
        )
    if (
        isinstance(max_records, bool)
        or not isinstance(max_records, int)
        or not 1 <= max_records <= 100
    ):
        raise VSDPromotionError("max_records must be an integer between 1 and 100")

    properties = {field: _field_schema(fields[field]) for field in filter_fields}
    response_properties = {
        field: _field_schema(fields[field]) for field in return_fields
    }
    return {
        "name": name,
        "type": "VSDDynamicRESTTool",
        "description": reviewed_description,
        "category": "special_tools",
        "cacheable": False,
        "mcp_annotations": {"readOnlyHint": True, "destructiveHint": False},
        "parameter": {
            "type": "object",
            "properties": properties,
            "required": list(filter_fields),
            "additionalProperties": False,
        },
        "return_schema": {
            "type": "object",
            "properties": {
                "result": {"type": "array"},
                "provenance": {"type": "object"},
            },
            "required": ["result", "provenance"],
            "additionalProperties": False,
        },
        "vsd_operation": {
            "version": 1,
            "method": "GET",
            "endpoint": candidate["api_endpoint"],
            "path_arguments": {},
            "query_arguments": {field: field for field in filter_fields},
            "fixed_query": {
                "$limit": max_records,
                "$select": ",".join(return_fields),
            },
            "timeout_seconds": 20,
            "auth": {"type": "none"},
            "response_schema": {
                "type": "array",
                "maxItems": max_records,
                "items": {
                    "type": "object",
                    "properties": response_properties,
                    "additionalProperties": False,
                },
            },
        },
        "vsd_promotion": {
            "generator_version": _GENERATOR_VERSION,
            "candidate_id": candidate["candidate_id"],
            "catalog_domain": candidate["catalog_domain"],
            "dataset_id": candidate["dataset_id"],
            "dataset_updated_at": candidate.get("updated_at"),
            "filter_fields": list(filter_fields),
            "return_fields": list(return_fields),
            "max_records": max_records,
        },
    }


def create_draft(
    candidate: dict[str, Any],
    *,
    tool_name: str,
    description: str,
    filter_fields: list[str],
    return_fields: list[str],
    max_records: int = 25,
    workspace: str | Path | None = None,
) -> dict[str, Any]:
    """Create a content-addressed draft without making it executable."""
    config = build_socrata_tool_config(
        candidate,
        tool_name=tool_name,
        description=description,
        filter_fields=filter_fields,
        return_fields=return_fields,
        max_records=max_records,
    )
    return _create_draft_from_config(config, workspace=workspace)


def _create_draft_from_config(
    config: dict[str, Any], *, workspace: str | Path | None = None
) -> dict[str, Any]:
    """Persist one already-validated generated configuration as an inert draft."""
    digest = operation_digest(config)
    slug = re.sub(r"[^a-z0-9]+", "_", config["name"].casefold()).strip("_")
    draft_id = f"{slug}_{digest[:12]}"
    record_body = {
        "version": _PROMOTION_VERSION,
        "draft_id": draft_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "operation_sha256": digest,
        "state": "draft",
        "config": config,
    }
    record = {**record_body, "draft_sha256": _canonical_digest(record_body)}
    root = _root(workspace)
    path = root / "drafts" / f"{draft_id}.json"
    with _promotion_transaction(root):
        if path.exists():
            existing = _read_json(path)
            if (
                existing.get("operation_sha256") != digest
                or existing.get("config") != config
            ):
                raise VSDPromotionError(
                    "Existing draft does not match generated content"
                )
            return existing
        _atomic_write_json(path, record)
    return record


def _hoist_schema_definitions(
    schema: dict[str, Any], definitions: dict[str, Any]
) -> dict[str, Any]:
    normalized = copy.deepcopy(schema)
    nested = normalized.pop("$defs", {})
    if not isinstance(nested, dict):
        raise VSDPromotionError("OpenAPI schema definitions must be an object")
    for name, definition in nested.items():
        existing = definitions.get(name)
        if existing is not None and existing != definition:
            raise VSDPromotionError(
                f"OpenAPI schema definition {name!r} is inconsistent"
            )
        definitions[name] = definition
    return normalized


def build_openapi_tool_config(
    candidate: dict[str, Any],
    *,
    tool_name: str,
    description: str,
    include_parameters: list[str] | None = None,
    fixed_query: dict[str, Any] | None = None,
    timeout_seconds: int | float = 20,
) -> dict[str, Any]:
    """Generate one narrow read-only tool from an inspected OpenAPI operation."""
    try:
        reviewed = validate_openapi_candidate(candidate)
    except VSDOpenAPIError as exc:
        raise VSDPromotionError(str(exc)) from exc
    name = _tool_name(tool_name)
    reviewed_description = _review_text(
        description, field="description", minimum=20, maximum=1000
    )
    parameters = reviewed.get("parameters")
    if not isinstance(parameters, list):
        raise VSDPromotionError("OpenAPI candidate parameters are invalid")
    indexed = {
        parameter.get("argument_name"): parameter
        for parameter in parameters
        if isinstance(parameter, dict)
        and isinstance(parameter.get("argument_name"), str)
    }
    if len(indexed) != len(parameters):
        raise VSDPromotionError("OpenAPI candidate argument names must be unique")
    required_names = {
        parameter["argument_name"]
        for parameter in parameters
        if parameter.get("required") is True
    }
    if include_parameters is None:
        selected_names = set(required_names)
    elif (
        not isinstance(include_parameters, list)
        or len(include_parameters) != len(set(include_parameters))
        or any(not isinstance(item, str) for item in include_parameters)
    ):
        raise VSDPromotionError("include_parameters must contain unique names")
    else:
        selected_names = set(include_parameters)
    unknown = selected_names - set(indexed)
    if unknown:
        raise VSDPromotionError(f"Unknown OpenAPI parameters: {sorted(unknown)!r}")

    fixed = {} if fixed_query is None else copy.deepcopy(fixed_query)
    if not isinstance(fixed, dict):
        raise VSDPromotionError("fixed_query must be an object")
    provider_index = {
        parameter["provider_name"]: parameter
        for parameter in parameters
        if parameter.get("location") == "query"
    }
    unknown_fixed = set(fixed) - set(provider_index)
    if unknown_fixed:
        raise VSDPromotionError(
            f"Unknown fixed OpenAPI query parameters: {sorted(unknown_fixed)!r}"
        )
    for provider_name, value in fixed.items():
        parameter = provider_index[provider_name]
        if parameter["argument_name"] in selected_names:
            raise VSDPromotionError(
                f"OpenAPI query parameter {provider_name!r} cannot be fixed and exposed"
            )
        try:
            from .vsd_dynamic_rest import _schema_validator

            _schema_validator(
                parameter["schema"], field=f"fixed query {provider_name}"
            ).validate(value)
        except (VSDDynamicRESTError, ValidationError) as exc:
            raise VSDPromotionError(
                f"Fixed OpenAPI query parameter {provider_name!r} is invalid"
            ) from exc
    unsatisfied = {
        parameter["argument_name"]
        for parameter in parameters
        if parameter.get("required") is True
        and parameter["argument_name"] not in selected_names
        and not (
            parameter.get("location") == "query"
            and parameter.get("provider_name") in fixed
        )
    }
    if unsatisfied:
        raise VSDPromotionError(
            f"Required OpenAPI parameters are not supplied: {sorted(unsatisfied)!r}"
        )
    if (
        isinstance(timeout_seconds, bool)
        or not isinstance(timeout_seconds, (int, float))
        or not 1 <= timeout_seconds <= 60
    ):
        raise VSDPromotionError("timeout_seconds must be between 1 and 60")

    input_definitions: dict[str, Any] = {}
    properties: dict[str, Any] = {}
    path_arguments: dict[str, str] = {}
    query_arguments: dict[str, str] = {}
    query_serialization: dict[str, dict[str, Any]] = {}
    for parameter in parameters:
        argument = parameter["argument_name"]
        if argument not in selected_names:
            continue
        schema = _hoist_schema_definitions(parameter["schema"], input_definitions)
        if parameter.get("description") and "description" not in schema:
            schema["description"] = parameter["description"]
        properties[argument] = schema
        if parameter["location"] == "path":
            path_arguments[argument] = parameter["provider_name"]
        else:
            query_arguments[argument] = parameter["provider_name"]
            query_serialization[argument] = {
                "style": parameter["style"],
                "explode": parameter["explode"],
            }

    input_schema: dict[str, Any] = {
        "type": "object",
        "properties": properties,
        "required": sorted(required_names & selected_names),
        "additionalProperties": False,
    }
    if input_definitions:
        input_schema["$defs"] = input_definitions

    response_schema = copy.deepcopy(reviewed["response_schema"])
    return_definitions = response_schema.pop("$defs", {})
    return_schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "result": response_schema,
            "provenance": {"type": "object"},
        },
        "required": ["result", "provenance"],
        "additionalProperties": False,
    }
    if return_definitions:
        return_schema["$defs"] = return_definitions
    endpoint = reviewed["server_url"] + "/" + reviewed["path"].lstrip("/")
    return {
        "name": name,
        "type": "VSDDynamicRESTTool",
        "description": reviewed_description,
        "category": "special_tools",
        "cacheable": False,
        "mcp_annotations": {"readOnlyHint": True, "destructiveHint": False},
        "parameter": input_schema,
        "return_schema": return_schema,
        "vsd_operation": {
            "version": 1,
            "method": "GET",
            "endpoint": endpoint,
            "path_arguments": path_arguments,
            "query_arguments": query_arguments,
            "query_serialization": query_serialization,
            "fixed_query": fixed,
            "timeout_seconds": timeout_seconds,
            "auth": {"type": "none"},
            "response_schema": reviewed["response_schema"],
        },
        "vsd_promotion": {
            "generator_version": _GENERATOR_VERSION,
            "source_type": "openapi",
            "candidate_id": reviewed["candidate_id"],
            "candidate_sha256": reviewed["candidate_sha256"],
            "source_document_sha256": reviewed["source_document_sha256"],
            "openapi_version": reviewed["openapi_version"],
            "api_title": reviewed["api_title"],
            "api_version": reviewed["api_version"],
            "operation_id": reviewed["operation_id"],
            "method": reviewed["method"],
            "path": reviewed["path"],
            "response_media_type": reviewed["response_media_type"],
            "included_parameters": sorted(selected_names),
            "fixed_query": fixed,
        },
    }


def create_openapi_draft(
    candidate: dict[str, Any],
    *,
    tool_name: str,
    description: str,
    include_parameters: list[str] | None = None,
    fixed_query: dict[str, Any] | None = None,
    timeout_seconds: int | float = 20,
    workspace: str | Path | None = None,
) -> dict[str, Any]:
    """Create an inert, content-addressed draft from one OpenAPI candidate."""
    config = build_openapi_tool_config(
        candidate,
        tool_name=tool_name,
        description=description,
        include_parameters=include_parameters,
        fixed_query=fixed_query,
        timeout_seconds=timeout_seconds,
    )
    return _create_draft_from_config(config, workspace=workspace)


def _load_draft(root: Path, draft_id: str) -> dict[str, Any]:
    record = _read_json(root / "drafts" / f"{_draft_id(draft_id)}.json")
    if (
        not isinstance(record, dict)
        or record.get("version") != _PROMOTION_VERSION
        or record.get("draft_id") != draft_id
        or not isinstance(record.get("config"), dict)
    ):
        raise VSDPromotionError("Draft artifact has an unsupported structure")
    try:
        digest = operation_digest(record["config"])
    except VSDDynamicRESTError as exc:
        raise VSDPromotionError("Draft operation contract is invalid") from exc
    if record.get("operation_sha256") != digest:
        raise VSDPromotionError("Draft operation digest does not match its content")
    body = {key: value for key, value in record.items() if key != "draft_sha256"}
    if record.get("draft_sha256") != _canonical_digest(body):
        raise VSDPromotionError("Draft artifact digest does not match its content")
    return record


def _validated_cases(cases: Any) -> list[dict[str, Any]]:
    if not isinstance(cases, list) or not 3 <= len(cases) <= 20:
        raise VSDPromotionError("Verification requires 3-20 cases")
    validated = []
    for index, case in enumerate(cases):
        if not isinstance(case, dict) or not isinstance(case.get("arguments"), dict):
            raise VSDPromotionError(f"Verification case {index} requires arguments")
        expect = case.get("expect")
        if not isinstance(expect, dict):
            raise VSDPromotionError(f"Verification case {index} requires expectations")
        result_type = expect.get("result_type", "array")
        minimum = expect.get("min_items") if result_type == "array" else None
        maximum = expect.get("max_items") if result_type == "array" else None
        fields = expect.get("required_fields")
        equals = expect.get("equals", {})
        required_paths = expect.get("required_paths", [])
        equals_paths = expect.get("equals_paths", {})
        if (
            result_type not in {"array", "object"}
            or (
                result_type == "array"
                and (
                    isinstance(minimum, bool)
                    or not isinstance(minimum, int)
                    or minimum < 0
                    or isinstance(maximum, bool)
                    or not isinstance(maximum, int)
                    or maximum < minimum
                    or maximum > 100
                )
            )
            or (
                result_type == "object"
                and ("min_items" in expect or "max_items" in expect)
            )
            or not isinstance(fields, list)
            or (not fields and not required_paths)
            or any(
                not isinstance(field, str) or not _FIELD_RE.fullmatch(field)
                for field in fields
            )
            or not isinstance(equals, dict)
            or any(
                not isinstance(field, str) or not _FIELD_RE.fullmatch(field)
                for field in equals
            )
            or not isinstance(required_paths, list)
            or any(not _valid_json_pointer(path) for path in required_paths)
            or len(required_paths) != len(set(required_paths))
            or not isinstance(equals_paths, dict)
            or any(not _valid_json_pointer(path) for path in equals_paths)
        ):
            raise VSDPromotionError(
                f"Verification case {index} has invalid expectations"
            )
        try:
            encoded_expectations = json.dumps(
                {"equals": equals, "equals_paths": equals_paths},
                allow_nan=False,
                ensure_ascii=True,
            )
        except (TypeError, ValueError) as exc:
            raise VSDPromotionError(
                f"Verification case {index} expectations must be finite JSON"
            ) from exc
        if len(encoded_expectations.encode("utf-8")) > 16_384:
            raise VSDPromotionError(
                f"Verification case {index} expectations exceed 16 KiB"
            )
        validated.append(
            {
                "arguments": dict(case["arguments"]),
                "expect": {
                    "result_type": result_type,
                    "min_items": minimum,
                    "max_items": maximum,
                    "required_fields": list(fields),
                    "equals": dict(equals),
                    "required_paths": list(required_paths),
                    "equals_paths": dict(equals_paths),
                },
            }
        )
    return validated


_POINTER_MISSING = object()


def _valid_json_pointer(value: Any) -> bool:
    if not isinstance(value, str) or not value.startswith("/") or len(value) > 512:
        return False
    if any(ord(character) < 32 for character in value):
        return False
    return all(not re.search(r"~(?:[^01]|$)", token) for token in value.split("/")[1:])


def _json_pointer_value(document: Any, pointer: str) -> Any:
    current = document
    for raw_token in pointer.split("/")[1:]:
        token = raw_token.replace("~1", "/").replace("~0", "~")
        if isinstance(current, dict):
            if token not in current:
                return _POINTER_MISSING
            current = current[token]
        elif isinstance(current, list) and token.isdigit():
            index = int(token)
            if index >= len(current):
                return _POINTER_MISSING
            current = current[index]
        else:
            return _POINTER_MISSING
    return current


def verify_draft(
    draft_id: str,
    cases: list[dict[str, Any]],
    *,
    workspace: str | Path | None = None,
) -> dict[str, Any]:
    """Execute a draft in an isolated verifier and persist bounded evidence."""
    root = _root(workspace)
    with _promotion_transaction(root):
        draft = _load_draft(root, draft_id)
    verified_cases = _validated_cases(cases)
    tooluniverse = ToolUniverse()
    try:
        name = register_reviewed_rest_tool(tooluniverse, draft["config"])
        results = []
        for index, case in enumerate(verified_cases):
            response = tooluniverse.run_one_function(
                {"name": name, "arguments": case["arguments"]}, use_cache=False
            )
            if not isinstance(response, dict) or response.get("status") != "success":
                raise VSDPromotionError(
                    f"Verification case {index} did not execute successfully: {response!r}"
                )
            envelope = response.get("data")
            result = envelope.get("result") if isinstance(envelope, dict) else None
            provenance = (
                envelope.get("provenance") if isinstance(envelope, dict) else None
            )
            expectation = case["expect"]
            result_type = expectation["result_type"]
            if (
                (result_type == "array" and not isinstance(result, list))
                or (result_type == "object" and not isinstance(result, dict))
                or not isinstance(provenance, dict)
            ):
                raise VSDPromotionError(
                    f"Verification case {index} returned an invalid evidence envelope"
                )
            if (
                provenance.get("operation_sha256") != draft["operation_sha256"]
                or provenance.get("http_status") != 200
                or provenance.get("redirects") != 0
                or not re.fullmatch(
                    r"[0-9a-f]{64}", str(provenance.get("payload_sha256", ""))
                )
            ):
                raise VSDPromotionError(
                    f"Verification case {index} returned invalid provenance"
                )
            rows = result if result_type == "array" else [result]
            if result_type == "array" and not (
                expectation["min_items"] <= len(rows) <= expectation["max_items"]
            ):
                raise VSDPromotionError(
                    f"Verification case {index} returned {len(rows)} rows outside "
                    f"{expectation['min_items']}..{expectation['max_items']}"
                )
            for row_index, row in enumerate(rows):
                if not isinstance(row, dict):
                    raise VSDPromotionError(
                        f"Verification case {index} row {row_index} is not an object"
                    )
                missing = [
                    field
                    for field in expectation["required_fields"]
                    if field not in row or row[field] is None
                ]
                if missing:
                    raise VSDPromotionError(
                        f"Verification case {index} row {row_index} lacks values for {missing!r}"
                    )
                mismatched = {
                    field: row.get(field)
                    for field, expected in expectation["equals"].items()
                    if row.get(field) != expected
                }
                if mismatched:
                    raise VSDPromotionError(
                        f"Verification case {index} row {row_index} failed equality assertions"
                    )
                missing_paths = [
                    pointer
                    for pointer in expectation["required_paths"]
                    if _json_pointer_value(row, pointer) is _POINTER_MISSING
                    or _json_pointer_value(row, pointer) is None
                ]
                if missing_paths:
                    raise VSDPromotionError(
                        f"Verification case {index} row {row_index} lacks values "
                        f"for JSON pointers {missing_paths!r}"
                    )
                mismatched_paths = {
                    pointer: _json_pointer_value(row, pointer)
                    for pointer, expected in expectation["equals_paths"].items()
                    if _json_pointer_value(row, pointer) != expected
                }
                if mismatched_paths:
                    raise VSDPromotionError(
                        f"Verification case {index} row {row_index} failed JSON "
                        "pointer equality assertions"
                    )
            results.append(
                {
                    "case_index": index,
                    "arguments": case["arguments"],
                    "expect": expectation,
                    "result_type": result_type,
                    "row_count": len(rows) if result_type == "array" else None,
                    "observed_fields": sorted(
                        {
                            field
                            for row in rows
                            if isinstance(row, dict)
                            for field in row
                        }
                    ),
                    "payload_sha256": provenance.get("payload_sha256"),
                    "operation_sha256": provenance.get("operation_sha256"),
                    "retrieved_at": provenance.get("retrieved_at"),
                    "http_status": provenance.get("http_status"),
                    "redirects": provenance.get("redirects"),
                }
            )
    finally:
        tooluniverse.close()

    evidence_body = {
        "version": _PROMOTION_VERSION,
        "draft_id": draft_id,
        "tool_name": draft["config"]["name"],
        "draft_sha256": draft["draft_sha256"],
        "operation_sha256": draft["operation_sha256"],
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "case_count": len(results),
        "all_cases_passed": True,
        "cases": results,
    }
    evidence = {
        **evidence_body,
        "verification_sha256": _canonical_digest(evidence_body),
    }
    with _promotion_transaction(root):
        current = _load_draft(root, draft_id)
        if current["operation_sha256"] != evidence["operation_sha256"]:
            raise VSDPromotionError("Draft changed during verification")
        _atomic_write_json(root / "evidence" / f"{draft_id}.json", evidence)
    return evidence


def _load_evidence(root: Path, draft: dict[str, Any]) -> dict[str, Any]:
    evidence = _read_json(root / "evidence" / f"{draft['draft_id']}.json")
    if (
        not isinstance(evidence, dict)
        or evidence.get("operation_sha256") != draft["operation_sha256"]
        or evidence.get("draft_sha256") != draft["draft_sha256"]
        or evidence.get("all_cases_passed") is not True
        or not isinstance(evidence.get("cases"), list)
        or evidence.get("case_count") != len(evidence["cases"])
        or evidence["case_count"] < 3
    ):
        raise VSDPromotionError("Verification evidence does not match the draft")
    body = {
        key: value for key, value in evidence.items() if key != "verification_sha256"
    }
    if evidence.get("verification_sha256") != _canonical_digest(body):
        raise VSDPromotionError(
            "Verification evidence digest does not match its content"
        )
    return evidence


def approve_draft(
    draft_id: str,
    *,
    reviewed_by: str,
    decision_note: str,
    workspace: str | Path | None = None,
) -> dict[str, Any]:
    """Record explicit administrative approval of exact draft and evidence hashes."""
    reviewer = _review_text(reviewed_by, field="reviewed_by", minimum=2, maximum=100)
    note = _review_text(decision_note, field="decision_note", minimum=20, maximum=1000)
    root = _root(workspace)
    with _promotion_transaction(root):
        draft = _load_draft(root, draft_id)
        evidence = _load_evidence(root, draft)
        approval_body = {
            "version": _PROMOTION_VERSION,
            "draft_id": draft_id,
            "tool_name": draft["config"]["name"],
            "decision": "approved",
            "reviewed_by": reviewer,
            "decision_note": note,
            "approved_at": datetime.now(timezone.utc).isoformat(),
            "draft_sha256": draft["draft_sha256"],
            "operation_sha256": draft["operation_sha256"],
            "verification_sha256": evidence["verification_sha256"],
        }
        approval = {
            **approval_body,
            "approval_sha256": _canonical_digest(approval_body),
        }
        _atomic_write_json(root / "approvals" / f"{draft_id}.json", approval)
    return approval


def _load_approval(
    root: Path, draft: dict[str, Any], evidence: dict[str, Any]
) -> dict[str, Any]:
    approval = _read_json(root / "approvals" / f"{draft['draft_id']}.json")
    if (
        not isinstance(approval, dict)
        or approval.get("decision") != "approved"
        or approval.get("operation_sha256") != draft["operation_sha256"]
        or approval.get("draft_sha256") != draft["draft_sha256"]
        or approval.get("verification_sha256") != evidence["verification_sha256"]
    ):
        raise VSDPromotionError("Approval does not match the draft and verification")
    body = {key: value for key, value in approval.items() if key != "approval_sha256"}
    if approval.get("approval_sha256") != _canonical_digest(body):
        raise VSDPromotionError("Approval digest does not match its content")
    return approval


def publish_draft(
    draft_id: str,
    *,
    workspace: str | Path | None = None,
    replace: bool = False,
) -> dict[str, Any]:
    """Atomically publish an approved record without loading or executing it."""
    if type(replace) is not bool:
        raise VSDPromotionError("replace must be a boolean")
    root = _root(workspace)
    with _promotion_transaction(root):
        draft = _load_draft(root, draft_id)
        evidence = _load_evidence(root, draft)
        approval = _load_approval(root, draft, evidence)
        tool_name = _tool_name(draft["config"]["name"])
        published_body = {
            "version": _PROMOTION_VERSION,
            "tool_name": tool_name,
            "draft_id": draft_id,
            "published_at": datetime.now(timezone.utc).isoformat(),
            "draft_sha256": draft["draft_sha256"],
            "operation_sha256": draft["operation_sha256"],
            "verification_sha256": evidence["verification_sha256"],
            "approval_sha256": approval["approval_sha256"],
            "reviewed_by": approval["reviewed_by"],
            "decision_note": approval["decision_note"],
            "config": draft["config"],
        }
        published = {
            **published_body,
            "publication_sha256": _canonical_digest(published_body),
        }
        path = root / "approved" / f"{tool_name}.json"
        if path.exists() and not replace:
            raise VSDPromotionError(
                f"Published tool {tool_name!r} already exists; set replace=true explicitly"
            )
        if path.exists():
            existing = _read_json(path)
            if existing.get("tool_name") != tool_name:
                raise VSDPromotionError("Published filename collides with another tool")
        _atomic_write_json(path, published)
    return published


def _validated_publication(record: Any) -> dict[str, Any]:
    if not isinstance(record, dict) or record.get("version") != _PROMOTION_VERSION:
        raise VSDPromotionError("Published record has an unsupported structure")
    tool_name = _tool_name(record.get("tool_name"))
    _draft_id(record.get("draft_id"))
    for field in (
        "operation_sha256",
        "draft_sha256",
        "verification_sha256",
        "approval_sha256",
        "publication_sha256",
    ):
        if not re.fullmatch(r"[0-9a-f]{64}", str(record.get(field, ""))):
            raise VSDPromotionError(f"Published {field} is invalid")
    config = record.get("config")
    if not isinstance(config, dict) or config.get("name") != tool_name:
        raise VSDPromotionError("Published tool name does not match its configuration")
    try:
        digest = operation_digest(config)
    except VSDDynamicRESTError as exc:
        raise VSDPromotionError("Published operation contract is invalid") from exc
    if digest != record.get("operation_sha256"):
        raise VSDPromotionError("Published operation digest does not match")
    body = {key: value for key, value in record.items() if key != "publication_sha256"}
    if record.get("publication_sha256") != _canonical_digest(body):
        raise VSDPromotionError("Publication digest does not match its content")
    return record


def load_published_tools(
    tooluniverse,
    *,
    workspace: str | Path | None = None,
) -> list[str]:
    """Explicitly load valid published records into one ToolUniverse instance."""
    root = _root(workspace)
    approved = root / "approved"
    paths = sorted(approved.glob("*.json")) if approved.exists() else []
    if len(paths) > _MAX_PUBLISHED_TOOLS:
        raise VSDPromotionError("Approved tool count exceeds the configured limit")
    records = [_validated_publication(_read_json(path)) for path in paths]
    names = [record["tool_name"] for record in records]
    if len({name.casefold() for name in names}) != len(names):
        raise VSDPromotionError(
            "Published tool names contain a case-insensitive collision"
        )
    for name in names:
        if name in tooluniverse.all_tool_dict:
            raise VSDPromotionError(
                f"Published tool {name!r} would replace a loaded tool"
            )
    loaded: list[str] = []
    for record in records:
        name = record["tool_name"]
        register_reviewed_rest_tool(tooluniverse, record["config"])
        loaded.append(name)
    return loaded


def list_promotion_state(
    *, workspace: str | Path | None = None
) -> dict[str, list[str]]:
    """List artifact identifiers without returning host filesystem paths."""
    root = _root(workspace)
    return {
        directory: sorted(path.stem for path in (root / directory).glob("*.json"))
        if (root / directory).exists()
        else []
        for directory in ("drafts", "evidence", "approvals", "approved")
    }


__all__ = [
    "VSDPromotionError",
    "approve_draft",
    "build_openapi_tool_config",
    "build_socrata_tool_config",
    "create_draft",
    "create_openapi_draft",
    "list_promotion_state",
    "load_published_tools",
    "publish_draft",
    "verify_draft",
]
