"""Private, explicit demand aggregation for VSD capability planning.

The ledger is local-only and administrator controlled. It never transmits data,
never stores the raw capability description, and never makes candidates
executable. Export requires an explicit allowlist of demand IDs and writes a
sanitized proposal file for human review.
"""

from __future__ import annotations

import copy
import hashlib
import ipaddress
import json
import os
import re
import tempfile
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from .vsd_coverage import normalize_capability_request, resolve_capability
from .vsd_tool import _acquire_process_lock, _release_process_lock

_LEDGER_VERSION = 1
_EXPORT_VERSION = 1
_MAX_FILE_BYTES = 2_000_000
_MAX_DEMANDS = 1000
_MAX_EVENT_HASHES = 100
_MAX_REGISTRY_SNAPSHOTS = 20
_MAX_MATCHES = 5
_DEMAND_ID_RE = re.compile(r"^[0-9a-f]{16}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_SOURCE_RE = re.compile(r"^[a-z][a-z0-9_]{2,31}$")
_PUBLIC_PROVIDER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 .:_-]{2,199}$")
_EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
_URL_RE = re.compile(r"https?://", re.I)
_SECRET_RE = re.compile(
    r"(?:api[_-]?key|access[_-]?token|password|secret)\s*[:=]|\bbearer\s+\S+",
    re.I,
)
_LEDGER_LOCK = threading.RLock()
_CAPABILITY_KEYS = {
    "provider",
    "method",
    "endpoint_host",
    "endpoint_path",
    "operation_id",
    "required_inputs",
    "output_fields",
}
_PUBLIC_CAPABILITY_KEYS = {
    "provider",
    "method",
    "operation_id",
    "required_inputs",
    "output_fields",
}
_OBSERVATION_KEYS = {"exact", "partial", "missing"}
_CLASSIFICATIONS = {
    "existing_exact": "exact",
    "existing_partial": "partial",
    "missing": "missing",
}


class VSDDemandError(ValueError):
    """Raised when local demand data cannot be recorded or exported safely."""


def _root(workspace: str | Path | None = None) -> Path:
    if workspace is not None:
        root = Path(workspace).expanduser()
    else:
        configured = os.environ.get("TOOLUNIVERSE_VSD_DIR")
        base = (
            Path(configured).expanduser()
            if configured
            else Path.home() / ".tooluniverse" / "vsd"
        )
        root = base / "demand"
    root.mkdir(parents=True, exist_ok=True)
    os.chmod(root, 0o700)
    return root


def _canonical_digest(value: Any) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _with_integrity(ledger: dict[str, Any]) -> dict[str, Any]:
    body = {"version": ledger["version"], "records": ledger["records"]}
    return {**body, "integrity_sha256": _canonical_digest(body)}


def _empty_ledger() -> dict[str, Any]:
    return _with_integrity({"version": _LEDGER_VERSION, "records": {}})


@contextmanager
def _ledger_transaction(root: Path) -> Iterator[None]:
    with _LEDGER_LOCK:
        lock_path = root / ".demand.lock"
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
        raise VSDDemandError("Demand artifact exceeds the 2 MB limit")
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


def _safe_public_text(value: Any, *, field: str, minimum: int, maximum: int) -> str:
    text = str(value or "").strip()
    if not minimum <= len(text) <= maximum:
        raise VSDDemandError(f"{field} must contain {minimum}-{maximum} characters")
    if any(ord(character) < 32 for character in text):
        raise VSDDemandError(f"{field} contains control characters")
    if _URL_RE.search(text) or _EMAIL_RE.search(text) or _SECRET_RE.search(text):
        raise VSDDemandError(
            f"{field} must not contain URLs, email addresses, or credential-like data"
        )
    return text


def _public_provider(value: Any) -> str:
    provider = str(value or "").strip()
    if not provider:
        return ""
    if not _PUBLIC_PROVIDER_RE.fullmatch(provider):
        raise VSDDemandError("provider is not safe for public export")
    if (
        _URL_RE.search(provider)
        or _EMAIL_RE.search(provider)
        or _SECRET_RE.search(provider)
    ):
        raise VSDDemandError("provider is not safe for public export")
    host = provider.casefold().rstrip(".")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        address = None
    if (
        (address is not None and not address.is_global)
        or host == "localhost"
        or host.endswith((".local", ".internal", ".localhost"))
    ):
        raise VSDDemandError("provider is not safe for public export")
    return provider


