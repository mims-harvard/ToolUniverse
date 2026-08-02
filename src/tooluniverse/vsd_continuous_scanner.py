"""Scheduled local catalog scanning for inert VSD operation candidates.

The scanner inventories an approved machine-readable directory, detects changes
between runs, snapshots a bounded selection of contracts, and uses the existing
VSD inspectors to determine which operations could become narrow tools. It does
not execute provider operations, create approvals, publish tools, or transmit
results.
"""

from __future__ import annotations

import copy
import hashlib
import ipaddress
import json
import os
import re
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator
from urllib.parse import urlsplit

from .vsd_contracts import inspect_contract_document
from .vsd_coverage import _operation_identity, _registry_tools
from .vsd_promotion import build_openapi_tool_config
from .vsd_source_intelligence import (
    _atomic_write,
    _canonical_url,
    _digest,
    _fetch_https,
    _timestamp,
    configured_source_inventory,
    validate_source_inventory,
)
from .vsd_tool import (
    _acquire_process_lock,
    _release_process_lock,
    _safe_get_json,
)

_VERSION = 1
_APIS_GURU_ID = "apis_guru"
_APIS_GURU_ENDPOINT = "https://api.apis.guru/v2/list.json"
_APIS_GURU_HOST = "api.apis.guru"
_MAX_DIRECTORY_RECORDS = 5_000
_MAX_CONTRACTS_PER_CYCLE = 200
_MAX_DRAFTABLE_TARGET = 2_000
_MAX_CONTRACT_BYTES = 1_000_000
_MAX_OPERATION_SUMMARIES = 5_000
_MAX_REPORT_BYTES = 12_000_000
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_ID_RE = re.compile(r"^[0-9a-f]{16}$")
_STATE_LOCK = threading.RLock()

_CatalogFetcher = Callable[..., tuple[Any, dict[str, Any]]]
_ContractFetcher = Callable[[str, float, int], tuple[bytes, dict[str, Any]]]


class VSDContinuousScannerError(ValueError):
    """Raised when a scheduled scan crosses its catalog or trust boundary."""


def _text(value: Any, maximum: int) -> str:
    normalized = " ".join(str(value or "").split())
    return "".join(character for character in normalized if ord(character) >= 32)[
        :maximum
    ]


def _record_digest(record: dict[str, Any]) -> str:
    return _digest(record)


def _checked_request(request: Any, payload: Any) -> dict[str, Any]:
    if not isinstance(request, dict):
        raise VSDContinuousScannerError("Catalog request metadata must be an object")
    status = request.get("status_code")
    content_type = _text(request.get("content_type"), 200)
    response_bytes = request.get("response_bytes")
    redirects = request.get("redirects")
    if (
        type(status) is not int
        or not 200 <= status < 300
        or not content_type
        or type(response_bytes) is not int
        or response_bytes < 1
        or redirects != 0
    ):
        raise VSDContinuousScannerError("Catalog request metadata is invalid")
    return {
        "status_code": status,
        "content_type": content_type,
        "response_bytes": response_bytes,
        "redirects": redirects,
        "payload_sha256": _digest(payload),
    }


def _apis_guru_specification_url(value: Any) -> str:
    try:
        url = _canonical_url(value, allowed_hosts={_APIS_GURU_HOST})
    except Exception as exc:  # noqa: BLE001
        raise VSDContinuousScannerError(
            "APIs.guru specification URL is outside the approved directory host"
        ) from exc
    path = urlsplit(url).path
    if not path.startswith("/v2/specs/") or not path.endswith(".json"):
        raise VSDContinuousScannerError(
            "APIs.guru specification URL is outside the approved path"
        )
    return url


