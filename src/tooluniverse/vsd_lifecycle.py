"""Local drift assessment and explicit lifecycle controls for published VSD tools."""

from __future__ import annotations

import copy
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .vsd_dynamic_rest import VSDDynamicRESTError, _validated_operation_config
from .vsd_openapi import VSDOpenAPIError, inspect_openapi_document
from .vsd_promotion import (
    VSDPromotionError,
    _atomic_write_json,
    _canonical_digest,
    _promotion_transaction,
    _read_json,
    _root,
    _tool_name,
    _validated_publication,
    build_openapi_tool_config,
)

_ASSESSMENT_FORMAT = "vsd_openapi_drift_assessment_v1"
_LIFECYCLE_FORMAT = "vsd_publication_lifecycle_event_v1"
_LIFECYCLE_ANCHOR_FORMAT = "vsd_publication_lifecycle_anchor_v1"
_LIFECYCLE_STATE_FORMAT = "vsd_publication_lifecycle_state_v1"
_VERSION = 1
_MAX_ASSESSMENTS = 1000
_MAX_EVENTS = 1000
_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_ANNOTATION_KEYS = {
    "$comment",
    "default",
    "deprecated",
    "description",
    "examples",
    "readOnly",
    "title",
    "writeOnly",
}
_SCHEMA_MAP_KEYS = {
    "$defs",
    "definitions",
    "dependentSchemas",
    "patternProperties",
    "properties",
}
_SCHEMA_LIST_KEYS = {"allOf", "anyOf", "oneOf", "prefixItems"}
_SCHEMA_VALUE_KEYS = {
    "additionalProperties",
    "contains",
    "contentSchema",
    "else",
    "if",
    "items",
    "not",
    "propertyNames",
    "then",
    "unevaluatedItems",
    "unevaluatedProperties",
}
_STATES = {"active", "retired", "suspended"}
_ALLOWED_TRANSITIONS = {
    "active": {"retired", "suspended"},
    "suspended": {"active", "retired"},
    "retired": set(),
}


class VSDLifecycleError(VSDPromotionError):
    """Raised when drift evidence or a publication lifecycle record is invalid."""


def _review_text(value: Any, *, field: str, minimum: int, maximum: int) -> str:
    text = str(value or "").strip()
    if not minimum <= len(text) <= maximum:
        raise VSDLifecycleError(f"{field} must contain {minimum}-{maximum} characters")
    if any(ord(character) < 32 for character in text):
        raise VSDLifecycleError(f"{field} contains control characters")
    return text


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_publication(root: Path, tool_name: str) -> dict[str, Any]:
    name = _tool_name(tool_name)
    return _validated_publication(_read_json(root / "approved" / f"{name}.json"))


def _validation_view(value: Any) -> Any:
    if not isinstance(value, dict):
        return copy.deepcopy(value)
    result: dict[str, Any] = {}
    for key, item in value.items():
        if key in _ANNOTATION_KEYS:
            continue
        if key in _SCHEMA_MAP_KEYS and isinstance(item, dict):
            result[key] = {
                name: _validation_view(schema) for name, schema in item.items()
            }
        elif key in _SCHEMA_LIST_KEYS and isinstance(item, list):
            result[key] = [_validation_view(schema) for schema in item]
        elif key in _SCHEMA_VALUE_KEYS and isinstance(item, dict):
            result[key] = _validation_view(item)
        else:
            result[key] = copy.deepcopy(item)
    return result


def _execution_contract(config: dict[str, Any]) -> dict[str, Any]:
    try:
        normalized = _validated_operation_config(config)
    except VSDDynamicRESTError as exc:
        raise VSDLifecycleError("Published execution contract is invalid") from exc
    operation = normalized["vsd_operation"]
    return {
        "method": operation["method"],
        "endpoint": operation["endpoint"],
        "path_arguments": operation.get("path_arguments", {}),
        "query_arguments": operation.get("query_arguments", {}),
        "query_serialization": operation.get("query_serialization", {}),
        "fixed_query": operation.get("fixed_query", {}),
        "auth": operation["auth"],
        "input_validation": _validation_view(normalized["parameter"]),
        "response_validation": _validation_view(operation["response_schema"]),
    }


