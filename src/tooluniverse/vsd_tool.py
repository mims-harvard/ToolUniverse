"""Safe, explicit Verified Source Directory (VSD) tools.

This module implements the smallest complete VSD workflow:

1. discover a packaged set of trusted public JSON sources,
2. probe and persist a source explicitly,
3. query only a previously registered source, and
4. list or remove persisted sources.

It deliberately does not auto-harvest arbitrary URLs, auto-run generated tools,
or expose container provisioning. Network access is HTTPS GET-only, host
allowlisted, redirect-validated, size-limited, and checked against private,
loopback, link-local, reserved, and other non-global addresses.
"""

from __future__ import annotations

import ipaddress
import json
import math
import os
import re
import socket
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlsplit

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

_CATALOG_LOCK = threading.RLock()
_CATALOG_VERSION = 1
_MAX_RESPONSE_BYTES = 1_000_000
_MAX_REDIRECTS = 3
_SOURCE_ID_RE = re.compile(r"^[a-z][a-z0-9_]{2,63}$")
_CREDENTIAL_KEY_RE = re.compile(
    r"(?:api[_-]?key|access[_-]?key|(?:^|[_-])key(?:$|[_-])|token|secret|"
    r"password|authorization|credential|signature|bearer|jwt|session)",
    re.IGNORECASE,
)

# Exact hosts only. Additional exact hosts require an explicit administrator or
# user opt-in through TOOLUNIVERSE_VSD_ALLOWED_HOSTS.
_BUILTIN_ALLOWED_HOSTS = frozenset(
    {
        "api.fda.gov",
        "api.reporter.nih.gov",
        "chronicdata.cdc.gov",
        "clinicaltrials.gov",
        "data.cdc.gov",
        "eutils.ncbi.nlm.nih.gov",
        "ghoapi.azureedge.net",
        "rest.ensembl.org",
        "www.ema.europa.eu",
    }
)

_PACKAGED_SOURCES = (
    {
        "source_id": "who_gho",
        "name": "WHO Global Health Observatory",
        "endpoint": "https://ghoapi.azureedge.net/api/Indicator",
        "description": "WHO global-health indicators exposed as JSON/OData.",
        "default_params": {"$top": 5},
    },
    {
        "source_id": "openfda_labels",
        "name": "openFDA Drug Labels",
        "endpoint": "https://api.fda.gov/drug/label.json",
        "description": "FDA drug labeling records, warnings, and indications.",
        "default_params": {"limit": 5},
    },
    {
        "source_id": "cdc_places",
        "name": "CDC PLACES",
        "endpoint": "https://chronicdata.cdc.gov/resource/cwsq-ngmh.json",
        "description": "CDC local chronic-disease and preventive-service estimates.",
        "default_params": {"$limit": 5},
    },
    {
        "source_id": "ensembl_ping",
        "name": "Ensembl REST",
        "endpoint": "https://rest.ensembl.org/info/ping",
        "description": "Ensembl REST JSON heartbeat and service entry point.",
        "default_params": {},
    },
)


class VSDPolicyError(ValueError):
    """Raised when a source violates the VSD network or credential policy."""


def _catalog_path() -> Path:
    configured = os.environ.get("TOOLUNIVERSE_VSD_DIR")
    base = (
        Path(configured).expanduser()
        if configured
        else Path.home() / ".tooluniverse" / "vsd"
    )
    return base / "sources.json"


def _empty_catalog() -> dict[str, Any]:
    return {"version": _CATALOG_VERSION, "sources": {}}


def _load_catalog() -> dict[str, Any]:
    path = _catalog_path()
    if not path.exists():
        return _empty_catalog()

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"VSD catalog is unreadable: {path}") from exc

    if (
        not isinstance(data, dict)
        or data.get("version") != _CATALOG_VERSION
        or not isinstance(data.get("sources"), dict)
    ):
        raise ValueError(f"VSD catalog has an unsupported structure: {path}")
    return data


def _write_catalog(catalog: dict[str, Any]) -> Path:
    path = _catalog_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".vsd_sources_", suffix=".json", dir=path.parent
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(catalog, handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.chmod(temporary_path, 0o600)
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)
    return path