def normalize_apis_guru_directory(
    payload: Any,
    *,
    request: Any,
    retrieved_at: str | None = None,
) -> dict[str, Any]:
    """Normalize the complete APIs.guru directory without trusting its records."""
    if not isinstance(payload, dict) or not 1 <= len(payload) <= _MAX_DIRECTORY_RECORDS:
        raise VSDContinuousScannerError(
            "APIs.guru directory must contain 1-5000 records"
        )
    records: list[dict[str, Any]] = []
    seen: set[str] = set()
    for provider_name, entry in sorted(payload.items(), key=lambda item: str(item[0])):
        if not isinstance(provider_name, str) or not isinstance(entry, dict):
            continue
        preferred = entry.get("preferred")
        versions = entry.get("versions")
        if not isinstance(preferred, str) or not isinstance(versions, dict):
            continue
        version = versions.get(preferred)
        if not isinstance(version, dict):
            continue
        try:
            specification_url = _apis_guru_specification_url(version.get("swaggerUrl"))
        except VSDContinuousScannerError:
            continue
        record_id = f"{provider_name}:{preferred}"
        if record_id in seen or len(record_id) > 600:
            continue
        info = version.get("info") if isinstance(version.get("info"), dict) else {}
        raw_categories = info.get("x-apisguru-categories") or []
        if isinstance(raw_categories, str):
            raw_categories = [raw_categories]
        categories = sorted(
            {
                category
                for value in raw_categories[:30]
                if (category := _text(value, 100))
                and re.fullmatch(r"[A-Za-z][A-Za-z0-9 _-]{1,99}", category)
            },
            key=str.casefold,
        )
        openapi_version = _text(version.get("openapiVer"), 40)
        compatible = bool(re.fullmatch(r"3\.(?:0|1)(?:\.[0-9]+)?", openapi_version))
        record_body = {
            "record_id": record_id,
            "source_id": hashlib.sha256(record_id.encode("utf-8")).hexdigest()[:16],
            "provider_name": _text(provider_name, 300),
            "title": _text(info.get("title") or provider_name, 300),
            "api_version": _text(preferred, 100),
            "openapi_version": openapi_version,
            "specification_url": specification_url,
            "format_hint": "openapi",
            "categories": categories,
            "updated_at": _text(version.get("updated") or version.get("added"), 100),
            "compatibility": (
                "inspectable_openapi_3" if compatible else "unsupported_openapi_version"
            ),
            "approval_state": "unreviewed_directory_record",
            "execution_allowed": False,
        }
        records.append({**record_body, "record_sha256": _record_digest(record_body)})
        seen.add(record_id)
    if not records:
        raise VSDContinuousScannerError("APIs.guru directory yielded no valid records")
    records.sort(key=lambda item: item["record_id"].casefold())
    body = {
        "format": "vsd_openapi_directory_snapshot_v1",
        "version": _VERSION,
        "catalog_id": _APIS_GURU_ID,
        "catalog_endpoint": _APIS_GURU_ENDPOINT,
        "retrieved_at": _timestamp(retrieved_at),
        "request": _checked_request(request, payload),
        "record_count": len(records),
        "compatible_record_count": sum(
            item["compatibility"] == "inspectable_openapi_3" for item in records
        ),
        "unsupported_record_count": sum(
            item["compatibility"] != "inspectable_openapi_3" for item in records
        ),
        "records": records,
        "approval_state": "unreviewed_directory_snapshot",
        "execution_allowed": False,
    }
    return {**body, "directory_sha256": _digest(body)}


def validate_directory_snapshot(value: Any) -> dict[str, Any]:
    required = {
        "format",
        "version",
        "catalog_id",
        "catalog_endpoint",
        "retrieved_at",
        "request",
        "record_count",
        "compatible_record_count",
        "unsupported_record_count",
        "records",
        "approval_state",
        "execution_allowed",
        "directory_sha256",
    }
    if not isinstance(value, dict) or set(value) != required:
        raise VSDContinuousScannerError("Directory snapshot structure is invalid")
    body = {key: item for key, item in value.items() if key != "directory_sha256"}
    records = value.get("records")
    if (
        value["format"] != "vsd_openapi_directory_snapshot_v1"
        or value["version"] != _VERSION
        or value["catalog_id"] != _APIS_GURU_ID
        or value["catalog_endpoint"] != _APIS_GURU_ENDPOINT
        or _timestamp(value["retrieved_at"]) != value["retrieved_at"]
        or value["approval_state"] != "unreviewed_directory_snapshot"
        or value["execution_allowed"] is not False
        or value["directory_sha256"] != _digest(body)
        or not isinstance(records, list)
        or not 1 <= len(records) <= _MAX_DIRECTORY_RECORDS
        or value["record_count"] != len(records)
    ):
        raise VSDContinuousScannerError("Directory snapshot identity is invalid")
    compatible = 0
    previous = ""
    record_keys = {
        "record_id",
        "source_id",
        "provider_name",
        "title",
        "api_version",
        "openapi_version",
        "specification_url",
        "format_hint",
        "categories",
        "updated_at",
        "compatibility",
        "approval_state",
        "execution_allowed",
        "record_sha256",
    }
    for record in records:
        if not isinstance(record, dict) or set(record) != record_keys:
            raise VSDContinuousScannerError("Directory record structure is invalid")
        record_body = {
            key: item for key, item in record.items() if key != "record_sha256"
        }
        record_id = record.get("record_id")
        if (
            not isinstance(record_id, str)
            or not record_id
            or record_id.casefold() <= previous
            or not _ID_RE.fullmatch(str(record.get("source_id", "")))
            or record["source_id"]
            != hashlib.sha256(record_id.encode("utf-8")).hexdigest()[:16]
            or record["record_sha256"] != _record_digest(record_body)
            or record["format_hint"] != "openapi"
            or record["approval_state"] != "unreviewed_directory_record"
            or record["execution_allowed"] is not False
            or record["compatibility"]
            not in {"inspectable_openapi_3", "unsupported_openapi_version"}
        ):
            raise VSDContinuousScannerError("Directory record identity is invalid")
        if (
            _apis_guru_specification_url(record["specification_url"])
            != record["specification_url"]
        ):
            raise VSDContinuousScannerError("Directory record URL is not canonical")
        categories = record.get("categories")
        if (
            not isinstance(categories, list)
            or categories != sorted(set(categories), key=str.casefold)
            or any(not isinstance(item, str) or not item for item in categories)
        ):
            raise VSDContinuousScannerError("Directory categories are invalid")
        compatible += record["compatibility"] == "inspectable_openapi_3"
        previous = record_id.casefold()
    if (
        value["compatible_record_count"] != compatible
        or value["unsupported_record_count"] != len(records) - compatible
    ):
        raise VSDContinuousScannerError("Directory counts do not match records")
    return copy.deepcopy(value)