def _contract_summary(config: dict[str, Any]) -> dict[str, Any]:
    contract = _execution_contract(config)
    return {
        "execution_contract_sha256": _canonical_digest(contract),
        "component_sha256": {
            key: _canonical_digest(value) for key, value in sorted(contract.items())
        },
    }


def _credential_env(publication: dict[str, Any]) -> str | None:
    auth = publication["config"]["vsd_operation"]["auth"]
    return None if auth["type"] == "none" else auth["env_var"]


def _matching_candidate(
    report: dict[str, Any], promotion: dict[str, Any]
) -> dict[str, Any] | None:
    matches = [
        candidate
        for candidate in report["candidates"]
        if candidate.get("method") == promotion.get("method")
        and candidate.get("path") == promotion.get("path")
    ]
    if len(matches) > 1:
        raise VSDLifecycleError("OpenAPI inspection returned an ambiguous operation")
    return matches[0] if matches else None


def _assessment_body(
    publication: dict[str, Any],
    report: dict[str, Any],
    *,
    assessed_at: str,
) -> dict[str, Any]:
    config = publication["config"]
    promotion = config.get("vsd_promotion")
    if not isinstance(promotion, dict) or promotion.get("source_type") != "openapi":
        raise VSDLifecycleError(
            "Drift assessment supports only publications generated from OpenAPI"
        )
    baseline = {
        "source_document_sha256": promotion.get("source_document_sha256"),
        "candidate_sha256": promotion.get("candidate_sha256"),
        **_contract_summary(config),
    }
    candidate = _matching_candidate(report, promotion)
    observed: dict[str, Any] = {
        "source_document_sha256": report["source_document_sha256"],
        "candidate_id": None,
        "candidate_sha256": None,
        "execution_contract_sha256": None,
        "component_sha256": {},
    }
    blockers: list[str] = []
    changes: list[str] = []
    classification = "breaking"
    detail = "The reviewed operation is absent from the inspected document."

    if candidate is None:
        blockers = ["operation_missing"]
        changes = ["operation"]
    else:
        observed["candidate_id"] = candidate["candidate_id"]
        observed["candidate_sha256"] = candidate["candidate_sha256"]
        blockers = list(candidate.get("blockers", []))
        if blockers:
            changes = ["operation_policy"]
            detail = "The operation is present but no longer satisfies VSD policy."
        else:
            try:
                new_config = build_openapi_tool_config(
                    candidate,
                    tool_name=publication["tool_name"],
                    description=config["description"],
                    include_parameters=promotion.get("included_parameters"),
                    fixed_query=promotion.get("fixed_query"),
                    timeout_seconds=config["vsd_operation"]["timeout_seconds"],
                    credential_env=_credential_env(publication),
                )
                observed.update(_contract_summary(new_config))
            except VSDPromotionError as exc:
                blockers = [f"contract_reconstruction:{exc}"]
                changes = ["operation_contract"]
                detail = "The reviewed operation can no longer be reconstructed."
            else:
                baseline_components = baseline["component_sha256"]
                observed_components = observed["component_sha256"]
                changes = sorted(
                    key
                    for key in baseline_components
                    if baseline_components[key] != observed_components.get(key)
                )
                if report["source_document_sha256"] == promotion.get(
                    "source_document_sha256"
                ) and candidate["candidate_sha256"] == promotion.get(
                    "candidate_sha256"
                ):
                    classification = "unchanged"
                    detail = (
                        "The inspected source and reviewed operation are unchanged."
                    )
                elif not changes:
                    classification = "metadata_only"
                    detail = (
                        "The source metadata changed without changing request or "
                        "response validation behavior."
                    )
                elif set(changes) & {
                    "auth",
                    "endpoint",
                    "fixed_query",
                    "method",
                    "path_arguments",
                    "query_arguments",
                    "query_serialization",
                }:
                    classification = "breaking"
                    detail = (
                        "The provider request contract changed at a transport, "
                        "authentication, or argument-mapping boundary."
                    )
                else:
                    classification = "review_required"
                    detail = (
                        "Input or response validation changed and requires a new "
                        "draft, verification evidence, and approval."
                    )

    return {
        "format": _ASSESSMENT_FORMAT,
        "version": _VERSION,
        "assessed_at": assessed_at,
        "tool_name": publication["tool_name"],
        "publication_sha256": publication["publication_sha256"],
        "execution_allowed": False,
        "baseline": baseline,
        "observed": observed,
        "classification": classification,
        "changes": changes,
        "blockers": blockers,
        "suspension_recommended": classification in {"breaking", "review_required"},
        "detail": detail,
    }