def _allowed_hosts() -> frozenset[str]:
    configured = os.environ.get("TOOLUNIVERSE_VSD_ALLOWED_HOSTS", "")
    extras = {
        item.strip().lower().rstrip(".")
        for item in configured.split(",")
        if item.strip()
    }
    return frozenset((*_BUILTIN_ALLOWED_HOSTS, *extras))


def _normalize_host(host: str) -> str:
    try:
        return host.encode("idna").decode("ascii").lower().rstrip(".")
    except UnicodeError as exc:
        raise VSDPolicyError("Source hostname is not valid IDNA") from exc


def _require_global_ip(address: str, *, context: str) -> None:
    try:
        parsed = ipaddress.ip_address(address)
    except ValueError as exc:
        raise VSDPolicyError(f"{context} did not produce a valid IP address") from exc
    if not parsed.is_global:
        raise VSDPolicyError(f"{context} resolved to prohibited address {parsed}")


def _resolve_public_addresses(host: str, port: int) -> tuple[str, ...]:
    try:
        records = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise VSDPolicyError(f"Could not resolve source host {host!r}") from exc

    addresses = tuple(sorted({record[4][0] for record in records}))
    if not addresses:
        raise VSDPolicyError(f"Source host {host!r} resolved to no addresses")
    for address in addresses:
        _require_global_ip(address, context=f"Source host {host!r}")
    return addresses


def validate_source_url(url: str) -> str:
    """Validate and normalize one VSD source URL before every request."""
    if not isinstance(url, str) or not url or len(url) > 2048:
        raise VSDPolicyError(
            "Source URL must be a non-empty string of at most 2048 characters"
        )
    if any(ord(character) < 32 for character in url):
        raise VSDPolicyError("Source URL contains control characters")

    parsed = urlsplit(url)
    if parsed.scheme.lower() != "https":
        raise VSDPolicyError("VSD sources must use HTTPS")
    if not parsed.hostname:
        raise VSDPolicyError("Source URL must include a hostname")
    if parsed.username is not None or parsed.password is not None:
        raise VSDPolicyError("Credentials are not allowed in source URLs")
    if parsed.query:
        raise VSDPolicyError(
            "Source endpoints must not contain query strings; use default_params"
        )
    if parsed.fragment:
        raise VSDPolicyError("Source URLs must not contain fragments")

    host = _normalize_host(parsed.hostname)
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise VSDPolicyError("IP-literal source URLs are not allowed")

    try:
        port = parsed.port
    except ValueError as exc:
        raise VSDPolicyError("Source URL contains an invalid port") from exc
    if port not in (None, 443):
        raise VSDPolicyError("VSD sources may use only the standard HTTPS port")
    if host not in _allowed_hosts():
        raise VSDPolicyError(
            f"Source host {host!r} is not allowlisted; add an exact host to "
            "TOOLUNIVERSE_VSD_ALLOWED_HOSTS to opt in"
        )

    _resolve_public_addresses(host, 443)
    return parsed.geturl()


def _validated_params(params: Any) -> dict[str, Any]:
    if params is None:
        return {}
    if not isinstance(params, dict):
        raise VSDPolicyError("Query parameters must be an object")
    if len(params) > 50:
        raise VSDPolicyError("At most 50 query parameters are allowed")

    validated: dict[str, Any] = {}
    for raw_key, value in params.items():
        if not isinstance(raw_key, str) or not raw_key or len(raw_key) > 128:
            raise VSDPolicyError("Query parameter names must be non-empty strings")
        if _CREDENTIAL_KEY_RE.search(raw_key):
            raise VSDPolicyError(
                f"Credential-like query parameter {raw_key!r} is prohibited; "
                "VSD credentials must come from environment-backed dedicated tools"
            )
        values = value if isinstance(value, list) else [value]
        if len(values) > 50 or any(
            not isinstance(item, (str, int, float, bool)) for item in values
        ):
            raise VSDPolicyError(
                f"Query parameter {raw_key!r} must contain scalar JSON values"
            )
        if any(isinstance(item, float) and not math.isfinite(item) for item in values):
            raise VSDPolicyError(
                f"Query parameter {raw_key!r} contains a non-finite number"
            )
        for item in values:
            if isinstance(item, str):
                if len(item) > 4096:
                    raise VSDPolicyError(
                        f"Query parameter {raw_key!r} contains a string longer "
                        "than 4096 characters"
                    )
                if any(ord(character) < 32 for character in item):
                    raise VSDPolicyError(
                        f"Query parameter {raw_key!r} contains control characters"
                    )
        validated[raw_key] = value

    if len(json.dumps(validated)) > 16_384:
        raise VSDPolicyError("Encoded query parameters exceed 16 KiB")
    return validated


