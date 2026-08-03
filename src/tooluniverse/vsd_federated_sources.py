"""Provider-independent scanning of reviewed machine-readable API sources."""

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

from .vsd_coverage import _operation_identity, _registry_tools
from .vsd_openapi import inspect_openapi_document, load_openapi_document
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
from .vsd_tool import _acquire_process_lock, _release_process_lock

_VERSION = 1
_MANIFEST_PATH = Path(__file__).with_name("data") / "vsd_federated_sources.json"
_MAX_SOURCES = 250
_MAX_CONTRACT_BYTES = 1_000_000
_MAX_OPERATIONS = 25_000
_MAX_REPORT_BYTES = 50_000_000
_SOURCE_ID_RE = re.compile(r"^[a-z][a-z0-9_]{2,63}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_STATE_LOCK = threading.RLock()

_ContractFetcher = Callable[[str, float, int], tuple[bytes, dict[str, Any]]]


class VSDFederatedSourceError(ValueError):
    """Raised when a reviewed-source scan crosses its trust boundary."""


def _text(value: Any, maximum: int) -> str:
    normalized = " ".join(str(value or "").split())
    return "".join(character for character in normalized if ord(character) >= 32)[
        :maximum
    ]


def _plain_https_url(value: Any, *, field: str) -> str:
    try:
        url = _canonical_url(value)
    except Exception as exc:  # noqa: BLE001
        raise VSDFederatedSourceError(f"{field} must be a canonical HTTPS URL") from exc
    parsed = urlsplit(url)
    host = (parsed.hostname or "").casefold()
    if parsed.query or parsed.fragment or parsed.username or parsed.password:
        raise VSDFederatedSourceError(f"{field} must be a plain HTTPS URL")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        if "." not in host:
            raise VSDFederatedSourceError(f"{field} must use a public DNS hostname")
    else:
        raise VSDFederatedSourceError(f"{field} must not use an IP literal")
    return url


def _bounded_strings(value: Any, *, field: str, maximum: int) -> list[str]:
    if (
        not isinstance(value, list)
        or not 1 <= len(value) <= maximum
        or any(not isinstance(item, str) or not 1 <= len(item) <= 100 for item in value)
    ):
        raise VSDFederatedSourceError(f"{field} must contain bounded strings")
    normalized = sorted(set(value), key=str.casefold)
    if normalized != value:
        raise VSDFederatedSourceError(f"{field} must be unique and sorted")
    return list(value)


def validate_federated_source_manifest(value: Any) -> dict[str, Any]:
    """Validate a reviewed manifest without granting operation-level trust."""
    required = {
        "format",
        "version",
        "catalog_id",
        "catalog_state",
        "reviewed_at",
        "review_policy",
        "execution_allowed",
        "automatic_registration",
        "sources",
        "manifest_sha256",
    }
    if not isinstance(value, dict) or set(value) != required:
        raise VSDFederatedSourceError("Federated source manifest structure is invalid")
    body = {key: item for key, item in value.items() if key != "manifest_sha256"}
    sources = value.get("sources")
    if (
        value["format"] != "vsd_federated_source_manifest_v1"
        or value["version"] != _VERSION
        or not _SOURCE_ID_RE.fullmatch(str(value.get("catalog_id", "")))
        or value["catalog_state"] != "reviewed_for_bounded_contract_discovery"
        or _timestamp(value["reviewed_at"]) != value["reviewed_at"]
        or value["review_policy"]
        != "Source review permits contract retrieval only; every operation remains inert until separate verification, approval, publication, and explicit loading."
        or value["execution_allowed"] is not False
        or value["automatic_registration"] is not False
        or value["manifest_sha256"] != _digest(body)
        or not isinstance(sources, list)
        or not 1 <= len(sources) <= _MAX_SOURCES
    ):
        raise VSDFederatedSourceError("Federated source manifest identity is invalid")

    source_keys = {
        "source_id",
        "name",
        "organization",
        "documentation_url",
        "specification_url",
        "runtime_base_url",
        "contract_format",
        "topics",
        "access",
        "trust_basis",
        "review_state",
        "execution_allowed",
        "source_sha256",
    }
    seen_ids: set[str] = set()
    seen_specs: set[str] = set()
    previous = ""
    for source in sources:
        if not isinstance(source, dict) or set(source) != source_keys:
            raise VSDFederatedSourceError("Federated source entry is invalid")
        source_body = {
            key: item for key, item in source.items() if key != "source_sha256"
        }
        source_id = source.get("source_id")
        specification_url = _plain_https_url(
            source.get("specification_url"), field="specification_url"
        )
        if (
            not isinstance(source_id, str)
            or not _SOURCE_ID_RE.fullmatch(source_id)
            or source_id in seen_ids
            or source_id.casefold() <= previous
            or specification_url != source["specification_url"]
            or specification_url in seen_specs
            or source["contract_format"] != "openapi"
            or source["access"] not in {"public", "registration", "mixed"}
            or source["trust_basis"]
            not in {"official_government", "official_project", "official_repository"}
            or source["review_state"] != "reviewed_contract_endpoint"
            or source["execution_allowed"] is not False
            or source["source_sha256"] != _digest(source_body)
        ):
            raise VSDFederatedSourceError("Federated source identity is invalid")
        if (
            _plain_https_url(source.get("documentation_url"), field="documentation_url")
            != source["documentation_url"]
            or _plain_https_url(
                source.get("runtime_base_url"), field="runtime_base_url"
            )
            != source["runtime_base_url"]
        ):
            raise VSDFederatedSourceError("Federated source URL is not canonical")
        if not _text(source.get("name"), 160) or not _text(
            source.get("organization"), 200
        ):
            raise VSDFederatedSourceError("Federated source metadata is incomplete")
        _bounded_strings(source.get("topics"), field="topics", maximum=12)
        seen_ids.add(source_id)
        seen_specs.add(specification_url)
        previous = source_id.casefold()
    return copy.deepcopy(value)


def load_federated_source_manifest(path: str | Path | None = None) -> dict[str, Any]:
    source = Path(path) if path is not None else _MANIFEST_PATH
    try:
        if source.stat().st_size > 2_000_000:
            raise VSDFederatedSourceError("Federated source manifest exceeds 2 MB")
        value = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise VSDFederatedSourceError(
            "Could not load the federated source manifest"
        ) from exc
    return validate_federated_source_manifest(value)


def _registry_context(
    inventory: Any, registry_tools: Iterable[dict[str, Any]]
) -> tuple[dict[str, Any], dict[tuple[str, str, str], list[str]], dict[str, list[str]]]:
    checked = validate_source_inventory(inventory)
    exact: dict[tuple[str, str, str], list[str]] = {}
    reviewed: list[dict[str, Any]] = []
    for config in registry_tools:
        if not isinstance(config, dict):
            continue
        identity = _operation_identity(config)
        name = _text(config.get("name"), 200)
        if name and all(identity):
            exact.setdefault(identity, []).append(name)
            reviewed.append({"name": name, "identity": list(identity)})
    for names in exact.values():
        names.sort(key=str.casefold)
    hosts = {entry["host"]: entry["tools"] for entry in checked["hosts"]}
    return (
        {
            "tool_count": checked["tool_count"],
            "host_count": checked["host_count"],
            "inventory_sha256": checked["inventory_sha256"],
            "reviewed_operation_count": len(exact),
            "reviewed_operation_sha256": _digest(
                sorted(reviewed, key=lambda item: item["name"].casefold())
            ),
        },
        exact,
        hosts,
    )


def _public_host(value: str) -> bool:
    host = (urlsplit(value).hostname or "").casefold()
    if not host or len(host) > 253 or "." not in host:
        return False
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return bool(re.fullmatch(r"[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?", host))
    return address.is_global


def _preview_config(
    source: dict[str, Any], candidate: dict[str, Any]
) -> tuple[dict[str, Any], str]:
    prefix = hashlib.sha256(source["source_id"].encode("utf-8")).hexdigest()[:8]
    name = f"VSDFederated{prefix}{candidate['candidate_id'][:12]}"
    config = build_openapi_tool_config(
        candidate,
        tool_name=name,
        description=(
            f"Unapproved federated-source preview for {candidate['api_title']} "
            f"operation {candidate['operation_id']}."
        )[:1_000],
        credential_env=(
            "TOOLUNIVERSE_VSD_FEDERATED_CREDENTIAL" if candidate.get("auth") else None
        ),
    )
    return config, _digest(config)


def _snapshot_contract(
    source: dict[str, Any],
    root: Path,
    *,
    fetcher: _ContractFetcher,
    timeout_seconds: float,
    max_bytes: int,
) -> tuple[Path, str, int]:
    url = source["specification_url"]
    raw, metadata = fetcher(url, timeout_seconds, max_bytes)
    if (
        not isinstance(raw, bytes)
        or metadata.get("url") != url
        or metadata.get("redirects") != 0
        or metadata.get("response_bytes") != len(raw)
        or not 1 <= len(raw) <= max_bytes
    ):
        raise VSDFederatedSourceError(
            "Contract fetch changed the reviewed URL or exceeded its byte boundary"
        )
    digest = hashlib.sha256(raw).hexdigest()
    destination = root / f"{digest}.contract"
    if destination.exists():
        if hashlib.sha256(destination.read_bytes()).hexdigest() != digest:
            raise VSDFederatedSourceError(
                "Existing contract snapshot failed digest verification"
            )
    else:
        _atomic_write(destination, raw)
    return destination, digest, len(raw)


def canonical_openapi_bytes(path: str | Path) -> tuple[bytes, str]:
    """Return deterministic JSON bytes for an already bounded OpenAPI document."""
    document, _ = load_openapi_document(path)
    raw = json.dumps(
        document,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    if not 1 <= len(raw) <= _MAX_CONTRACT_BYTES:
        raise VSDFederatedSourceError(
            "Canonical OpenAPI document exceeds the inspection byte boundary"
        )
    return raw, hashlib.sha256(raw).hexdigest()


def _previous_sources(previous: Any | None) -> tuple[str | None, dict[str, str]]:
    if previous is None:
        return None, {}
    checked = validate_federated_scan(previous)
    return checked["scan_id"], {
        item["source_id"]: item["semantic_sha256"] for item in checked["sources"]
    }


def build_federated_scan(
    manifest: Any,
    *,
    inventory: Any,
    registry_tools: Iterable[dict[str, Any]],
    snapshot_directory: str | Path,
    previous_scan: Any | None = None,
    timeout_seconds: float = 20,
    max_contract_bytes: int = _MAX_CONTRACT_BYTES,
    contract_fetcher: _ContractFetcher = _fetch_https,
    scanned_at: str | None = None,
) -> dict[str, Any]:
    """Inspect every reviewed source while leaving all operations inert."""
    checked_manifest = validate_federated_source_manifest(manifest)
    if not isinstance(timeout_seconds, (int, float)) or not 1 <= timeout_seconds <= 60:
        raise VSDFederatedSourceError("timeout_seconds must be between 1 and 60")
    if (
        type(max_contract_bytes) is not int
        or not 1 <= max_contract_bytes <= _MAX_CONTRACT_BYTES
    ):
        raise VSDFederatedSourceError(
            "max_contract_bytes must be between 1 and 1000000"
        )
    previous_scan_id, previous_content = _previous_sources(previous_scan)
    registry, exact_operations, host_tools = _registry_context(
        inventory, registry_tools
    )
    root = Path(snapshot_directory).expanduser()
    root.mkdir(parents=True, exist_ok=True)
    os.chmod(root, 0o700)

    sources: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    operations: list[dict[str, Any]] = []
    blocker_counts: dict[str, int] = {}
    identity_owner: dict[tuple[str, str, str], str] = {}
    for source in checked_manifest["sources"]:
        source_counts = {
            "candidate_count": 0,
            "structurally_draftable_count": 0,
            "preview_count": 0,
            "existing_exact_count": 0,
            "existing_host_gap_count": 0,
            "new_host_candidate_count": 0,
            "duplicate_source_operation_count": 0,
            "blocked_count": 0,
        }
        try:
            raw_path, content_sha256, response_bytes = _snapshot_contract(
                source,
                root,
                fetcher=contract_fetcher,
                timeout_seconds=timeout_seconds,
                max_bytes=max_contract_bytes,
            )
            canonical_raw, semantic_sha256 = canonical_openapi_bytes(raw_path)
            path = root / f"{semantic_sha256}.openapi.json"
            if path.exists():
                if path.read_bytes() != canonical_raw:
                    raise VSDFederatedSourceError(
                        "Canonical contract snapshot failed digest verification"
                    )
            else:
                _atomic_write(path, canonical_raw)
            report = inspect_openapi_document(
                path, server_url_override=source["runtime_base_url"]
            )
            candidates = report["candidates"]
            source_counts["candidate_count"] = len(candidates)
            if len(operations) + len(candidates) > _MAX_OPERATIONS:
                raise VSDFederatedSourceError(
                    "Federated scan exceeds 25000 operation summaries"
                )
            for candidate in candidates:
                blockers = sorted(
                    {
                        item
                        for item in candidate.get("blockers", [])
                        if isinstance(item, str) and item
                    }
                )
                if not blockers and not _public_host(candidate.get("server_url", "")):
                    blockers = ["server_host_not_publicly_addressable"]
                for blocker in blockers:
                    blocker_counts[blocker] = blocker_counts.get(blocker, 0) + 1
                preview: dict[str, str] | None = None
                coverage = "blocked"
                matches: list[str] = []
                duplicate_of: str | None = None
                identity = (
                    str(candidate.get("method") or "").upper(),
                    (
                        urlsplit(candidate.get("server_url", "")).hostname or ""
                    ).casefold(),
                    str(candidate.get("path") or ""),
                )
                if not blockers:
                    source_counts["structurally_draftable_count"] += 1
                    try:
                        config, config_sha256 = _preview_config(source, candidate)
                        identity = _operation_identity(config)
                        if not all(identity):
                            raise VSDFederatedSourceError(
                                "Preview operation identity is incomplete"
                            )
                        matches = exact_operations.get(identity, [])
                        duplicate_of = identity_owner.get(identity)
                        identity_owner.setdefault(identity, source["source_id"])
                        if matches:
                            coverage = "existing_exact"
                            source_counts["existing_exact_count"] += 1
                        elif duplicate_of is not None:
                            coverage = "duplicate_federated_source"
                            source_counts["duplicate_source_operation_count"] += 1
                        else:
                            host = identity[1]
                            coverage = (
                                "existing_host_gap"
                                if host in host_tools
                                else "candidate_gap"
                            )
                            count_key = (
                                "existing_host_gap_count"
                                if coverage == "existing_host_gap"
                                else "new_host_candidate_count"
                            )
                            source_counts[count_key] += 1
                            preview = {
                                "tool_name": config["name"],
                                "config_sha256": config_sha256,
                            }
                            source_counts["preview_count"] += 1
                    except Exception:  # noqa: BLE001
                        source_counts["structurally_draftable_count"] -= 1
                        blockers = ["preview_generation_failed"]
                        blocker_counts["preview_generation_failed"] = (
                            blocker_counts.get("preview_generation_failed", 0) + 1
                        )
                        coverage = "blocked"
                if blockers:
                    source_counts["blocked_count"] += 1
                parameters = candidate.get("parameters", [])
                operations.append(
                    {
                        "source_id": source["source_id"],
                        "content_sha256": content_sha256,
                        "candidate_id": _text(candidate.get("candidate_id"), 32),
                        "candidate_sha256": _text(
                            candidate.get("candidate_sha256"), 64
                        ),
                        "api_title": _text(candidate.get("api_title"), 300),
                        "api_version": _text(candidate.get("api_version"), 100),
                        "operation_id": _text(candidate.get("operation_id"), 300),
                        "method": _text(candidate.get("method"), 20),
                        "host": identity[1],
                        "path": _text(identity[2], 500),
                        "parameter_count": len(parameters),
                        "required_parameter_count": sum(
                            isinstance(item, dict) and item.get("required") is True
                            for item in parameters
                        ),
                        "authenticated": candidate.get("auth") is not None,
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
                        "duplicate_of_source_id": duplicate_of,
                        "preview": preview,
                        "approval_state": "unreviewed_operation_candidate",
                        "execution_allowed": False,
                    }
                )
            sources.append(
                {
                    "source_id": source["source_id"],
                    "source_sha256": source["source_sha256"],
                    "specification_url": source["specification_url"],
                    "runtime_base_url": source["runtime_base_url"],
                    "content_sha256": content_sha256,
                    "semantic_sha256": semantic_sha256,
                    "response_bytes": response_bytes,
                    "snapshot_file": raw_path.name,
                    "inspection_snapshot_file": path.name,
                    "api_title": report["api_title"],
                    "api_version": report["api_version"],
                    "openapi_version": report["openapi_version"],
                    "inspection_sha256": _digest(report),
                    **source_counts,
                }
            )
        except Exception as exc:  # noqa: BLE001
            failures.append(
                {
                    "source_id": source["source_id"],
                    "source_sha256": source["source_sha256"],
                    "error_type": type(exc).__name__[:100],
                    "message": _text(exc, 300) or "Contract inspection failed",
                }
            )

    current_semantic = {item["source_id"]: item["semantic_sha256"] for item in sources}
    current_content = {item["source_id"]: item["content_sha256"] for item in sources}
    previous_raw = (
        {
            item["source_id"]: item["content_sha256"]
            for item in validate_federated_scan(previous_scan)["sources"]
        }
        if previous_scan is not None
        else {}
    )
    previous_ids, current_ids = set(previous_content), set(current_semantic)
    changed = {
        source_id
        for source_id in previous_ids & current_ids
        if previous_content[source_id] != current_semantic[source_id]
    }
    representation_changed = {
        source_id
        for source_id in set(previous_raw) & set(current_content)
        if previous_raw[source_id] != current_content[source_id]
        and previous_content[source_id] == current_semantic[source_id]
    }
    metrics = {
        "manifest_source_count": len(checked_manifest["sources"]),
        "successful_source_count": len(sources),
        "failed_source_count": len(failures),
        "operation_candidate_count": len(operations),
        "unique_operation_identity_count": len(
            {
                (item["method"], item["host"], item["path"])
                for item in operations
                if item["method"] and item["host"] and item["path"]
            }
        ),
        "structurally_draftable_count": sum(
            item["structurally_draftable_count"] for item in sources
        ),
        "net_new_preview_count": sum(item["preview_count"] for item in sources),
        "existing_exact_operation_count": sum(
            item["existing_exact_count"] for item in sources
        ),
        "existing_host_gap_count": sum(
            item["existing_host_gap_count"] for item in sources
        ),
        "new_host_candidate_count": sum(
            item["new_host_candidate_count"] for item in sources
        ),
        "duplicate_source_operation_count": sum(
            item["duplicate_source_operation_count"] for item in sources
        ),
        "blocked_operation_count": sum(item["blocked_count"] for item in sources),
    }
    body = {
        "format": "vsd_federated_source_scan_v1",
        "version": _VERSION,
        "scanned_at": _timestamp(scanned_at),
        "previous_scan_id": previous_scan_id,
        "manifest": checked_manifest,
        "registry": registry,
        "limits": {
            "timeout_seconds": timeout_seconds,
            "max_contract_bytes": max_contract_bytes,
        },
        "source_delta": {
            "added_source_ids": sorted(current_ids - previous_ids),
            "removed_source_ids": sorted(previous_ids - current_ids),
            "changed_source_ids": sorted(changed),
            "representation_changed_source_ids": sorted(representation_changed),
            "unchanged_source_ids": sorted((previous_ids & current_ids) - changed),
        },
        "sources": sources,
        "failures": failures,
        "operations": operations,
        "blocker_counts": dict(sorted(blocker_counts.items())),
        "metrics": metrics,
        "approval_state": "unreviewed_federated_scan",
        "execution_allowed": False,
        "automatic_publication": False,
        "transmission": "none; local review is required before explicit handoff",
        "boundary": (
            "Reviewed source metadata permits bounded contract retrieval only. Preview "
            "hashes are unverified, unapproved, unpublished, unloaded, and non-executable."
        ),
    }
    digest = _digest(body)
    return {**body, "scan_id": digest[:16], "scan_sha256": digest}


def validate_federated_scan(value: Any) -> dict[str, Any]:
    required = {
        "format",
        "version",
        "scanned_at",
        "previous_scan_id",
        "manifest",
        "registry",
        "limits",
        "source_delta",
        "sources",
        "failures",
        "operations",
        "blocker_counts",
        "metrics",
        "approval_state",
        "execution_allowed",
        "automatic_publication",
        "transmission",
        "boundary",
        "scan_id",
        "scan_sha256",
    }
    if not isinstance(value, dict) or set(value) != required:
        raise VSDFederatedSourceError("Federated scan structure is invalid")
    body = {
        key: item
        for key, item in value.items()
        if key not in {"scan_id", "scan_sha256"}
    }
    sources = value.get("sources")
    failures = value.get("failures")
    operations = value.get("operations")
    metrics = value.get("metrics")
    if (
        value["format"] != "vsd_federated_source_scan_v1"
        or value["version"] != _VERSION
        or _timestamp(value["scanned_at"]) != value["scanned_at"]
        or value["approval_state"] != "unreviewed_federated_scan"
        or value["execution_allowed"] is not False
        or value["automatic_publication"] is not False
        or value["scan_sha256"] != _digest(body)
        or value["scan_id"] != value["scan_sha256"][:16]
        or not isinstance(sources, list)
        or not isinstance(failures, list)
        or not isinstance(operations, list)
        or len(operations) > _MAX_OPERATIONS
        or not isinstance(metrics, dict)
    ):
        raise VSDFederatedSourceError("Federated scan identity is invalid")
    manifest = validate_federated_source_manifest(value["manifest"])
    registry = value.get("registry")
    limits = value.get("limits")
    if (
        not isinstance(registry, dict)
        or set(registry)
        != {
            "tool_count",
            "host_count",
            "inventory_sha256",
            "reviewed_operation_count",
            "reviewed_operation_sha256",
        }
        or any(
            type(registry.get(key)) is not int or registry[key] < 0
            for key in {
                "tool_count",
                "host_count",
                "reviewed_operation_count",
            }
        )
        or not _SHA256_RE.fullmatch(str(registry.get("inventory_sha256", "")))
        or not _SHA256_RE.fullmatch(str(registry.get("reviewed_operation_sha256", "")))
        or not isinstance(limits, dict)
        or set(limits) != {"timeout_seconds", "max_contract_bytes"}
        or not isinstance(limits.get("timeout_seconds"), (int, float))
        or not 1 <= limits["timeout_seconds"] <= 60
        or type(limits.get("max_contract_bytes")) is not int
        or not 1 <= limits["max_contract_bytes"] <= _MAX_CONTRACT_BYTES
        or (
            value.get("previous_scan_id") is not None
            and not re.fullmatch(r"[0-9a-f]{16}", str(value["previous_scan_id"]))
        )
        or value.get("transmission")
        != "none; local review is required before explicit handoff"
    ):
        raise VSDFederatedSourceError("Federated scan context is invalid")
    expected_metric_keys = {
        "manifest_source_count",
        "successful_source_count",
        "failed_source_count",
        "operation_candidate_count",
        "unique_operation_identity_count",
        "structurally_draftable_count",
        "net_new_preview_count",
        "existing_exact_operation_count",
        "existing_host_gap_count",
        "new_host_candidate_count",
        "duplicate_source_operation_count",
        "blocked_operation_count",
    }
    expected_source_keys = {
        "source_id",
        "source_sha256",
        "specification_url",
        "runtime_base_url",
        "content_sha256",
        "semantic_sha256",
        "response_bytes",
        "snapshot_file",
        "inspection_snapshot_file",
        "api_title",
        "api_version",
        "openapi_version",
        "inspection_sha256",
        "candidate_count",
        "structurally_draftable_count",
        "preview_count",
        "existing_exact_count",
        "existing_host_gap_count",
        "new_host_candidate_count",
        "duplicate_source_operation_count",
        "blocked_count",
    }
    expected_operation_keys = {
        "source_id",
        "content_sha256",
        "candidate_id",
        "candidate_sha256",
        "api_title",
        "api_version",
        "operation_id",
        "method",
        "host",
        "path",
        "parameter_count",
        "required_parameter_count",
        "authenticated",
        "blockers",
        "warnings",
        "registry_coverage",
        "existing_tools",
        "duplicate_of_source_id",
        "preview",
        "approval_state",
        "execution_allowed",
    }
    expected_delta_keys = {
        "added_source_ids",
        "removed_source_ids",
        "changed_source_ids",
        "representation_changed_source_ids",
        "unchanged_source_ids",
    }
    if (
        set(metrics) != expected_metric_keys
        or metrics.get("manifest_source_count") != len(manifest["sources"])
        or metrics.get("successful_source_count") != len(sources)
        or metrics.get("failed_source_count") != len(failures)
        or metrics.get("operation_candidate_count") != len(operations)
        or len(sources) + len(failures) != len(manifest["sources"])
        or metrics.get("net_new_preview_count")
        != sum(item.get("preview") is not None for item in operations)
        or metrics.get("blocked_operation_count")
        != sum(bool(item.get("blockers")) for item in operations)
    ):
        raise VSDFederatedSourceError("Federated scan metrics do not match evidence")
    known_sources = {item["source_id"] for item in manifest["sources"]}
    manifest_by_id = {item["source_id"]: item for item in manifest["sources"]}
    observed_sources = {item.get("source_id") for item in [*sources, *failures]}
    successful_source_ids = {item.get("source_id") for item in sources}
    delta = value.get("source_delta")
    delta_lists = list(delta.values()) if isinstance(delta, dict) else []
    primary_delta_keys = {
        "added_source_ids",
        "removed_source_ids",
        "changed_source_ids",
        "unchanged_source_ids",
    }
    primary_delta_lists = (
        [delta[key] for key in primary_delta_keys]
        if isinstance(delta, dict) and set(delta) == expected_delta_keys
        else []
    )
    if (
        observed_sources != known_sources
        or len(observed_sources) != len(sources) + len(failures)
        or not isinstance(delta, dict)
        or set(delta) != expected_delta_keys
        or any(
            not isinstance(items, list)
            or items != sorted(set(items))
            or any(not _SOURCE_ID_RE.fullmatch(str(item)) for item in items)
            for items in delta_lists
        )
        or sum(len(items) for items in primary_delta_lists)
        != len(set().union(*(set(items) for items in primary_delta_lists)))
        or (
            isinstance(delta, dict)
            and not set(delta.get("representation_changed_source_ids", []))
            <= set(delta.get("unchanged_source_ids", []))
        )
        or (
            isinstance(delta, dict)
            and not set(
                delta.get("added_source_ids", [])
                + delta.get("changed_source_ids", [])
                + delta.get("unchanged_source_ids", [])
            )
            <= successful_source_ids
        )
        or (
            isinstance(delta, dict)
            and set(delta.get("removed_source_ids", [])) & known_sources
        )
        or not isinstance(value.get("blocker_counts"), dict)
        or any(
            not isinstance(key, str) or not key or type(count) is not int or count < 1
            for key, count in value["blocker_counts"].items()
        )
    ):
        raise VSDFederatedSourceError("Federated scan source coverage is incomplete")
    operations_by_source: dict[str, list[dict[str, Any]]] = {
        source_id: [] for source_id in known_sources
    }
    observed_blockers: dict[str, int] = {}
    for operation in operations:
        if (
            not isinstance(operation, dict)
            or set(operation) != expected_operation_keys
            or operation.get("source_id") not in known_sources
            or operation.get("approval_state") != "unreviewed_operation_candidate"
            or operation.get("execution_allowed") is not False
            or not _SHA256_RE.fullmatch(str(operation.get("content_sha256", "")))
            or not _SHA256_RE.fullmatch(str(operation.get("candidate_sha256", "")))
            or operation.get("candidate_id")
            != str(operation.get("candidate_sha256"))[:16]
            or not re.fullmatch(r"[A-Z]+", str(operation.get("method", "")))
            or not operation.get("host")
            or not str(operation.get("path", "")).startswith("/")
            or type(operation.get("parameter_count")) is not int
            or type(operation.get("required_parameter_count")) is not int
            or not 0
            <= operation["required_parameter_count"]
            <= operation["parameter_count"]
            or type(operation.get("authenticated")) is not bool
            or not isinstance(operation.get("blockers"), list)
            or operation["blockers"] != sorted(set(operation["blockers"]))
            or any(
                not isinstance(item, str) or not item for item in operation["blockers"]
            )
            or not isinstance(operation.get("warnings"), list)
            or operation["warnings"] != sorted(set(operation["warnings"]))
            or operation.get("registry_coverage")
            not in {
                "blocked",
                "candidate_gap",
                "existing_host_gap",
                "existing_exact",
                "duplicate_federated_source",
            }
            or not isinstance(operation.get("existing_tools"), list)
            or operation["existing_tools"]
            != sorted(set(operation["existing_tools"]), key=str.casefold)
        ):
            raise VSDFederatedSourceError("Federated operation crossed its boundary")
        operations_by_source[operation["source_id"]].append(operation)
        for blocker in operation["blockers"]:
            observed_blockers[blocker] = observed_blockers.get(blocker, 0) + 1
        preview = operation.get("preview")
        if preview is not None and (
            not isinstance(preview, dict)
            or set(preview) != {"tool_name", "config_sha256"}
            or not _SHA256_RE.fullmatch(str(preview.get("config_sha256", "")))
            or operation.get("blockers")
            or operation.get("registry_coverage")
            not in {"candidate_gap", "existing_host_gap"}
        ):
            raise VSDFederatedSourceError("Federated preview evidence is invalid")
        coverage = operation["registry_coverage"]
        if (
            (coverage == "blocked") != bool(operation["blockers"])
            or (coverage == "existing_exact") != bool(operation["existing_tools"])
            or (
                coverage == "duplicate_federated_source"
                and operation["duplicate_of_source_id"] is None
            )
            or operation["duplicate_of_source_id"] not in known_sources | {None}
            or (preview is not None)
            != (coverage in {"candidate_gap", "existing_host_gap"})
        ):
            raise VSDFederatedSourceError(
                "Federated operation coverage is inconsistent"
            )
    if dict(sorted(observed_blockers.items())) != value["blocker_counts"]:
        raise VSDFederatedSourceError("Federated blocker counts do not match evidence")
    for failure in failures:
        if (
            not isinstance(failure, dict)
            or set(failure) != {"source_id", "source_sha256", "error_type", "message"}
            or failure.get("source_id") not in manifest_by_id
            or failure.get("source_sha256")
            != manifest_by_id[failure["source_id"]]["source_sha256"]
            or not _text(failure.get("error_type"), 100)
            or not _text(failure.get("message"), 300)
        ):
            raise VSDFederatedSourceError("Federated source failure is invalid")
    for source in sources:
        if (
            not isinstance(source, dict)
            or set(source) != expected_source_keys
            or source.get("source_id") not in manifest_by_id
            or source.get("source_sha256")
            != manifest_by_id[source["source_id"]]["source_sha256"]
            or source.get("specification_url")
            != manifest_by_id[source["source_id"]]["specification_url"]
            or source.get("runtime_base_url")
            != manifest_by_id[source["source_id"]]["runtime_base_url"]
            or not _SHA256_RE.fullmatch(str(source.get("content_sha256", "")))
            or not _SHA256_RE.fullmatch(str(source.get("semantic_sha256", "")))
            or not _SHA256_RE.fullmatch(str(source.get("inspection_sha256", "")))
            or source.get("snapshot_file") != f"{source.get('content_sha256')}.contract"
            or source.get("inspection_snapshot_file")
            != f"{source.get('semantic_sha256')}.openapi.json"
            or type(source.get("response_bytes")) is not int
            or not 1
            <= source["response_bytes"]
            <= value["limits"]["max_contract_bytes"]
        ):
            raise VSDFederatedSourceError("Federated source digest evidence is invalid")
        source_operations = operations_by_source[source["source_id"]]
        if any(
            item["content_sha256"] != source["content_sha256"]
            for item in source_operations
        ):
            raise VSDFederatedSourceError(
                "Federated operation does not match its source snapshot"
            )
        source_metrics = {
            "candidate_count": len(source_operations),
            "structurally_draftable_count": sum(
                not item["blockers"] for item in source_operations
            ),
            "preview_count": sum(
                item["preview"] is not None for item in source_operations
            ),
            "existing_exact_count": sum(
                item["registry_coverage"] == "existing_exact"
                for item in source_operations
            ),
            "existing_host_gap_count": sum(
                item["registry_coverage"] == "existing_host_gap"
                for item in source_operations
            ),
            "new_host_candidate_count": sum(
                item["registry_coverage"] == "candidate_gap"
                for item in source_operations
            ),
            "duplicate_source_operation_count": sum(
                item["registry_coverage"] == "duplicate_federated_source"
                for item in source_operations
            ),
            "blocked_count": sum(bool(item["blockers"]) for item in source_operations),
        }
        if any(source[key] != count for key, count in source_metrics.items()):
            raise VSDFederatedSourceError(
                "Federated source metrics do not match operation evidence"
            )
    expected_metrics = {
        "manifest_source_count": len(manifest["sources"]),
        "successful_source_count": len(sources),
        "failed_source_count": len(failures),
        "operation_candidate_count": len(operations),
        "unique_operation_identity_count": len(
            {(item["method"], item["host"], item["path"]) for item in operations}
        ),
        "structurally_draftable_count": sum(
            not item["blockers"] for item in operations
        ),
        "net_new_preview_count": sum(
            item["preview"] is not None for item in operations
        ),
        "existing_exact_operation_count": sum(
            item["registry_coverage"] == "existing_exact" for item in operations
        ),
        "existing_host_gap_count": sum(
            item["registry_coverage"] == "existing_host_gap" for item in operations
        ),
        "new_host_candidate_count": sum(
            item["registry_coverage"] == "candidate_gap" for item in operations
        ),
        "duplicate_source_operation_count": sum(
            item["registry_coverage"] == "duplicate_federated_source"
            for item in operations
        ),
        "blocked_operation_count": sum(bool(item["blockers"]) for item in operations),
    }
    if metrics != expected_metrics or any(
        type(item) is not int for item in metrics.values()
    ):
        raise VSDFederatedSourceError("Federated scan totals do not match evidence")
    return copy.deepcopy(value)


def summarize_federated_scan(value: Any) -> dict[str, Any]:
    checked = validate_federated_scan(value)
    return {
        "scan_id": checked["scan_id"],
        "scanned_at": checked["scanned_at"],
        **copy.deepcopy(checked["metrics"]),
    }


def _state_root(value: str | Path) -> Path:
    root = Path(value).expanduser()
    root.mkdir(parents=True, exist_ok=True)
    os.chmod(root, 0o700)
    return root


@contextmanager
def _state_transaction(path: str | Path) -> Iterator[Path]:
    with _STATE_LOCK:
        root = _state_root(path)
        lock_path = root / ".federated-source-scanner.lock"
        with lock_path.open("a+b") as handle:
            if handle.seek(0, os.SEEK_END) == 0:
                handle.write(b"\0")
                handle.flush()
            _acquire_process_lock(handle)
            try:
                yield root
            finally:
                _release_process_lock(handle)


def _read_report(path: Path) -> dict[str, Any]:
    try:
        if path.stat().st_size > _MAX_REPORT_BYTES:
            raise VSDFederatedSourceError("Federated scan report exceeds 50 MB")
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise VSDFederatedSourceError("Federated scan report is unreadable") from exc
    return validate_federated_scan(value)


def load_latest_federated_scan(
    state_directory: str | Path,
) -> dict[str, Any] | None:
    path = _state_root(state_directory) / "latest.json"
    return _read_report(path) if path.exists() else None


def _write_report(root: Path, report: Any) -> tuple[Path, Path]:
    checked = validate_federated_scan(report)
    raw = (
        json.dumps(checked, indent=2, sort_keys=True, ensure_ascii=True).encode("utf-8")
        + b"\n"
    )
    history = root / f"scan-{checked['scan_id']}.json"
    if history.exists() and history.read_bytes() != raw:
        raise VSDFederatedSourceError("Immutable federated scan was modified")
    if not history.exists():
        _atomic_write(history, raw)
    latest = root / "latest.json"
    _atomic_write(latest, raw)
    return history, latest


def run_federated_source_scan(
    tooluniverse: Any,
    state_directory: str | Path,
    *,
    manifest_path: str | Path | None = None,
    timeout_seconds: float = 20,
    max_contract_bytes: int = _MAX_CONTRACT_BYTES,
    contract_fetcher: _ContractFetcher = _fetch_https,
    scanned_at: str | None = None,
) -> dict[str, Any]:
    """Run a serialized full-manifest scan suitable for cron or a scheduler."""
    with _state_transaction(state_directory) as root:
        latest_path = root / "latest.json"
        previous = _read_report(latest_path) if latest_path.exists() else None
        manifest = load_federated_source_manifest(manifest_path)
        if previous and (previous["manifest"]["catalog_id"] != manifest["catalog_id"]):
            raise VSDFederatedSourceError("Scanner state belongs to another manifest")
        report = build_federated_scan(
            manifest,
            inventory=configured_source_inventory(tooluniverse),
            registry_tools=_registry_tools(tooluniverse),
            snapshot_directory=root / "contracts",
            previous_scan=previous,
            timeout_seconds=timeout_seconds,
            max_contract_bytes=max_contract_bytes,
            contract_fetcher=contract_fetcher,
            scanned_at=scanned_at,
        )
        history, latest = _write_report(root, report)
        return {
            "scan": report,
            "history_file": str(history),
            "latest_file": str(latest),
            "snapshot_directory": str(root / "contracts"),
        }


__all__ = [
    "VSDFederatedSourceError",
    "build_federated_scan",
    "canonical_openapi_bytes",
    "load_federated_source_manifest",
    "load_latest_federated_scan",
    "run_federated_source_scan",
    "summarize_federated_scan",
    "validate_federated_scan",
    "validate_federated_source_manifest",
]