def validate_drift_assessment(value: Any) -> dict[str, Any]:
    """Validate the content digest and safety boundary of one assessment artifact."""
    if not isinstance(value, dict):
        raise VSDLifecycleError("Drift assessment must be an object")
    expected_keys = {
        "assessment_id",
        "assessment_sha256",
        "assessed_at",
        "baseline",
        "blockers",
        "changes",
        "classification",
        "detail",
        "execution_allowed",
        "format",
        "observed",
        "publication_sha256",
        "suspension_recommended",
        "tool_name",
        "version",
    }
    body = {
        key: item
        for key, item in value.items()
        if key not in {"assessment_id", "assessment_sha256"}
    }
    digest = _canonical_digest(body)
    if (
        value.get("format") != _ASSESSMENT_FORMAT
        or set(value) != expected_keys
        or value.get("version") != _VERSION
        or value.get("execution_allowed") is not False
        or value.get("assessment_sha256") != digest
        or value.get("assessment_id") != digest[:16]
        or value.get("classification")
        not in {"breaking", "metadata_only", "review_required", "unchanged"}
        or type(value.get("suspension_recommended")) is not bool
        or not isinstance(value.get("changes"), list)
        or not isinstance(value.get("blockers"), list)
        or value.get("suspension_recommended")
        != (value.get("classification") in {"breaking", "review_required"})
        or not isinstance(value.get("assessed_at"), str)
        or not isinstance(value.get("detail"), str)
        or not isinstance(value.get("baseline"), dict)
        or not isinstance(value.get("observed"), dict)
        or not _DIGEST_RE.fullmatch(str(value.get("publication_sha256", "")))
    ):
        raise VSDLifecycleError("Drift assessment is invalid or has been modified")
    _tool_name(value.get("tool_name"))
    return copy.deepcopy(value)


def assess_openapi_drift(
    tool_name: str,
    spec_file: str | Path,
    *,
    workspace: str | Path | None = None,
    server_index: int = 0,
) -> dict[str, Any]:
    """Inspect a local OpenAPI file and persist an inert drift assessment."""
    root = _root(workspace)
    publication = _load_publication(root, tool_name)
    try:
        report = inspect_openapi_document(spec_file, server_index=server_index)
    except VSDOpenAPIError as exc:
        raise VSDLifecycleError(str(exc)) from exc
    assessed_at = _timestamp()
    body = _assessment_body(publication, report, assessed_at=assessed_at)
    digest = _canonical_digest(body)
    assessment = {
        **body,
        "assessment_id": digest[:16],
        "assessment_sha256": digest,
    }
    validate_drift_assessment(assessment)
    with _promotion_transaction(root):
        current = _load_publication(root, tool_name)
        if current["publication_sha256"] != publication["publication_sha256"]:
            raise VSDLifecycleError(
                "Publication changed while the drift assessment was being created"
            )
        directory = root / "assessments" / publication["tool_name"]
        existing = sorted(directory.glob("*.json")) if directory.exists() else []
        if len(existing) >= _MAX_ASSESSMENTS:
            raise VSDLifecycleError("Assessment history reached its 1000-record limit")
        path = directory / f"{assessment['assessment_sha256']}.json"
        if path.exists():
            raise VSDLifecycleError("Drift assessment artifact already exists")
        _atomic_write_json(path, assessment)
    return assessment