def _balanced(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[str, list[dict[str, Any]]] = {}
    for record in sorted(records, key=lambda item: item["record_id"].casefold()):
        bucket = record["categories"][0] if record["categories"] else "uncategorized"
        buckets.setdefault(bucket.casefold(), []).append(record)
    output: list[dict[str, Any]] = []
    while buckets:
        for key in sorted(list(buckets)):
            output.append(buckets[key].pop(0))
            if not buckets[key]:
                del buckets[key]
    return output


def _append_unique(
    output: list[dict[str, Any]],
    seen: set[str],
    records: Iterable[dict[str, Any]],
    maximum: int,
) -> None:
    for record in records:
        if len(output) >= maximum:
            return
        if record["record_id"] not in seen:
            output.append(record)
            seen.add(record["record_id"])


def _select_records(
    records: list[dict[str, Any]],
    *,
    added: set[str],
    changed: set[str],
    previously_inspected: set[str],
    cursor: int,
    maximum: int,
) -> list[dict[str, Any]]:
    compatible = [
        record
        for record in records
        if record["compatibility"] == "inspectable_openapi_3"
    ]
    by_id = {record["record_id"]: record for record in compatible}
    output: list[dict[str, Any]] = []
    seen: set[str] = set()
    priority = [
        by_id[record_id]
        for record_id in sorted((added | changed) & set(by_id), key=str.casefold)
    ]
    _append_unique(output, seen, _balanced(priority), maximum)
    uninspected = [
        record
        for record in compatible
        if record["record_id"] not in previously_inspected
    ]
    _append_unique(output, seen, _balanced(uninspected), maximum)
    if compatible and len(output) < maximum:
        start = cursor % len(compatible)
        rotated = compatible[start:] + compatible[:start]
        _append_unique(output, seen, rotated, maximum)
    return output


def _registry_context(
    inventory: Any, registry_tools: Iterable[dict[str, Any]]
) -> tuple[dict[str, Any], dict[tuple[str, str, str], list[str]], dict[str, list[str]]]:
    checked_inventory = validate_source_inventory(inventory)
    exact: dict[tuple[str, str, str], list[str]] = {}
    registry_summary: list[dict[str, Any]] = []
    for config in registry_tools:
        if not isinstance(config, dict):
            continue
        identity = _operation_identity(config)
        name = _text(config.get("name"), 200)
        if name and all(identity):
            exact.setdefault(identity, []).append(name)
            registry_summary.append({"name": name, "identity": list(identity)})
    for names in exact.values():
        names.sort(key=str.casefold)
    hosts = {entry["host"]: entry["tools"] for entry in checked_inventory["hosts"]}
    summary = {
        "tool_count": checked_inventory["tool_count"],
        "host_count": checked_inventory["host_count"],
        "inventory_sha256": checked_inventory["inventory_sha256"],
        "reviewed_operation_count": len(exact),
        "reviewed_operation_sha256": _digest(
            sorted(registry_summary, key=lambda item: item["name"].casefold())
        ),
    }
    return summary, exact, hosts


def _preview_name(record: dict[str, Any], candidate: dict[str, Any]) -> str:
    seed = hashlib.sha256(record["record_id"].encode("utf-8")).hexdigest()[:8]
    return f"VSDScan{seed}{candidate['candidate_id'][:12]}"


def _public_server_host(candidate: dict[str, Any]) -> bool:
    host = (urlsplit(str(candidate.get("server_url") or "")).hostname or "").casefold()
    if (
        not host
        or len(host) > 253
        or "." not in host
        or host.endswith((".local", ".localhost", ".internal", ".invalid", ".test"))
    ):
        return False
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return bool(re.fullmatch(r"[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?", host))
    return address.is_global


def _preview_config(
    record: dict[str, Any], candidate: dict[str, Any]
) -> tuple[dict[str, Any], str]:
    name = _preview_name(record, candidate)
    credential_env = (
        "TOOLUNIVERSE_VSD_SCANNER_CREDENTIAL" if candidate.get("auth") else None
    )
    config = build_openapi_tool_config(
        candidate,
        tool_name=name,
        description=(
            "Unapproved scanner preview for the reviewed "
            f"{candidate['api_title']} operation {candidate['operation_id']}."
        )[:1_000],
        credential_env=credential_env,
    )
    return config, _digest(config)


def _snapshot_contract(
    record: dict[str, Any],
    root: Path,
    *,
    fetcher: _ContractFetcher,
    timeout_seconds: float,
    max_bytes: int,
) -> tuple[Path, str, int]:
    url = record["specification_url"]
    raw, metadata = fetcher(url, timeout_seconds, max_bytes)
    if (
        not isinstance(raw, bytes)
        or metadata.get("url") != url
        or metadata.get("redirects") != 0
        or metadata.get("response_bytes") != len(raw)
        or not 1 <= len(raw) <= max_bytes
    ):
        raise VSDContinuousScannerError(
            "Contract fetch changed the URL or exceeded its byte boundary"
        )
    digest = hashlib.sha256(raw).hexdigest()
    destination = root / f"{digest}.openapi.json"
    if destination.exists():
        if hashlib.sha256(destination.read_bytes()).hexdigest() != digest:
            raise VSDContinuousScannerError(
                "Existing contract snapshot failed digest verification"
            )
    else:
        _atomic_write(destination, raw)
    return destination, digest, len(raw)


def _error_record(record: dict[str, Any], exc: Exception) -> dict[str, str]:
    return {
        "record_id": record["record_id"],
        "source_id": record["source_id"],
        "error_type": type(exc).__name__[:100],
        "message": _text(exc, 300) or "Contract inspection failed",
    }


def _previous_state(previous: Any | None) -> dict[str, Any]:
    if previous is None:
        return {
            "cycle_id": None,
            "directory_records": [],
            "inspected_record_ids": [],
            "next_cursor": 0,
        }
    checked = validate_continuous_scan_cycle(previous)
    return {
        "cycle_id": checked["cycle_id"],
        **copy.deepcopy(checked["state"]),
    }


def build_continuous_scan_cycle(
    directory: Any,
    *,
    inventory: Any,
    registry_tools: Iterable[dict[str, Any]],
    snapshot_directory: str | Path,
    previous_cycle: Any | None = None,
    max_contracts: int = 100,
    draftable_tool_target: int = 500,
    timeout_seconds: float = 20,
    max_contract_bytes: int = _MAX_CONTRACT_BYTES,
    contract_fetcher: _ContractFetcher = _fetch_https,
    scanned_at: str | None = None,
) -> dict[str, Any]:
    """Build one incremental cycle and leave every discovered operation inert."""
    checked_directory = validate_directory_snapshot(directory)
    if (
        type(max_contracts) is not int
        or not 1 <= max_contracts <= _MAX_CONTRACTS_PER_CYCLE
    ):
        raise VSDContinuousScannerError("max_contracts must be between 1 and 200")
    if (
        type(draftable_tool_target) is not int
        or not 1 <= draftable_tool_target <= _MAX_DRAFTABLE_TARGET
    ):
        raise VSDContinuousScannerError(
            "draftable_tool_target must be between 1 and 2000"
        )
    if not isinstance(timeout_seconds, (int, float)) or not 1 <= timeout_seconds <= 60:
        raise VSDContinuousScannerError("timeout_seconds must be between 1 and 60")
    if (
        type(max_contract_bytes) is not int
        or not 1 <= max_contract_bytes <= _MAX_CONTRACT_BYTES
    ):
        raise VSDContinuousScannerError(
            "max_contract_bytes must be between 1 and 1000000"
        )

    previous = _previous_state(previous_cycle)
    current_index = {
        item["record_id"]: item["record_sha256"]
        for item in checked_directory["records"]
    }
    previous_index = {
        item["record_id"]: item["record_sha256"]
        for item in previous["directory_records"]
    }
    added = set(current_index) - set(previous_index)
    removed = set(previous_index) - set(current_index)
    changed = {
        record_id
        for record_id in set(current_index) & set(previous_index)
        if current_index[record_id] != previous_index[record_id]
    }
    unchanged = set(current_index) - added - changed
    previously_inspected = set(previous["inspected_record_ids"]) - removed
    selected = _select_records(
        checked_directory["records"],
        added=added,
        changed=changed,
        previously_inspected=previously_inspected,
        cursor=previous["next_cursor"],
        maximum=max_contracts,
    )

    root = Path(snapshot_directory).expanduser()
    root.mkdir(parents=True, exist_ok=True)
    os.chmod(root, 0o700)
    registry, exact_operations, host_tools = _registry_context(
        inventory, registry_tools
    )
    contracts: list[dict[str, Any]] = []
    operations: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    newly_inspected: set[str] = set()
    blocker_counts: dict[str, int] = {}
    draftable_count = 0
    existing_exact_count = 0
    attempted: list[str] = []

    for record in selected:
        if draftable_count >= draftable_tool_target:
            break
        attempted.append(record["record_id"])
        try:
            path, content_sha256, response_bytes = _snapshot_contract(
                record,
                root,
                fetcher=contract_fetcher,
                timeout_seconds=timeout_seconds,
                max_bytes=max_contract_bytes,
            )
            report = inspect_contract_document(path, format_hint=record["format_hint"])
            candidates = report.get("candidates")
            if not isinstance(candidates, list):
                raise VSDContinuousScannerError(
                    "Contract inspector returned no candidate list"
                )
            contract_draftable = 0
            contract_existing = 0
            contract_blocked = 0
            for candidate in candidates:
                if len(operations) >= _MAX_OPERATION_SUMMARIES:
                    raise VSDContinuousScannerError(
                        "Cycle exceeds the operation summary limit"
                    )
                raw_blockers = candidate.get("blockers")
                blockers = (
                    sorted(set(raw_blockers))
                    if isinstance(raw_blockers, list)
                    and all(isinstance(item, str) for item in raw_blockers)
                    else ["invalid_blocker_inventory"]
                )
                if not blockers and not _public_server_host(candidate):
                    blockers = ["server_host_not_publicly_addressable"]
                for blocker in blockers:
                    blocker_counts[blocker] = blocker_counts.get(blocker, 0) + 1
                preview: dict[str, str] | None = None
                coverage = "blocked"
                matches: list[str] = []
                identity = ("", "", "")
                if not blockers:
                    try:
                        config, config_sha256 = _preview_config(record, candidate)
                        identity = _operation_identity(config)
                        if not all(identity):
                            raise VSDContinuousScannerError(
                                "Preview operation identity is incomplete"
                            )
                        matches = exact_operations.get(identity, [])
                        if matches:
                            coverage = "existing_exact"
                            contract_existing += 1
                            existing_exact_count += 1
                        else:
                            coverage = (
                                "existing_host_gap"
                                if identity[1] in host_tools
                                else "candidate_gap"
                            )
                            preview = {
                                "tool_name": config["name"],
                                "config_sha256": config_sha256,
                            }
                            contract_draftable += 1
                            draftable_count += 1
                    except Exception:  # noqa: BLE001
                        blockers = ["preview_generation_failed"]
                        blocker_counts["preview_generation_failed"] = (
                            blocker_counts.get("preview_generation_failed", 0) + 1
                        )
                        coverage = "blocked"
                if blockers:
                    contract_blocked += 1
                operations.append(
                    {
                        "source_id": record["source_id"],
                        "record_id": record["record_id"],
                        "content_sha256": content_sha256,
                        "candidate_id": _text(candidate.get("candidate_id"), 32),
                        "candidate_sha256": _text(
                            candidate.get("candidate_sha256"), 64
                        ),
                        "api_title": _text(candidate.get("api_title"), 300),
                        "api_version": _text(candidate.get("api_version"), 100),
                        "operation_id": _text(candidate.get("operation_id"), 300),
                        "method": _text(candidate.get("method"), 20),
                        "host": identity[1]
                        or _text(
                            urlsplit(str(candidate.get("server_url") or "")).hostname,
                            253,
                        ),
                        "path": identity[2] or _text(candidate.get("path"), 500),
                        "blockers": blockers,
                        "warnings": sorted(
                            {
                                item
                                for item in candidate.get("warnings", [])
                                if isinstance(item, str)
                            }
                        )[:50],
                        "registry_coverage": coverage,
                        "existing_tools": matches,
                        "preview": preview,
                        "approval_state": "unreviewed_operation_candidate",
                        "execution_allowed": False,
                    }
                )
            contracts.append(
                {
                    "source_id": record["source_id"],
                    "record_id": record["record_id"],
                    "specification_url": record["specification_url"],
                    "content_sha256": content_sha256,
                    "response_bytes": response_bytes,
                    "snapshot_file": path.name,
                    "candidate_count": len(candidates),
                    "draftable_count": contract_draftable,
                    "existing_exact_count": contract_existing,
                    "blocked_count": contract_blocked,
                    "inspection_sha256": _digest(report),
                }
            )
            newly_inspected.add(record["record_id"])
        except Exception as exc:  # noqa: BLE001
            failures.append(_error_record(record, exc))

    inspected = sorted(previously_inspected | newly_inspected, key=str.casefold)
    directory_records = [
        {"record_id": key, "record_sha256": current_index[key]}
        for key in sorted(current_index, key=str.casefold)
    ]
    metrics = {
        "catalog_record_count": checked_directory["record_count"],
        "compatible_record_count": checked_directory["compatible_record_count"],
        "unsupported_record_count": checked_directory["unsupported_record_count"],
        "selected_record_count": len(attempted),
        "inspected_contract_count": len(contracts),
        "failed_contract_count": len(failures),
        "operation_candidate_count": len(operations),
        "draftable_tool_count": draftable_count,
        "existing_exact_operation_count": existing_exact_count,
        "existing_host_gap_count": sum(
            item["registry_coverage"] == "existing_host_gap" for item in operations
        ),
        "new_host_candidate_count": sum(
            item["registry_coverage"] == "candidate_gap" for item in operations
        ),
        "blocked_operation_count": sum(bool(item["blockers"]) for item in operations),
        "target_reached": draftable_count >= draftable_tool_target,
    }
    body = {
        "format": "vsd_continuous_catalog_cycle_v1",
        "version": _VERSION,
        "scanned_at": _timestamp(scanned_at),
        "previous_cycle_id": previous["cycle_id"],
        "directory": checked_directory,
        "delta": {
            "added_count": len(added),
            "changed_count": len(changed),
            "removed_count": len(removed),
            "unchanged_count": len(unchanged),
            "added_record_ids": sorted(added, key=str.casefold),
            "changed_record_ids": sorted(changed, key=str.casefold),
            "removed_record_ids": sorted(removed, key=str.casefold),
        },
        "registry": registry,
        "limits": {
            "max_contracts": max_contracts,
            "draftable_tool_target": draftable_tool_target,
            "timeout_seconds": timeout_seconds,
            "max_contract_bytes": max_contract_bytes,
        },
        "attempted_record_ids": attempted,
        "contracts": contracts,
        "failures": failures,
        "operations": operations,
        "blocker_counts": dict(sorted(blocker_counts.items())),
        "metrics": metrics,
        "state": {
            "directory_records": directory_records,
            "inspected_record_ids": inspected,
            "next_cursor": (
                (previous["next_cursor"] + len(attempted))
                % max(1, checked_directory["compatible_record_count"])
            ),
        },
        "approval_state": "unreviewed_continuous_scan",
        "execution_allowed": False,
        "automatic_publication": False,
        "transmission": "none; local review is required before explicit handoff",
        "boundary": (
            "Preview hashes demonstrate that compatible operations can form narrow VSD "
            "configs. They are not verified, approved, published, loaded, or executed."
        ),
    }
    digest = _digest(body)
    return {**body, "cycle_id": digest[:16], "cycle_sha256": digest}


def validate_continuous_scan_cycle(value: Any) -> dict[str, Any]:
    required = {
        "format",
        "version",
        "scanned_at",
        "previous_cycle_id",
        "directory",
        "delta",
        "registry",
        "limits",
        "attempted_record_ids",
        "contracts",
        "failures",
        "operations",
        "blocker_counts",
        "metrics",
        "state",
        "approval_state",
        "execution_allowed",
        "automatic_publication",
        "transmission",
        "boundary",
        "cycle_id",
        "cycle_sha256",
    }
    if not isinstance(value, dict) or set(value) != required:
        raise VSDContinuousScannerError("Continuous scan structure is invalid")
    body = {
        key: item
        for key, item in value.items()
        if key not in {"cycle_id", "cycle_sha256"}
    }
    digest = _digest(body)
    operations = value.get("operations")
    contracts = value.get("contracts")
    failures = value.get("failures")
    metrics = value.get("metrics")
    if (
        value["format"] != "vsd_continuous_catalog_cycle_v1"
        or value["version"] != _VERSION
        or _timestamp(value["scanned_at"]) != value["scanned_at"]
        or value["approval_state"] != "unreviewed_continuous_scan"
        or value["execution_allowed"] is not False
        or value["automatic_publication"] is not False
        or value["cycle_sha256"] != digest
        or value["cycle_id"] != digest[:16]
        or not isinstance(operations, list)
        or len(operations) > _MAX_OPERATION_SUMMARIES
        or not isinstance(contracts, list)
        or not isinstance(failures, list)
        or not isinstance(metrics, dict)
    ):
        raise VSDContinuousScannerError("Continuous scan identity is invalid")
    validate_directory_snapshot(value["directory"])
    if (
        metrics.get("inspected_contract_count") != len(contracts)
        or metrics.get("failed_contract_count") != len(failures)
        or metrics.get("operation_candidate_count") != len(operations)
        or metrics.get("draftable_tool_count")
        != sum(item.get("preview") is not None for item in operations)
        or metrics.get("existing_host_gap_count")
        != sum(
            item.get("registry_coverage") == "existing_host_gap" for item in operations
        )
        or metrics.get("new_host_candidate_count")
        != sum(item.get("registry_coverage") == "candidate_gap" for item in operations)
        or metrics.get("blocked_operation_count")
        != sum(bool(item.get("blockers")) for item in operations)
    ):
        raise VSDContinuousScannerError("Continuous scan metrics do not match evidence")
    for operation in operations:
        if (
            not isinstance(operation, dict)
            or operation.get("approval_state") != "unreviewed_operation_candidate"
            or operation.get("execution_allowed") is not False
            or not _SHA256_RE.fullmatch(str(operation.get("content_sha256", "")))
        ):
            raise VSDContinuousScannerError("Operation summary crossed its boundary")
        preview = operation.get("preview")
        if preview is not None and (
            not isinstance(preview, dict)
            or set(preview) != {"tool_name", "config_sha256"}
            or not _SHA256_RE.fullmatch(str(preview.get("config_sha256", "")))
            or operation.get("blockers")
            or operation.get("registry_coverage")
            not in {"candidate_gap", "existing_host_gap"}
        ):
            raise VSDContinuousScannerError("Draftable preview evidence is invalid")
    state = value.get("state")
    if not isinstance(state, dict) or set(state) != {
        "directory_records",
        "inspected_record_ids",
        "next_cursor",
    }:
        raise VSDContinuousScannerError("Continuous scan state is invalid")
    directory_records = state["directory_records"]
    expected_records = [
        {"record_id": item["record_id"], "record_sha256": item["record_sha256"]}
        for item in value["directory"]["records"]
    ]
    if directory_records != expected_records:
        raise VSDContinuousScannerError("Continuous scan state lost directory identity")
    raw = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True).encode("utf-8")
    if len(raw) > _MAX_REPORT_BYTES:
        raise VSDContinuousScannerError("Continuous scan report exceeds 12 MB")
    return copy.deepcopy(value)