def _source(value: Any) -> str:
    source = str(value or "").strip()
    if not _SOURCE_RE.fullmatch(source):
        raise VSDDemandError("source must be a stable lowercase identifier")
    return source


def _timestamp(value: str | None = None) -> str:
    if value is None:
        return datetime.now(timezone.utc).isoformat()
    if not isinstance(value, str) or len(value) > 64:
        raise VSDDemandError("observed_at must be a bounded ISO-8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise VSDDemandError("observed_at must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise VSDDemandError("observed_at must include a timezone")
    return parsed.astimezone(timezone.utc).isoformat()


def _event_hash(source: str, event_id: str | None) -> str | None:
    if event_id is None:
        return None
    if not isinstance(event_id, str) or not 1 <= len(event_id) <= 200:
        raise VSDDemandError("event_id must contain 1-200 characters")
    if any(ord(character) < 32 for character in event_id):
        raise VSDDemandError("event_id contains control characters")
    return _canonical_digest({"source": source, "event_id": event_id})


def _stored_capability(normalized: dict[str, Any]) -> dict[str, Any]:
    return {key: copy.deepcopy(normalized[key]) for key in sorted(_CAPABILITY_KEYS)}


def _normalized_request(request: dict[str, Any]) -> dict[str, Any]:
    if isinstance(request, dict) and set(request) == _CAPABILITY_KEYS | {"description"}:
        capability = _stored_capability(request)
        _validate_capability(capability)
        reconstructed = {
            "description": request["description"],
            "provider": capability["provider"],
            "method": capability["method"],
            "operation_id": capability["operation_id"],
            "required_inputs": capability["required_inputs"],
            "output_fields": capability["output_fields"],
        }
        if capability["endpoint_host"]:
            reconstructed["endpoint"] = (
                f"https://{capability['endpoint_host']}{capability['endpoint_path']}"
            )
        normalized = normalize_capability_request(reconstructed)
        if normalized != request:
            raise VSDDemandError("Normalized capability request is not canonical")
        return normalized
    return normalize_capability_request(request)


def _validate_capability(capability: Any) -> None:
    if not isinstance(capability, dict) or set(capability) != _CAPABILITY_KEYS:
        raise VSDDemandError("Demand ledger has an invalid capability record")
    reconstructed = {
        "description": "validated public capability placeholder",
        "provider": capability["provider"],
        "method": capability["method"],
        "operation_id": capability["operation_id"],
        "required_inputs": capability["required_inputs"],
        "output_fields": capability["output_fields"],
    }
    if capability["endpoint_host"]:
        reconstructed["endpoint"] = (
            f"https://{capability['endpoint_host']}{capability['endpoint_path']}"
        )
    try:
        expected = _stored_capability(normalize_capability_request(reconstructed))
    except ValueError as exc:
        raise VSDDemandError("Demand ledger has an invalid capability record") from exc
    if capability != expected:
        raise VSDDemandError("Demand ledger capability is not canonical")


def _export_capability(capability: dict[str, Any]) -> dict[str, Any]:
    _validate_capability(capability)
    return {
        "provider": _public_provider(capability["provider"]),
        "method": capability["method"],
        "operation_id": capability["operation_id"],
        "required_inputs": copy.deepcopy(capability["required_inputs"]),
        "output_fields": copy.deepcopy(capability["output_fields"]),
    }


def _validate_export_capability(capability: Any) -> None:
    if not isinstance(capability, dict) or set(capability) != _PUBLIC_CAPABILITY_KEYS:
        raise VSDDemandError("Proposal export has an invalid public capability")
    reconstructed = {
        "description": "validated public capability placeholder",
        "provider": _public_provider(capability["provider"]),
        "method": capability["method"],
        "operation_id": capability["operation_id"],
        "required_inputs": capability["required_inputs"],
        "output_fields": capability["output_fields"],
    }
    try:
        normalized = normalize_capability_request(reconstructed)
    except ValueError as exc:
        raise VSDDemandError(
            "Proposal export has an invalid public capability"
        ) from exc
    expected = {key: normalized[key] for key in sorted(_PUBLIC_CAPABILITY_KEYS)}
    if capability != expected:
        raise VSDDemandError("Proposal export capability is not canonical")


def _validate_record(demand_id: str, record: Any) -> None:
    if not _DEMAND_ID_RE.fullmatch(demand_id) or not isinstance(record, dict):
        raise VSDDemandError("Demand ledger has an invalid record")
    required = {
        "demand_id",
        "public_summary",
        "capability",
        "observation_counts",
        "total_observations",
        "source_counts",
        "first_observed_at",
        "last_observed_at",
        "registry_snapshots",
        "last_matches",
        "event_hashes",
    }
    if set(record) != required or record.get("demand_id") != demand_id:
        raise VSDDemandError("Demand ledger has an unsupported record")
    summary = _safe_public_text(
        record.get("public_summary"),
        field="public_summary",
        minimum=10,
        maximum=240,
    )
    _validate_capability(record.get("capability"))
    expected_id = _canonical_digest(
        {"public_summary": summary.casefold(), "capability": record["capability"]}
    )[:16]
    if expected_id != demand_id:
        raise VSDDemandError("Demand ID does not match its sanitized content")
    counts = record.get("observation_counts")
    if (
        not isinstance(counts, dict)
        or set(counts) != _OBSERVATION_KEYS
        or any(type(value) is not int or value < 0 for value in counts.values())
        or record.get("total_observations") != sum(counts.values())
    ):
        raise VSDDemandError("Demand ledger has invalid observation counts")
    source_counts = record.get("source_counts")
    if (
        not isinstance(source_counts, dict)
        or len(source_counts) > 20
        or any(
            not _SOURCE_RE.fullmatch(name) or type(count) is not int or count < 1
            for name, count in source_counts.items()
        )
        or sum(source_counts.values()) != record["total_observations"]
    ):
        raise VSDDemandError("Demand ledger has invalid source counts")
    first = _timestamp(record.get("first_observed_at"))
    last = _timestamp(record.get("last_observed_at"))
    if (
        first != record["first_observed_at"]
        or last != record["last_observed_at"]
        or datetime.fromisoformat(first) > datetime.fromisoformat(last)
    ):
        raise VSDDemandError("Demand ledger timestamps are not canonical")
    snapshots = record.get("registry_snapshots")
    if (
        not isinstance(snapshots, list)
        or len(snapshots) > _MAX_REGISTRY_SNAPSHOTS
        or len(snapshots) != len(set(snapshots))
        or any(
            not isinstance(value, str) or not _SHA256_RE.fullmatch(value)
            for value in snapshots
        )
    ):
        raise VSDDemandError("Demand ledger has invalid registry snapshots")
    matches = record.get("last_matches")
    if (
        not isinstance(matches, list)
        or len(matches) > _MAX_MATCHES
        or len(matches) != len(set(matches))
        or any(
            not isinstance(value, str) or not 1 <= len(value) <= 128
            for value in matches
        )
    ):
        raise VSDDemandError("Demand ledger has invalid tool matches")
    events = record.get("event_hashes")
    if (
        not isinstance(events, list)
        or len(events) > _MAX_EVENT_HASHES
        or len(events) != len(set(events))
        or any(
            not isinstance(value, str) or not _SHA256_RE.fullmatch(value)
            for value in events
        )
    ):
        raise VSDDemandError("Demand ledger has invalid event hashes")


def _load_ledger(root: Path) -> dict[str, Any]:
    path = root / "demand_ledger.json"
    if not path.exists():
        return _empty_ledger()
    try:
        if path.stat().st_size > _MAX_FILE_BYTES:
            raise VSDDemandError("Demand ledger exceeds the 2 MB limit")
        ledger = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise VSDDemandError("Demand ledger is unreadable") from exc
    if (
        not isinstance(ledger, dict)
        or set(ledger) != {"version", "records", "integrity_sha256"}
        or ledger.get("version") != _LEDGER_VERSION
        or not isinstance(ledger.get("records"), dict)
        or len(ledger["records"]) > _MAX_DEMANDS
    ):
        raise VSDDemandError("Demand ledger has an unsupported structure")
    expected = _with_integrity(ledger)
    if ledger.get("integrity_sha256") != expected["integrity_sha256"]:
        raise VSDDemandError("Demand ledger integrity digest does not match")
    for demand_id, record in ledger["records"].items():
        _validate_record(demand_id, record)
    return ledger


def _observation_from_coverage(
    request: dict[str, Any], coverage: dict[str, Any]
) -> tuple[dict[str, Any], str, str, list[str]]:
    normalized = _normalized_request(request)
    data = coverage.get("data") if isinstance(coverage, dict) else None
    if not isinstance(data, dict) or data.get("request") != normalized:
        raise VSDDemandError("Coverage result does not match the capability request")
    observation = _CLASSIFICATIONS.get(data.get("classification"))
    registry_sha256 = data.get("registry_sha256")
    matches = data.get("matches")
    if (
        observation is None
        or not isinstance(registry_sha256, str)
        or not _SHA256_RE.fullmatch(registry_sha256)
        or not isinstance(matches, list)
    ):
        raise VSDDemandError("Coverage result has an unsupported structure")
    names = []
    for match in matches[:_MAX_MATCHES]:
        name = match.get("name") if isinstance(match, dict) else None
        if not isinstance(name, str) or not 1 <= len(name) <= 128:
            raise VSDDemandError("Coverage result has an invalid match name")
        if name not in names:
            names.append(name)
    return normalized, observation, registry_sha256, names


def _prepare_observation(
    request: dict[str, Any],
    coverage: dict[str, Any],
    *,
    public_summary: str,
    source: str,
    event_id: str | None,
    observed_at: str | None,
) -> dict[str, Any]:
    summary = _safe_public_text(
        public_summary, field="public_summary", minimum=10, maximum=240
    )
    source_id = _source(source)
    timestamp = _timestamp(observed_at)
    normalized, observation, registry_sha256, matches = _observation_from_coverage(
        request, coverage
    )
    capability = _stored_capability(normalized)
    demand_id = _canonical_digest(
        {"public_summary": summary.casefold(), "capability": capability}
    )[:16]
    return {
        "demand_id": demand_id,
        "public_summary": summary,
        "capability": capability,
        "observation": observation,
        "source": source_id,
        "timestamp": timestamp,
        "registry_sha256": registry_sha256,
        "matches": matches,
        "event_hash": _event_hash(source_id, event_id),
    }


def _apply_observation(
    ledger: dict[str, Any], prepared: dict[str, Any]
) -> tuple[bool, dict[str, Any]]:
    demand_id = prepared["demand_id"]
    record = ledger["records"].get(demand_id)
    if record is None:
        if len(ledger["records"]) >= _MAX_DEMANDS:
            raise VSDDemandError("Demand ledger reached its 1000-record limit")
        record = {
            "demand_id": demand_id,
            "public_summary": prepared["public_summary"],
            "capability": prepared["capability"],
            "observation_counts": {key: 0 for key in sorted(_OBSERVATION_KEYS)},
            "total_observations": 0,
            "source_counts": {},
            "first_observed_at": prepared["timestamp"],
            "last_observed_at": prepared["timestamp"],
            "registry_snapshots": [],
            "last_matches": [],
            "event_hashes": [],
        }
        ledger["records"][demand_id] = record
    event_hash = prepared["event_hash"]
    if event_hash is not None and event_hash in record["event_hashes"]:
        return False, record
    observation = prepared["observation"]
    source = prepared["source"]
    if source not in record["source_counts"] and len(record["source_counts"]) >= 20:
        raise VSDDemandError("Demand record reached its 20-source limit")
    record["observation_counts"][observation] += 1
    record["total_observations"] += 1
    record["source_counts"][source] = record["source_counts"].get(source, 0) + 1
    observed = datetime.fromisoformat(prepared["timestamp"])
    first = datetime.fromisoformat(record["first_observed_at"])
    last = datetime.fromisoformat(record["last_observed_at"])
    record["first_observed_at"] = min(first, observed).isoformat()
    record["last_observed_at"] = max(last, observed).isoformat()
    registry_sha256 = prepared["registry_sha256"]
    if registry_sha256 not in record["registry_snapshots"]:
        record["registry_snapshots"].append(registry_sha256)
        record["registry_snapshots"] = record["registry_snapshots"][
            -_MAX_REGISTRY_SNAPSHOTS:
        ]
    record["last_matches"] = prepared["matches"]
    if event_hash is not None:
        record["event_hashes"].append(event_hash)
        record["event_hashes"] = record["event_hashes"][-_MAX_EVENT_HASHES:]
    return True, record


def record_coverage_observation(
    request: dict[str, Any],
    coverage: dict[str, Any],
    *,
    public_summary: str,
    source: str = "manual",
    event_id: str | None = None,
    observed_at: str | None = None,
    workspace: str | Path | None = None,
) -> dict[str, Any]:
    """Record one explicit local observation without persisting the raw query."""
    prepared = _prepare_observation(
        request,
        coverage,
        public_summary=public_summary,
        source=source,
        event_id=event_id,
        observed_at=observed_at,
    )
    root = _root(workspace)
    with _ledger_transaction(root):
        ledger = _load_ledger(root)
        recorded, record = _apply_observation(ledger, prepared)
        if not recorded:
            return {
                "status": "success",
                "data": {
                    "recorded": False,
                    "deduplicated": True,
                    "demand": _public_record(record),
                    "privacy": _privacy_statement(),
                },
            }
        updated = _with_integrity(ledger)
        _atomic_write_json(root / "demand_ledger.json", updated)
        return {
            "status": "success",
            "data": {
                "recorded": True,
                "deduplicated": False,
                "demand": _public_record(record),
                "ledger_sha256": updated["integrity_sha256"],
                "privacy": _privacy_statement(),
            },
        }


def observe_capability_demand(
    tooluniverse: Any,
    request: dict[str, Any],
    *,
    public_summary: str,
    source: str = "manual",
    event_id: str | None = None,
    observed_at: str | None = None,
    workspace: str | Path | None = None,
    limit: int = 5,
) -> dict[str, Any]:
    """Resolve current local coverage and explicitly record the observation."""
    coverage = resolve_capability(tooluniverse, request, limit=limit)
    return record_coverage_observation(
        request,
        coverage,
        public_summary=public_summary,
        source=source,
        event_id=event_id,
        observed_at=observed_at,
        workspace=workspace,
    )


def record_plan_demands(
    plan: dict[str, Any],
    public_summaries: dict[str, str],
    *,
    workspace: str | Path | None = None,
    source: str = "workflow_plan",
    run_id: str | None = None,
    observed_at: str | None = None,
    include_classifications: tuple[str, ...] = ("missing", "existing_partial"),
) -> dict[str, Any]:
    """Atomically record summarized tool steps from a hash-bound VSD plan."""
    data = plan.get("data") if isinstance(plan, dict) and "data" in plan else plan
    if not isinstance(data, dict):
        raise VSDDemandError("plan must be a VSD workflow plan object")
    plan_sha256 = data.get("plan_sha256")
    plan_id = data.get("plan_id")
    body = {
        key: value
        for key, value in data.items()
        if key not in {"plan_id", "plan_sha256"}
    }
    expected = _canonical_digest(body)
    if (
        not isinstance(plan_sha256, str)
        or plan_sha256 != expected
        or plan_id != expected[:16]
        or data.get("execution_allowed") is not False
        or not isinstance(data.get("registry_sha256"), str)
        or not _SHA256_RE.fullmatch(data["registry_sha256"])
    ):
        raise VSDDemandError("Plan identity or non-execution boundary is invalid")
    allowed = {"missing", "existing_partial", "existing_exact"}
    if (
        not isinstance(include_classifications, tuple)
        or not include_classifications
        or len(include_classifications) != len(set(include_classifications))
        or not set(include_classifications) <= allowed
    ):
        raise VSDDemandError("include_classifications contains unsupported values")
    if not isinstance(public_summaries, dict) or any(
        not isinstance(key, str) or not isinstance(value, str)
        for key, value in public_summaries.items()
    ):
        raise VSDDemandError("public_summaries must map step IDs to reviewed text")
    source_id = _source(source)
    timestamp = _timestamp(observed_at)
    if run_id is not None and (
        not isinstance(run_id, str)
        or not 1 <= len(run_id) <= 100
        or any(ord(character) < 32 for character in run_id)
    ):
        raise VSDDemandError("run_id must contain 1-100 printable characters")
    steps = data.get("steps")
    if not isinstance(steps, list) or not 1 <= len(steps) <= 20:
        raise VSDDemandError("Plan must contain 1-20 workflow steps")
    known_step_ids = {step.get("step_id") for step in steps if isinstance(step, dict)}
    if None in known_step_ids or set(public_summaries) - known_step_ids:
        raise VSDDemandError("public_summaries contains unknown workflow steps")
    selected = [
        step
        for step in steps
        if isinstance(step, dict)
        and step.get("fulfillment") == "tool"
        and step.get("classification") in include_classifications
    ]
    missing_summaries = sorted(
        step["step_id"] for step in selected if step["step_id"] not in public_summaries
    )
    if missing_summaries:
        raise VSDDemandError(
            f"Reviewed public summaries are required for steps: {missing_summaries!r}"
        )
    prepared = []
    for step in selected:
        classification = step["classification"]
        request = step.get("request")
        coverage = {
            "data": {
                "request": request,
                "classification": classification,
                "registry_sha256": data["registry_sha256"],
                "matches": step.get("matches"),
            }
        }
        event_id = f"{run_id or plan_id}:{step['step_id']}"
        prepared.append(
            _prepare_observation(
                request,
                coverage,
                public_summary=public_summaries[step["step_id"]],
                source=source_id,
                event_id=event_id,
                observed_at=timestamp,
            )
        )
    root = _root(workspace)
    with _ledger_transaction(root):
        ledger = _load_ledger(root)
        outcomes = [_apply_observation(ledger, item) for item in prepared]
        recorded_count = sum(recorded for recorded, _ in outcomes)
        if recorded_count:
            updated = _with_integrity(ledger)
            _atomic_write_json(root / "demand_ledger.json", updated)
        else:
            updated = ledger
    return {
        "status": "success",
        "data": {
            "plan_id": plan_id,
            "selected_step_count": len(selected),
            "recorded_count": recorded_count,
            "deduplicated_count": len(selected) - recorded_count,
            "demands": [_public_record(record) for _, record in outcomes],
            "ledger_sha256": updated["integrity_sha256"],
            "privacy": _privacy_statement(),
        },
    }


def _priority(record: dict[str, Any]) -> tuple[int, float]:
    counts = record["observation_counts"]
    score = counts["missing"] * 5 + counts["partial"] * 2
    unmet = counts["missing"] + counts["partial"]
    return score, round(unmet / record["total_observations"], 4)


def _public_record(record: dict[str, Any]) -> dict[str, Any]:
    score, unmet_rate = _priority(record)
    return {
        key: copy.deepcopy(value)
        for key, value in record.items()
        if key != "event_hashes"
    } | {"priority_score": score, "unmet_rate": unmet_rate}


def _privacy_statement() -> str:
    return (
        "The demand ledger is local and explicit. Raw query descriptions and event "
        "IDs are not stored, and nothing is transmitted automatically."
    )


def rank_demands(
    *,
    workspace: str | Path | None = None,
    minimum_observations: int = 1,
    limit: int = 100,
    include_satisfied: bool = False,
) -> dict[str, Any]:
    """Return deterministic local priority ordering without changing the ledger."""
    if (
        type(minimum_observations) is not int
        or not 1 <= minimum_observations <= 1_000_000
    ):
        raise VSDDemandError("minimum_observations must be a positive integer")
    if type(limit) is not int or not 1 <= limit <= 1000:
        raise VSDDemandError("limit must be an integer between 1 and 1000")
    if type(include_satisfied) is not bool:
        raise VSDDemandError("include_satisfied must be boolean")
    root = _root(workspace)
    with _ledger_transaction(root):
        ledger = _load_ledger(root)
    ranked = [
        _public_record(record)
        for record in ledger["records"].values()
        if record["total_observations"] >= minimum_observations
        and (
            include_satisfied
            or record["observation_counts"]["missing"] > 0
            or record["observation_counts"]["partial"] > 0
        )
    ]
    ranked.sort(
        key=lambda record: (
            -record["priority_score"],
            -record["total_observations"],
            record["public_summary"].casefold(),
            record["demand_id"],
        )
    )
    return {
        "status": "success",
        "data": {
            "ranked_demands": ranked[:limit],
            "matching_demand_count": len(ranked),
            "total_demand_count": len(ledger["records"]),
            "ledger_sha256": ledger["integrity_sha256"],
            "privacy": _privacy_statement(),
        },
    }


def export_proposals(
    demand_ids: list[str],
    output_path: str | Path,
    *,
    reviewed_by: str,
    decision_note: str,
    workspace: str | Path | None = None,
    created_at: str | None = None,
    replace: bool = False,
) -> dict[str, Any]:
    """Write an explicitly selected, sanitized proposal bundle without sending it."""
    if (
        not isinstance(demand_ids, list)
        or not 1 <= len(demand_ids) <= 100
        or len(demand_ids) != len(set(demand_ids))
        or any(
            not isinstance(value, str) or not _DEMAND_ID_RE.fullmatch(value)
            for value in demand_ids
        )
    ):
        raise VSDDemandError("demand_ids must contain 1-100 unique demand IDs")
    reviewer = _safe_public_text(
        reviewed_by, field="reviewed_by", minimum=3, maximum=100
    )
    note = _safe_public_text(
        decision_note, field="decision_note", minimum=20, maximum=500
    )
    if type(replace) is not bool:
        raise VSDDemandError("replace must be boolean")
    timestamp = _timestamp(created_at)
    root = _root(workspace)
    with _ledger_transaction(root):
        ledger = _load_ledger(root)
    unknown = sorted(set(demand_ids) - set(ledger["records"]))
    if unknown:
        raise VSDDemandError(f"Unknown demand IDs: {unknown!r}")
    proposals = []
    for demand_id in demand_ids:
        record = ledger["records"][demand_id]
        counts = record["observation_counts"]
        if counts["missing"] == 0 and counts["partial"] == 0:
            raise VSDDemandError(
                f"Demand {demand_id!r} has no unmet observations to export"
            )
        score, unmet_rate = _priority(record)
        proposal_body = {
            "public_summary": record["public_summary"],
            "capability": _export_capability(record["capability"]),
            "observation_counts": copy.deepcopy(counts),
            "total_observations": record["total_observations"],
            "priority_score": score,
            "unmet_rate": unmet_rate,
            "recommended_next_step": (
                "review_external_api_candidates"
                if counts["missing"] > 0
                else "inspect_or_extend_existing_tools"
            ),
        }
        proposals.append(
            {"proposal_id": _canonical_digest(proposal_body)[:16], **proposal_body}
        )
    export = {
        "version": _EXPORT_VERSION,
        "created_at": timestamp,
        "review": {"reviewed_by": reviewer, "decision_note": note},
        "proposals": proposals,
        "transmission": "none; this file was written locally for explicit human review",
    }
    export["export_sha256"] = _canonical_digest(export)
    validate_proposal_export(export)
    destination = Path(output_path).expanduser()
    protected = {
        (root / "demand_ledger.json").resolve(),
        (root / ".demand.lock").resolve(),
    }
    if destination.resolve() in protected:
        raise VSDDemandError("Proposal output must not replace private ledger files")
    if destination.suffix.casefold() != ".json":
        raise VSDDemandError("Proposal output must use a .json filename")
    if destination.exists() and not replace:
        raise VSDDemandError("Proposal output already exists; set replace explicitly")
    _atomic_write_json(destination, export)
    return export


def validate_proposal_export(value: Any) -> None:
    """Validate the complete sanitized export and its content digest."""
    required = {
        "version",
        "created_at",
        "review",
        "proposals",
        "transmission",
        "export_sha256",
    }
    if not isinstance(value, dict) or set(value) != required:
        raise VSDDemandError("Proposal export has an unsupported structure")
    if value.get("version") != _EXPORT_VERSION:
        raise VSDDemandError("Proposal export version is not supported")
    if _timestamp(value.get("created_at")) != value["created_at"]:
        raise VSDDemandError("Proposal export timestamp is not canonical")
    review = value.get("review")
    if not isinstance(review, dict) or set(review) != {"reviewed_by", "decision_note"}:
        raise VSDDemandError("Proposal export review is invalid")
    _safe_public_text(
        review["reviewed_by"], field="reviewed_by", minimum=3, maximum=100
    )
    _safe_public_text(
        review["decision_note"], field="decision_note", minimum=20, maximum=500
    )
    proposals = value.get("proposals")
    if not isinstance(proposals, list) or not 1 <= len(proposals) <= 100:
        raise VSDDemandError("Proposal export must contain 1-100 proposals")
    proposal_ids: set[str] = set()
    proposal_keys = {
        "proposal_id",
        "public_summary",
        "capability",
        "observation_counts",
        "total_observations",
        "priority_score",
        "unmet_rate",
        "recommended_next_step",
    }
    for proposal in proposals:
        if not isinstance(proposal, dict) or set(proposal) != proposal_keys:
            raise VSDDemandError("Proposal export contains an invalid proposal")
        proposal_id = proposal.get("proposal_id")
        if (
            not isinstance(proposal_id, str)
            or not _DEMAND_ID_RE.fullmatch(proposal_id)
            or proposal_id in proposal_ids
        ):
            raise VSDDemandError("Proposal export contains invalid proposal IDs")
        proposal_ids.add(proposal_id)
        _safe_public_text(
            proposal["public_summary"],
            field="public_summary",
            minimum=10,
            maximum=240,
        )
        _validate_export_capability(proposal["capability"])
        counts = proposal.get("observation_counts")
        if (
            not isinstance(counts, dict)
            or set(counts) != _OBSERVATION_KEYS
            or any(type(count) is not int or count < 0 for count in counts.values())
            or proposal.get("total_observations") != sum(counts.values())
            or counts["missing"] + counts["partial"] == 0
        ):
            raise VSDDemandError("Proposal export contains invalid observation counts")
        score = counts["missing"] * 5 + counts["partial"] * 2
        unmet_rate = round(
            (counts["missing"] + counts["partial"]) / proposal["total_observations"],
            4,
        )
        expected_next = (
            "review_external_api_candidates"
            if counts["missing"] > 0
            else "inspect_or_extend_existing_tools"
        )
        body = {key: proposal[key] for key in proposal_keys - {"proposal_id"}}
        if (
            proposal["priority_score"] != score
            or proposal["unmet_rate"] != unmet_rate
            or proposal["recommended_next_step"] != expected_next
            or proposal_id != _canonical_digest(body)[:16]
        ):
            raise VSDDemandError("Proposal export contains inconsistent derived fields")
    if value.get("transmission") != (
        "none; this file was written locally for explicit human review"
    ):
        raise VSDDemandError("Proposal export transmission boundary is invalid")
    expected_digest = _canonical_digest(
        {key: item for key, item in value.items() if key != "export_sha256"}
    )
    if value.get("export_sha256") != expected_digest:
        raise VSDDemandError("Proposal export integrity digest does not match")


def remove_demand(
    demand_id: str,
    *,
    workspace: str | Path | None = None,
    confirm: bool = False,
) -> dict[str, Any]:
    """Remove one local aggregate through an explicit privacy control."""
    if not isinstance(demand_id, str) or not _DEMAND_ID_RE.fullmatch(demand_id):
        raise VSDDemandError("demand_id is not valid")
    if confirm is not True:
        raise VSDDemandError("confirm=True is required to remove a demand")
    root = _root(workspace)
    with _ledger_transaction(root):
        ledger = _load_ledger(root)
        if demand_id not in ledger["records"]:
            raise VSDDemandError("Demand does not exist")
        del ledger["records"][demand_id]
        updated = _with_integrity(ledger)
        _atomic_write_json(root / "demand_ledger.json", updated)
    return {
        "status": "success",
        "data": {
            "removed": True,
            "demand_id": demand_id,
            "ledger_sha256": updated["integrity_sha256"],
        },
    }


__all__ = [
    "VSDDemandError",
    "export_proposals",
    "observe_capability_demand",
    "rank_demands",
    "record_coverage_observation",
    "record_plan_demands",
    "remove_demand",
    "validate_proposal_export",
]