def _publication_directory(root: Path, publication: dict[str, Any]) -> Path:
    return (
        root
        / "lifecycle"
        / _tool_name(publication["tool_name"])
        / publication["publication_sha256"]
    )


def _event_paths(root: Path, publication: dict[str, Any]) -> list[Path]:
    directory = _publication_directory(root, publication) / "events"
    paths = sorted(directory.glob("*.json")) if directory.exists() else []
    if len(paths) > _MAX_EVENTS:
        raise VSDLifecycleError("Lifecycle history exceeds its 1000-record limit")
    return paths


def _load_history(root: Path, publication: dict[str, Any]) -> list[dict[str, Any]]:
    history: list[dict[str, Any]] = []
    previous_sha256: str | None = None
    previous_state = "active"
    tool_name = publication["tool_name"]
    publication_sha256 = publication["publication_sha256"]
    expected_keys = {
        "assessment_sha256",
        "changed_at",
        "changed_by",
        "event_sha256",
        "format",
        "previous_event_sha256",
        "previous_state",
        "publication_sha256",
        "reason",
        "revision",
        "state",
        "tool_name",
        "version",
    }
    for revision, path in enumerate(_event_paths(root, publication), start=1):
        if path.name != f"{revision:06d}.json":
            raise VSDLifecycleError("Lifecycle revisions must be contiguous")
        event = _read_json(path)
        if not isinstance(event, dict):
            raise VSDLifecycleError("Lifecycle event must be an object")
        body = {key: value for key, value in event.items() if key != "event_sha256"}
        digest = _canonical_digest(body)
        if (
            event.get("format") != _LIFECYCLE_FORMAT
            or set(event) != expected_keys
            or event.get("version") != _VERSION
            or event.get("revision") != revision
            or event.get("tool_name") != tool_name
            or event.get("publication_sha256") != publication_sha256
            or event.get("state") not in _STATES
            or event.get("previous_event_sha256") != previous_sha256
            or event.get("event_sha256") != digest
            or event.get("previous_state") != previous_state
            or event.get("state") not in _ALLOWED_TRANSITIONS[previous_state]
            or not isinstance(event.get("changed_at"), str)
            or not isinstance(event.get("changed_by"), str)
            or not isinstance(event.get("reason"), str)
        ):
            raise VSDLifecycleError(
                f"Lifecycle event {revision} is invalid or has been modified"
            )
        assessment_sha256 = event.get("assessment_sha256")
        if assessment_sha256 is not None and not _DIGEST_RE.fullmatch(
            str(assessment_sha256)
        ):
            raise VSDLifecycleError("Lifecycle assessment reference is invalid")
        if assessment_sha256 is not None:
            _find_assessment(
                root,
                tool_name,
                assessment_sha256,
                publication_sha256,
            )
        history.append(event)
        previous_sha256 = digest
        previous_state = event["state"]
    return history


def _state_body(
    publication: dict[str, Any],
    *,
    state: str,
    revision: int,
    current_event_sha256: str | None,
    updated_at: str,
) -> dict[str, Any]:
    return {
        "format": _LIFECYCLE_STATE_FORMAT,
        "version": _VERSION,
        "anchor_id": publication["lifecycle"]["anchor_id"],
        "tool_name": publication["tool_name"],
        "publication_sha256": publication["publication_sha256"],
        "state": state,
        "revision": revision,
        "current_event_sha256": current_event_sha256,
        "updated_at": updated_at,
    }


def _write_state(
    root: Path,
    publication: dict[str, Any],
    *,
    state: str,
    revision: int,
    current_event_sha256: str | None,
    updated_at: str,
) -> dict[str, Any]:
    body = _state_body(
        publication,
        state=state,
        revision=revision,
        current_event_sha256=current_event_sha256,
        updated_at=updated_at,
    )
    record = {**body, "state_sha256": _canonical_digest(body)}
    _atomic_write_json(_publication_directory(root, publication) / "state.json", record)
    return record