def _state_root(path: str | Path) -> Path:
    root = Path(path).expanduser()
    root.mkdir(parents=True, exist_ok=True)
    os.chmod(root, 0o700)
    return root


@contextmanager
def _state_transaction(path: str | Path) -> Iterator[Path]:
    with _STATE_LOCK:
        root = _state_root(path)
        lock_path = root / ".continuous-scanner.lock"
        with lock_path.open("a+b") as handle:
            if handle.seek(0, os.SEEK_END) == 0:
                handle.write(b"\0")
                handle.flush()
            _acquire_process_lock(handle)
            try:
                yield root
            finally:
                _release_process_lock(handle)


def _read_latest(root: Path) -> dict[str, Any] | None:
    path = root / "latest.json"
    if not path.exists():
        return None
    try:
        if path.stat().st_size > _MAX_REPORT_BYTES:
            raise VSDContinuousScannerError("Latest scan report exceeds 12 MB")
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise VSDContinuousScannerError("Latest scan report is unreadable") from exc
    return validate_continuous_scan_cycle(value)


def load_latest_continuous_scan(state_directory: str | Path) -> dict[str, Any] | None:
    root = _state_root(state_directory)
    return _read_latest(root)


def _write_cycle(root: Path, cycle: Any) -> tuple[Path, Path]:
    checked = validate_continuous_scan_cycle(cycle)
    raw = (
        json.dumps(checked, indent=2, sort_keys=True, ensure_ascii=True).encode("utf-8")
        + b"\n"
    )
    history = root / f"cycle-{checked['cycle_id']}.json"
    if history.exists():
        if history.read_bytes() != raw:
            raise VSDContinuousScannerError("Immutable cycle history was modified")
    else:
        _atomic_write(history, raw)
    latest = root / "latest.json"
    _atomic_write(latest, raw)
    return history, latest