def _bounded_text(value: Any, *, field: str, maximum: int, fallback: str = "") -> str:
    text = str(value or fallback).strip()
    if len(text) > maximum:
        raise VSDPolicyError(f"{field} must be at most {maximum} characters")
    if any(ord(character) < 32 for character in text):
        raise VSDPolicyError(f"{field} contains control characters")
    return text


def _peer_address(response: requests.Response) -> str:
    raw = response.raw
    connection = getattr(raw, "_connection", None) or getattr(raw, "connection", None)
    sock = getattr(connection, "sock", None)
    if sock is None:
        try:
            sock = raw._fp.fp.raw._sock  # type: ignore[attr-defined]
        except AttributeError:
            sock = None
    if sock is None:
        raise VSDPolicyError("Could not verify the connected peer address")
    return str(sock.getpeername()[0])


def _safe_get_json(
    url: str,
    params: dict[str, Any] | None = None,
    *,
    timeout: float = 20.0,
    session: requests.Session | None = None,
) -> tuple[Any, dict[str, Any]]:
    """GET JSON with host, DNS, connected-peer, redirect, and size checks."""
    current_url = url
    current_params = _validated_params(params)
    owned_session = session is None
    http = session or requests.Session()
    http.trust_env = False

    try:
        for redirect_count in range(_MAX_REDIRECTS + 1):
            validate_source_url(current_url)
            response = http.get(
                current_url,
                params=current_params or None,
                headers={"Accept": "application/json"},
                timeout=(5.0, timeout),
                allow_redirects=False,
                stream=True,
            )
            try:
                peer_ip = _peer_address(response)
                _require_global_ip(peer_ip, context="Connected peer")

                if response.status_code in {301, 302, 303, 307, 308}:
                    location = response.headers.get("Location")
                    if not location:
                        raise VSDPolicyError("Redirect response omitted Location")
                    if redirect_count == _MAX_REDIRECTS:
                        raise VSDPolicyError("Source exceeded the redirect limit")
                    current_url = urljoin(current_url, location)
                    current_params = {}
                    continue

                response.raise_for_status()
                content_type = response.headers.get("Content-Type", "").lower()
                if "json" not in content_type:
                    raise VSDPolicyError(
                        f"Source returned non-JSON content type {content_type!r}"
                    )

                declared_length = response.headers.get("Content-Length")
                if declared_length:
                    try:
                        parsed_length = int(declared_length)
                    except (TypeError, ValueError) as exc:
                        raise VSDPolicyError(
                            "Source returned an invalid Content-Length"
                        ) from exc
                    if parsed_length < 0:
                        raise VSDPolicyError(
                            "Source returned an invalid Content-Length"
                        )
                    if parsed_length > _MAX_RESPONSE_BYTES:
                        raise VSDPolicyError("Source response exceeds the 1 MB limit")

                chunks: list[bytes] = []
                total = 0
                for chunk in response.iter_content(chunk_size=65_536):
                    if not chunk:
                        continue
                    total += len(chunk)
                    if total > _MAX_RESPONSE_BYTES:
                        raise VSDPolicyError("Source response exceeds the 1 MB limit")
                    chunks.append(chunk)
                try:
                    payload = json.loads(b"".join(chunks).decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                    raise VSDPolicyError(
                        "Source response is not valid UTF-8 JSON"
                    ) from exc
                return payload, {
                    "url": current_url,
                    "status_code": response.status_code,
                    "content_type": content_type,
                    "response_bytes": total,
                    "peer_ip": peer_ip,
                    "redirects": redirect_count,
                }
            finally:
                response.close()
    finally:
        if owned_session:
            http.close()

    raise VSDPolicyError("Source request did not produce a response")


def _source_id(arguments: dict[str, Any]) -> str:
    value = str(arguments.get("source_id") or "")
    if not _SOURCE_ID_RE.fullmatch(value):
        raise ValueError(
            "source_id must start with a lowercase letter and contain 3-64 "
            "lowercase letters, digits, or underscores"
        )
    return value


@register_tool("VSDDiscoverSources")
class VSDDiscoverSources(BaseTool):
    """Search the packaged, reviewed VSD source seeds without network access."""

    def run(self, arguments=None, **_: Any):
        arguments = arguments or {}
        query = _bounded_text(
            arguments.get("query"), field="query", maximum=500
        ).casefold()
        sources = [
            dict(source)
            for source in _PACKAGED_SOURCES
            if not query
            or query
            in " ".join(
                str(source.get(field, ""))
                for field in ("source_id", "name", "description", "endpoint")
            ).casefold()
        ]
        return {"status": "success", "data": {"sources": sources}}


@register_tool("VSDRegisterSource")
class VSDRegisterSource(BaseTool):
    """Probe and persist an explicitly trusted, public, JSON GET source."""

    def run(self, arguments=None, **_: Any):
        arguments = arguments or {}
        source_id = _source_id(arguments)
        endpoint = validate_source_url(str(arguments.get("endpoint") or ""))
        default_params = _validated_params(arguments.get("default_params"))
        payload, probe = _safe_get_json(endpoint, default_params)
        record = {
            "source_id": source_id,
            "name": _bounded_text(
                arguments.get("name"), field="name", maximum=200, fallback=source_id
            ),
            "description": _bounded_text(
                arguments.get("description"), field="description", maximum=2000
            ),
            "endpoint": endpoint,
            "host": _normalize_host(urlsplit(endpoint).hostname or ""),
            "default_params": default_params,
            "registered_at": datetime.now(timezone.utc).isoformat(),
            "last_probe": {
                **probe,
                "result_type": type(payload).__name__,
            },
        }
        with _CATALOG_LOCK:
            catalog = _load_catalog()
            catalog["sources"][source_id] = record
            path = _write_catalog(catalog)
        return {
            "status": "success",
            "data": {"registered": True, "source": record, "catalog_path": str(path)},
        }


@register_tool("VSDListSources")
class VSDListSources(BaseTool):
    """List explicitly registered VSD sources."""

    def run(self, arguments=None, **_: Any):
        del arguments
        with _CATALOG_LOCK:
            sources = list(_load_catalog()["sources"].values())
        sources.sort(key=lambda source: source["source_id"])
        return {"status": "success", "data": {"sources": sources}}


@register_tool("VSDQuerySource")
class VSDQuerySource(BaseTool):
    """Run a safe JSON GET against one explicitly registered source."""

    def run(self, arguments=None, **_: Any):
        arguments = arguments or {}
        source_id = _source_id(arguments)
        with _CATALOG_LOCK:
            source = _load_catalog()["sources"].get(source_id)
        if source is None:
            raise ValueError(f"Unknown VSD source_id {source_id!r}")

        params = dict(source.get("default_params") or {})
        params.update(_validated_params(arguments.get("params")))
        payload, request = _safe_get_json(source["endpoint"], params)
        return {
            "status": "success",
            "data": {
                "source": {
                    "source_id": source_id,
                    "name": source["name"],
                    "endpoint": source["endpoint"],
                },
                "request": request,
                "result": payload,
            },
        }


@register_tool("VSDRemoveSource")
class VSDRemoveSource(BaseTool):
    """Remove one explicitly registered VSD source."""

    def run(self, arguments=None, **_: Any):
        arguments = arguments or {}
        source_id = _source_id(arguments)
        with _CATALOG_LOCK:
            catalog = _load_catalog()
            removed = catalog["sources"].pop(source_id, None)
            if removed is not None:
                _write_catalog(catalog)
        return {
            "status": "success",
            "data": {"removed": removed is not None, "source_id": source_id},
        }