def _initialize_publication_lifecycle(
    root: Path, publication: dict[str, Any]
) -> dict[str, Any]:
    """Create the state anchor required by a newly published record."""
    lifecycle = publication.get("lifecycle")
    if (
        not isinstance(lifecycle, dict)
        or lifecycle.get("format") != _LIFECYCLE_ANCHOR_FORMAT
        or not _DIGEST_RE.fullmatch(str(lifecycle.get("anchor_id", "")))
    ):
        raise VSDLifecycleError("Publication lifecycle anchor is invalid")
    path = _publication_directory(root, publication) / "state.json"
    if path.exists():
        raise VSDLifecycleError("Publication lifecycle state already exists")
    return _write_state(
        root,
        publication,
        state="active",
        revision=0,
        current_event_sha256=None,
        updated_at=publication["published_at"],
    )


def _load_managed_state(
    root: Path, publication: dict[str, Any]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    try:
        record = _read_json(_publication_directory(root, publication) / "state.json")
    except VSDPromotionError as exc:
        raise VSDLifecycleError("Publication lifecycle state is missing") from exc
    if not isinstance(record, dict):
        raise VSDLifecycleError("Publication lifecycle state must be an object")
    expected_keys = {
        "anchor_id",
        "current_event_sha256",
        "format",
        "publication_sha256",
        "revision",
        "state",
        "state_sha256",
        "tool_name",
        "updated_at",
        "version",
    }
    body = {key: value for key, value in record.items() if key != "state_sha256"}
    if (
        set(record) != expected_keys
        or record.get("format") != _LIFECYCLE_STATE_FORMAT
        or record.get("version") != _VERSION
        or record.get("anchor_id") != publication["lifecycle"]["anchor_id"]
        or record.get("tool_name") != publication["tool_name"]
        or record.get("publication_sha256") != publication["publication_sha256"]
        or record.get("state") not in _STATES
        or not isinstance(record.get("revision"), int)
        or isinstance(record.get("revision"), bool)
        or record["revision"] < 0
        or not isinstance(record.get("updated_at"), str)
        or record.get("state_sha256") != _canonical_digest(body)
    ):
        raise VSDLifecycleError("Publication lifecycle state is invalid or modified")
    current_event_sha256 = record.get("current_event_sha256")
    if current_event_sha256 is not None and not _DIGEST_RE.fullmatch(
        str(current_event_sha256)
    ):
        raise VSDLifecycleError("Publication lifecycle event pointer is invalid")
    history = _load_history(root, publication)
    expected_state = history[-1]["state"] if history else "active"
    expected_event = history[-1]["event_sha256"] if history else None
    if (
        record["revision"] != len(history)
        or record["state"] != expected_state
        or current_event_sha256 != expected_event
    ):
        raise VSDLifecycleError(
            "Publication lifecycle state does not match its event history"
        )
    return record, history


def _state_for_publication(root: Path, publication: dict[str, Any]) -> dict[str, Any]:
    if publication.get("lifecycle") is None:
        return {
            "tool_name": publication["tool_name"],
            "publication_sha256": publication["publication_sha256"],
            "state": "active",
            "revision": 0,
            "event_sha256": None,
            "assessment_sha256": None,
            "lifecycle_managed": False,
        }
    current, history = _load_managed_state(root, publication)
    event = history[-1] if history else None
    return {
        "tool_name": publication["tool_name"],
        "publication_sha256": publication["publication_sha256"],
        "state": current["state"],
        "revision": current["revision"],
        "event_sha256": current["current_event_sha256"],
        "assessment_sha256": event["assessment_sha256"] if event else None,
        "lifecycle_managed": True,
    }


def _find_assessment(
    root: Path,
    tool_name: str,
    assessment_sha256: str,
    publication_sha256: str,
) -> dict[str, Any]:
    if not _DIGEST_RE.fullmatch(str(assessment_sha256)):
        raise VSDLifecycleError(
            "assessment_sha256 must contain 64 lowercase hex digits"
        )
    path = root / "assessments" / tool_name / f"{assessment_sha256}.json"
    try:
        assessment = validate_drift_assessment(_read_json(path))
    except VSDLifecycleError:
        raise
    except VSDPromotionError as exc:
        raise VSDLifecycleError("Referenced drift assessment does not exist") from exc
    if assessment["assessment_sha256"] != assessment_sha256:
        raise VSDLifecycleError("Referenced drift assessment digest does not match")
    if (
        assessment["tool_name"] != tool_name
        or assessment["publication_sha256"] != publication_sha256
    ):
        raise VSDLifecycleError("Drift assessment does not match this publication")
    return assessment


def set_publication_state(
    tool_name: str,
    state: str,
    *,
    changed_by: str,
    reason: str,
    assessment_sha256: str | None = None,
    workspace: str | Path | None = None,
) -> dict[str, Any]:
    """Append one explicit, hash-chained lifecycle transition."""
    if state not in _STATES:
        raise VSDLifecycleError(f"state must be one of {sorted(_STATES)!r}")
    reviewer = _review_text(changed_by, field="changed_by", minimum=2, maximum=100)
    decision_reason = _review_text(reason, field="reason", minimum=20, maximum=1000)
    root = _root(workspace)
    with _promotion_transaction(root):
        publication = _load_publication(root, tool_name)
        if publication.get("lifecycle") is None:
            raise VSDLifecycleError(
                "Legacy publication must be republished before lifecycle control"
            )
        current_record, history = _load_managed_state(root, publication)
        current = {
            "state": current_record["state"],
            "event_sha256": current_record["current_event_sha256"],
        }
        if state not in _ALLOWED_TRANSITIONS[current["state"]]:
            raise VSDLifecycleError(
                f"Cannot transition publication from {current['state']!r} to {state!r}"
            )
        assessment = None
        if assessment_sha256 is not None:
            assessment = _find_assessment(
                root,
                publication["tool_name"],
                assessment_sha256,
                publication["publication_sha256"],
            )
        if state == "active" and assessment is None:
            raise VSDLifecycleError(
                "Activating a suspended publication requires a drift assessment"
            )
        if state == "active" and assessment["classification"] not in {
            "metadata_only",
            "unchanged",
        }:
            raise VSDLifecycleError(
                "Activation requires an unchanged or metadata-only assessment"
            )
        changed_at = _timestamp()
        body = {
            "format": _LIFECYCLE_FORMAT,
            "version": _VERSION,
            "revision": len(history) + 1,
            "tool_name": publication["tool_name"],
            "publication_sha256": publication["publication_sha256"],
            "previous_state": current["state"],
            "state": state,
            "changed_at": changed_at,
            "changed_by": reviewer,
            "reason": decision_reason,
            "assessment_sha256": assessment_sha256,
            "previous_event_sha256": (history[-1]["event_sha256"] if history else None),
        }
        event = {**body, "event_sha256": _canonical_digest(body)}
        path = (
            _publication_directory(root, publication)
            / "events"
            / f"{event['revision']:06d}.json"
        )
        if len(history) >= _MAX_EVENTS or path.exists():
            raise VSDLifecycleError("Lifecycle history reached its 1000-record limit")
        _atomic_write_json(path, event)
        _write_state(
            root,
            publication,
            state=state,
            revision=event["revision"],
            current_event_sha256=event["event_sha256"],
            updated_at=changed_at,
        )
    return event


def list_publication_states(
    tool_name: str | None = None, *, workspace: str | Path | None = None
) -> dict[str, Any]:
    """Return validated current lifecycle state for published tools."""
    root = _root(workspace)
    with _promotion_transaction(root):
        if tool_name is not None:
            publications = [_load_publication(root, tool_name)]
        else:
            approved = root / "approved"
            paths = sorted(approved.glob("*.json")) if approved.exists() else []
            publications = [_validated_publication(_read_json(path)) for path in paths]
        states = [
            _state_for_publication(root, publication) for publication in publications
        ]
    return {
        "format": "vsd_publication_lifecycle_status_v1",
        "execution_allowed": False,
        "tools": states,
    }


__all__ = [
    "VSDLifecycleError",
    "assess_openapi_drift",
    "list_publication_states",
    "set_publication_state",
    "validate_drift_assessment",
]