def write_continuous_scan_cycle(
    cycle: Any, state_directory: str | Path
) -> tuple[Path, Path]:
    with _state_transaction(state_directory) as root:
        return _write_cycle(root, cycle)


def run_scheduled_apis_guru_scan(
    tooluniverse: Any,
    state_directory: str | Path,
    *,
    max_contracts: int = 100,
    draftable_tool_target: int = 500,
    timeout_seconds: float = 20,
    max_contract_bytes: int = _MAX_CONTRACT_BYTES,
    catalog_fetcher: _CatalogFetcher = _safe_get_json,
    contract_fetcher: _ContractFetcher = _fetch_https,
    scanned_at: str | None = None,
) -> dict[str, Any]:
    """Run one serialized APIs.guru cycle suitable for cron or a scheduler."""
    with _state_transaction(state_directory) as root:
        previous = _read_latest(root)
        payload, request = catalog_fetcher(
            _APIS_GURU_ENDPOINT,
            None,
            timeout=max(30, timeout_seconds),
            max_response_bytes=10_000_000,
        )
        directory = normalize_apis_guru_directory(
            payload, request=request, retrieved_at=scanned_at
        )
        inventory = configured_source_inventory(tooluniverse)
        cycle = build_continuous_scan_cycle(
            directory,
            inventory=inventory,
            registry_tools=_registry_tools(tooluniverse),
            snapshot_directory=root / "contracts",
            previous_cycle=previous,
            max_contracts=max_contracts,
            draftable_tool_target=draftable_tool_target,
            timeout_seconds=timeout_seconds,
            max_contract_bytes=max_contract_bytes,
            contract_fetcher=contract_fetcher,
            scanned_at=scanned_at,
        )
        history, latest = _write_cycle(root, cycle)
        return {
            "cycle": cycle,
            "history_file": str(history),
            "latest_file": str(latest),
            "snapshot_directory": str(root / "contracts"),
        }


def summarize_continuous_scan(cycle: Any) -> dict[str, Any]:
    checked = validate_continuous_scan_cycle(cycle)
    return {
        "cycle_id": checked["cycle_id"],
        "scanned_at": checked["scanned_at"],
        "previous_cycle_id": checked["previous_cycle_id"],
        "directory_sha256": checked["directory"]["directory_sha256"],
        "delta": {
            key: checked["delta"][key]
            for key in ("added_count", "changed_count", "removed_count")
        },
        "registry": checked["registry"],
        "metrics": checked["metrics"],
        "blocker_counts": checked["blocker_counts"],
        "cycle_sha256": checked["cycle_sha256"],
        "boundary": checked["boundary"],
    }


__all__ = [
    "VSDContinuousScannerError",
    "build_continuous_scan_cycle",
    "load_latest_continuous_scan",
    "normalize_apis_guru_directory",
    "run_scheduled_apis_guru_scan",
    "summarize_continuous_scan",
    "validate_continuous_scan_cycle",
    "validate_directory_snapshot",
    "write_continuous_scan_cycle",
]
