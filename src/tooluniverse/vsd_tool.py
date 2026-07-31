"""Safe, explicit Verified Source Directory (VSD) tools.

This module implements two VSD boundaries:

1. agent-facing, read-only adapters for packaged public JSON sources with fixed
   endpoints and source-specific contracts, and
2. explicit administration primitives for probing, persisting, querying, and
   removing additional sources through the VSD administration CLI.

It deliberately does not auto-harvest arbitrary URLs, auto-run generated tools,
or expose container provisioning. Network access is HTTPS GET-only, host
allowlisted, DNS-pinned, redirect-free, size-limited, and checked against
private, loopback, link-local, reserved, and other non-global addresses.
"""

from __future__ import annotations

import hashlib
import ipaddress
import json
import math
import os
import re
import socket
import tempfile
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, BinaryIO, Iterator
from urllib.parse import urljoin, urlsplit

import requests
from requests.adapters import HTTPAdapter
from urllib3.exceptions import ReadTimeoutError
from urllib3.util import Timeout as Urllib3Timeout

from .base_tool import BaseTool
from .tool_registry import register_tool

_CATALOG_LOCK = threading.RLock()
_CATALOG_LOCK_TIMEOUT = 10.0
_CATALOG_VERSION = 1
_MAX_RESPONSE_BYTES = 1_000_000
_SOURCE_ID_RE = re.compile(r"^[a-z][a-z0-9_]{2,63}$")
_CREDENTIAL_KEY_RE = re.compile(
    r"(?:api[_-]?key|access[_-]?key|(?:^|[_-])key(?:$|[_-])|token|secret|"
    r"password|authorization|credential|signature|bearer|jwt|session)",
    re.IGNORECASE,
)
_SECRET_PATH_RE = re.compile(
    r"(?:sk_(?:live|test)_[a-z0-9_-]{8,}|gh[pousr]_[a-z0-9]{8,}|"
    r"AKIA[A-Z0-9]{12,}|eyJ[a-z0-9_-]{12,}\.[a-z0-9_-]{8,})",
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
        "tool_name": "VSDWHOHypertensionIndicator",
        "review_scope": "Transport and response adapter reviewed; not scientific endorsement.",
    },
    {
        "source_id": "openfda_labels",
        "name": "openFDA Drug Labels",
        "endpoint": "https://api.fda.gov/drug/label.json",
        "description": "FDA drug labeling records, warnings, and indications.",
        "default_params": {"limit": 5},
        "tool_name": "VSDOpenFDALabelBySetId",
        "review_scope": "Transport and response adapter reviewed; not scientific endorsement.",
    },
    {
        "source_id": "cdc_places",
        "name": "CDC PLACES",
        "endpoint": "https://chronicdata.cdc.gov/resource/cwsq-ngmh.json",
        "description": "CDC local chronic-disease and preventive-service estimates.",
        "default_params": {"$limit": 5},
        "tool_name": "VSDCDCPlacesCoronaryHeartDisease",
        "review_scope": "Transport and response adapter reviewed; not scientific endorsement.",
    },
    {
        "source_id": "ensembl_ping",
        "name": "Ensembl REST",
        "endpoint": "https://rest.ensembl.org/info/ping",
        "description": "Ensembl REST JSON heartbeat and service entry point.",
        "default_params": {},
        "tool_name": "VSDEnsemblServiceStatus",
        "review_scope": "Transport and response adapter reviewed; not scientific endorsement.",
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


def _acquire_process_lock(handle: BinaryIO) -> None:
    deadline = time.monotonic() + _CATALOG_LOCK_TIMEOUT
    while True:
        try:
            handle.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            return
        except OSError as exc:
            if time.monotonic() >= deadline:
                raise TimeoutError(
                    "Timed out waiting for the VSD catalog lock"
                ) from exc
            time.sleep(0.05)


def _release_process_lock(handle: BinaryIO) -> None:
    handle.seek(0)
    if os.name == "nt":
        import msvcrt

        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl

        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


@contextmanager
def _catalog_transaction() -> Iterator[None]:
    """Serialize a complete catalog operation across threads and processes."""
    with _CATALOG_LOCK:
        path = _catalog_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        lock_path = path.with_name(f".{path.name}.lock")
        with lock_path.open("a+b") as handle:
            if handle.seek(0, os.SEEK_END) == 0:
                handle.write(b"\0")
                handle.flush()
            _acquire_process_lock(handle)
            try:
                yield
            finally:
                _release_process_lock(handle)


def _load_catalog() -> dict[str, Any]:
    path = _catalog_path()
    if not path.exists():
        return _empty_catalog()

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("VSD catalog is unreadable") from exc

    if (
        not isinstance(data, dict)
        or data.get("version") != _CATALOG_VERSION
        or not isinstance(data.get("sources"), dict)
    ):
        raise ValueError("VSD catalog has an unsupported structure")
    for source_id, source in data["sources"].items():
        if (
            not isinstance(source_id, str)
            or not _SOURCE_ID_RE.fullmatch(source_id)
            or not isinstance(source, dict)
            or source.get("source_id") != source_id
            or not isinstance(source.get("name"), str)
            or not isinstance(source.get("endpoint"), str)
            or not isinstance(source.get("default_params"), dict)
        ):
            raise ValueError("VSD catalog has an unsupported source record")
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
            handle.flush()
            os.fsync(handle.fileno())
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


def _validated_source_target(url: str) -> tuple[str, str, tuple[str, ...]]:
    """Return a normalized URL, hostname, and its vetted public addresses."""
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
    if _SECRET_PATH_RE.search(parsed.path):
        raise VSDPolicyError("Credential-like values are not allowed in source paths")

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

    addresses = _resolve_public_addresses(host, 443)
    return parsed.geturl(), host, addresses


def validate_source_url(url: str) -> str:
    """Validate and normalize one VSD source URL before every request."""
    normalized_url, _, _ = _validated_source_target(url)
    return normalized_url


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


def _response_socket(response: requests.Response):
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
    return sock


def _peer_address(response: requests.Response) -> str:
    return str(_response_socket(response).getpeername()[0])


def _response_chunks(
    response: requests.Response, *, deadline: float
) -> Iterator[bytes]:
    """Yield undecoded bytes while enforcing one wall-clock deadline."""
    raw_read = getattr(response.raw, "read", None)
    if not callable(raw_read):
        for chunk in response.iter_content(chunk_size=65_536):
            if time.monotonic() >= deadline:
                raise VSDPolicyError("Source request exceeded its total timeout")
            if chunk:
                yield chunk
        return

    response.raw.decode_content = False
    sock = _response_socket(response)
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise VSDPolicyError("Source request exceeded its total timeout")
        settimeout = getattr(sock, "settimeout", None)
        if callable(settimeout):
            settimeout(max(0.001, remaining))
        try:
            try:
                chunk = raw_read(65_536, decode_content=False)
            except TypeError:
                chunk = raw_read(65_536)
        except (ReadTimeoutError, socket.timeout, TimeoutError) as exc:
            raise VSDPolicyError("Source request exceeded its total timeout") from exc
        if not chunk:
            return
        if time.monotonic() >= deadline:
            raise VSDPolicyError("Source request exceeded its total timeout")
        yield chunk


def _reject_json_constant(value: str) -> None:
    raise VSDPolicyError(f"Source response contains non-standard JSON value {value}")


class _PinnedHTTPSAdapter(HTTPAdapter):
    """Connect to one vetted IP while authenticating the original hostname."""

    def __init__(self, hostname: str, address: str) -> None:
        self.hostname = hostname
        self.address = address
        super().__init__()

    def add_headers(self, request: requests.PreparedRequest, **kwargs: Any) -> None:
        del kwargs
        request.headers["Host"] = self.hostname

    def build_connection_pool_key_attributes(
        self,
        request: requests.PreparedRequest,
        verify: bool | str | None,
        cert: Any = None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        host_params, pool_kwargs = super().build_connection_pool_key_attributes(
            request, verify, cert
        )
        requested_host = _normalize_host(str(host_params.get("host") or ""))
        if requested_host != self.hostname:
            raise VSDPolicyError("Pinned transport received an unexpected hostname")
        host_params["host"] = self.address
        host_params["port"] = 443
        pool_kwargs["assert_hostname"] = self.hostname
        pool_kwargs["server_hostname"] = self.hostname
        return host_params, pool_kwargs

    def get_connection(self, url: str, proxies: Any = None):
        """Support Requests versions that still use the legacy adapter hook."""
        del url, proxies
        return self.poolmanager.connection_from_host(
            scheme="https",
            host=self.address,
            port=443,
            pool_kwargs={
                "assert_hostname": self.hostname,
                "server_hostname": self.hostname,
            },
        )


def _safe_get_json(
    url: str,
    params: dict[str, Any] | None = None,
    *,
    timeout: float = 20.0,
    session: requests.Session | None = None,
) -> tuple[Any, dict[str, Any]]:
    """GET JSON through a DNS-pinned HTTPS connection with bounded decoding."""
    if (
        isinstance(timeout, bool)
        or not isinstance(timeout, (int, float))
        or not math.isfinite(timeout)
        or timeout <= 0
    ):
        raise ValueError("timeout must be a positive finite number")
    deadline = time.monotonic() + timeout
    normalized_url, hostname, addresses = _validated_source_target(url)
    pinned_address = addresses[0]
    validated_params = _validated_params(params)
    owned_session = session is None
    http = session or requests.Session()
    http.trust_env = False

    mount = getattr(http, "mount", None)
    if mount is not None:
        mount("https://", _PinnedHTTPSAdapter(hostname, pinned_address))

    try:
        try:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise VSDPolicyError("Source request exceeded its total timeout")
            response = http.get(
                normalized_url,
                params=validated_params or None,
                headers={
                    "Accept": "application/json",
                    "Accept-Encoding": "identity",
                },
                timeout=Urllib3Timeout(
                    total=remaining,
                    connect=min(5.0, remaining),
                    read=remaining,
                ),
                allow_redirects=False,
                stream=True,
            )
        except requests.Timeout as exc:
            raise VSDPolicyError("Source request exceeded its total timeout") from exc
        try:
            if time.monotonic() >= deadline:
                raise VSDPolicyError("Source request exceeded its total timeout")
            peer_ip = _peer_address(response)
            _require_global_ip(peer_ip, context="Connected peer")
            if ipaddress.ip_address(peer_ip) != ipaddress.ip_address(pinned_address):
                raise VSDPolicyError(
                    "Connected peer did not match the vetted DNS address"
                )

            if response.status_code in {301, 302, 303, 307, 308}:
                location = response.headers.get("Location")
                if location:
                    # Preserve the more specific policy error for an unsafe target.
                    validate_source_url(urljoin(normalized_url, location))
                raise VSDPolicyError("Source redirects are not allowed")

            response.raise_for_status()
            content_encoding = response.headers.get("Content-Encoding", "")
            encodings = {
                item.strip().lower()
                for item in content_encoding.split(",")
                if item.strip()
            }
            if encodings - {"identity"}:
                raise VSDPolicyError("Source returned a non-identity Content-Encoding")

            content_type = response.headers.get("Content-Type", "").lower()
            media_type = content_type.split(";", 1)[0].strip()
            if media_type != "application/json" and not media_type.endswith("+json"):
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
                    raise VSDPolicyError("Source returned an invalid Content-Length")
                if parsed_length > _MAX_RESPONSE_BYTES:
                    raise VSDPolicyError("Source response exceeds the 1 MB limit")

            chunks: list[bytes] = []
            total = 0
            for chunk in _response_chunks(response, deadline=deadline):
                total += len(chunk)
                if total > _MAX_RESPONSE_BYTES:
                    raise VSDPolicyError("Source response exceeds the 1 MB limit")
                chunks.append(chunk)
            try:
                payload = json.loads(
                    b"".join(chunks).decode("utf-8"),
                    parse_constant=_reject_json_constant,
                )
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise VSDPolicyError("Source response is not valid UTF-8 JSON") from exc
            return payload, {
                "url": normalized_url,
                "status_code": response.status_code,
                "content_type": content_type,
                "response_bytes": total,
                "peer_ip": peer_ip,
                "redirects": 0,
            }
        finally:
            response.close()
    finally:
        if owned_session:
            http.close()


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


class VSDRegisterSource(BaseTool):
    """Probe and persist an explicitly trusted, public, JSON GET source."""

    def run(self, arguments=None, **_: Any):
        arguments = arguments or {}
        source_id = _source_id(arguments)
        replace = arguments.get("replace", False)
        if type(replace) is not bool:
            raise ValueError("replace must be a boolean")
        endpoint = validate_source_url(str(arguments.get("endpoint") or ""))
        default_params = _validated_params(arguments.get("default_params"))
        name = _bounded_text(
            arguments.get("name"), field="name", maximum=200, fallback=source_id
        )
        description = _bounded_text(
            arguments.get("description"), field="description", maximum=2000
        )

        with _catalog_transaction():
            existing = _load_catalog()["sources"].get(source_id)
        if existing is not None and not replace:
            raise ValueError(
                f"VSD source_id {source_id!r} is already registered; "
                "set replace=true to replace it"
            )

        payload, probe = _safe_get_json(endpoint, default_params)
        record = {
            "source_id": source_id,
            "name": name,
            "description": description,
            "endpoint": endpoint,
            "host": _normalize_host(urlsplit(endpoint).hostname or ""),
            "default_params": default_params,
            "registered_at": datetime.now(timezone.utc).isoformat(),
            "last_probe": {
                **probe,
                "result_type": type(payload).__name__,
            },
        }
        with _catalog_transaction():
            catalog = _load_catalog()
            existing = catalog["sources"].get(source_id)
            if existing is not None and not replace:
                raise ValueError(
                    f"VSD source_id {source_id!r} was registered concurrently; "
                    "set replace=true to replace it"
                )
            catalog["sources"][source_id] = record
            _write_catalog(catalog)
        return {
            "status": "success",
            "data": {
                "registered": True,
                "replaced": existing is not None,
                "source": record,
            },
        }


class VSDListSources(BaseTool):
    """List explicitly registered VSD sources."""

    def run(self, arguments=None, **_: Any):
        del arguments
        with _catalog_transaction():
            sources = list(_load_catalog()["sources"].values())
        sources.sort(key=lambda source: source["source_id"])
        return {"status": "success", "data": {"sources": sources}}


class VSDQuerySource(BaseTool):
    """Run a safe JSON GET against one explicitly registered source."""

    def run(self, arguments=None, **_: Any):
        arguments = arguments or {}
        source_id = _source_id(arguments)
        with _catalog_transaction():
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


class VSDRemoveSource(BaseTool):
    """Remove one explicitly registered VSD source."""

    def run(self, arguments=None, **_: Any):
        arguments = arguments or {}
        source_id = _source_id(arguments)
        with _catalog_transaction():
            catalog = _load_catalog()
            removed = catalog["sources"].pop(source_id, None)
            if removed is not None:
                _write_catalog(catalog)
        return {
            "status": "success",
            "data": {"removed": removed is not None, "source_id": source_id},
        }


def _source_provenance(
    provider: str,
    request: dict[str, Any],
    query_params: dict[str, Any],
    payload: Any,
) -> dict[str, Any]:
    """Return the stable provenance contract shared by reviewed source tools."""
    canonical_payload = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return {
        "provider": provider,
        "endpoint": request["url"],
        "query_params": query_params,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "http_status": request["status_code"],
        "content_type": request["content_type"],
        "response_bytes": request["response_bytes"],
        "redirects": request["redirects"],
        "payload_sha256": hashlib.sha256(canonical_payload).hexdigest(),
    }


def _one_string(values: Any) -> str | None:
    if isinstance(values, list) and len(values) == 1 and isinstance(values[0], str):
        return values[0]
    return values if isinstance(values, str) else None


@register_tool("VSDWHOHypertensionIndicator")
class VSDWHOHypertensionIndicator(BaseTool):
    """Return one fixed WHO hypertension indicator definition."""

    ENDPOINT = "https://ghoapi.azureedge.net/api/Indicator"
    PARAMS = {
        "$filter": "IndicatorCode eq 'NCD_HYP_DIAGNOSIS_C'",
        "$select": "IndicatorCode,IndicatorName,Language",
        "$top": 1,
    }

    def run(self, arguments=None, **_: Any):
        if arguments:
            raise ValueError("VSDWHOHypertensionIndicator accepts no arguments")
        payload, request = _safe_get_json(self.ENDPOINT, self.PARAMS)
        rows = payload.get("value") if isinstance(payload, dict) else None
        if (
            not isinstance(rows, list)
            or len(rows) != 1
            or not isinstance(rows[0], dict)
        ):
            raise VSDPolicyError(
                "WHO response did not match the reviewed indicator schema"
            )
        row = rows[0]
        indicator = {
            "indicator_code": row.get("IndicatorCode"),
            "indicator_name": row.get("IndicatorName"),
            "language": row.get("Language"),
        }
        if not all(isinstance(value, str) and value for value in indicator.values()):
            raise VSDPolicyError("WHO indicator fields were missing or invalid")
        return {
            "status": "success",
            "data": {
                "indicator": indicator,
                "provenance": _source_provenance(
                    "WHO Global Health Observatory", request, self.PARAMS, payload
                ),
            },
        }


@register_tool("VSDCDCPlacesCoronaryHeartDisease")
class VSDCDCPlacesCoronaryHeartDisease(BaseTool):
    """Return typed CDC PLACES CHD estimates for one county."""

    ENDPOINT = "https://chronicdata.cdc.gov/resource/cwsq-ngmh.json"
    MEASURE = "Coronary heart disease among adults"
    SELECT = (
        "year,stateabbr,countyname,locationname,measure,data_value,"
        "low_confidence_limit,high_confidence_limit"
    )

    def run(self, arguments=None, **_: Any):
        arguments = arguments or {}
        state_abbr = str(arguments.get("state_abbr") or "").upper()
        if not re.fullmatch(r"[A-Z]{2}", state_abbr):
            raise ValueError("state_abbr must contain exactly two letters")
        county_name = _bounded_text(
            arguments.get("county_name"), field="county_name", maximum=100
        ).strip()
        if not re.fullmatch(r"[A-Za-z][A-Za-z .'-]{0,99}", county_name):
            raise ValueError("county_name contains unsupported characters")
        limit = arguments.get("limit", 500)
        if (
            isinstance(limit, bool)
            or not isinstance(limit, int)
            or not 1 <= limit <= 500
        ):
            raise ValueError("limit must be an integer between 1 and 500")

        escaped_county = county_name.replace("'", "''")
        params = {
            "$select": self.SELECT,
            "$where": (
                f"stateabbr='{state_abbr}' AND countyname='{escaped_county}' "
                f"AND measure='{self.MEASURE}'"
            ),
            "$order": "locationname ASC",
            "$limit": limit,
        }
        payload, request = _safe_get_json(self.ENDPOINT, params)
        if not isinstance(payload, list) or len(payload) > limit:
            raise VSDPolicyError(
                "CDC response did not match the reviewed collection schema"
            )

        fields = (
            "year",
            "stateabbr",
            "countyname",
            "locationname",
            "measure",
            "data_value",
            "low_confidence_limit",
            "high_confidence_limit",
        )
        tracts = []
        for row in payload:
            if not isinstance(row, dict):
                raise VSDPolicyError("CDC response contained a non-object record")
            normalized = {field: row.get(field) for field in fields}
            if not all(
                isinstance(value, str) and value for value in normalized.values()
            ):
                raise VSDPolicyError("CDC record fields were missing or invalid")
            if (
                normalized["stateabbr"] != state_abbr
                or normalized["countyname"] != county_name
                or normalized["measure"] != self.MEASURE
            ):
                raise VSDPolicyError(
                    "CDC response escaped the requested disease geography"
                )
            try:
                numeric = [
                    float(normalized[field])
                    for field in (
                        "data_value",
                        "low_confidence_limit",
                        "high_confidence_limit",
                    )
                ]
            except ValueError as exc:
                raise VSDPolicyError("CDC estimate fields were not numeric") from exc
            if not all(math.isfinite(value) for value in numeric):
                raise VSDPolicyError("CDC estimate fields were not finite")
            tracts.append(normalized)

        return {
            "status": "success",
            "data": {
                "measure": self.MEASURE,
                "state_abbr": state_abbr,
                "county_name": county_name,
                "tracts": tracts,
                "possibly_truncated": len(tracts) == limit,
                "provenance": _source_provenance(
                    "CDC PLACES", request, params, payload
                ),
            },
        }


@register_tool("VSDOpenFDALabelBySetId")
class VSDOpenFDALabelBySetId(BaseTool):
    """Return a normalized public openFDA label selected by set ID."""

    ENDPOINT = "https://api.fda.gov/drug/label.json"

    def run(self, arguments=None, **_: Any):
        arguments = arguments or {}
        set_id = str(arguments.get("set_id") or "").lower()
        if not re.fullmatch(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
            set_id,
        ):
            raise ValueError("set_id must be a UUID")
        params = {"search": f'set_id:"{set_id}"', "limit": 1}
        payload, request = _safe_get_json(self.ENDPOINT, params)
        rows = payload.get("results") if isinstance(payload, dict) else None
        if (
            not isinstance(rows, list)
            or len(rows) != 1
            or not isinstance(rows[0], dict)
        ):
            raise VSDPolicyError("openFDA response did not contain exactly one label")
        row = rows[0]
        openfda = row.get("openfda") if isinstance(row.get("openfda"), dict) else {}
        warnings = row.get("warnings") or []
        if not isinstance(warnings, list) or not all(
            isinstance(value, str) for value in warnings
        ):
            raise VSDPolicyError("openFDA warnings did not match the reviewed schema")
        label = {
            "set_id": row.get("set_id"),
            "effective_time": row.get("effective_time"),
            "brand_name": _one_string(openfda.get("brand_name")),
            "generic_name": _one_string(openfda.get("generic_name")),
            "route": _one_string(openfda.get("route")),
            "warnings": warnings,
        }
        if label["set_id"] != set_id or not all(
            isinstance(label[field], str) and label[field]
            for field in ("effective_time", "brand_name", "generic_name", "route")
        ):
            raise VSDPolicyError("openFDA label fields were missing or invalid")
        return {
            "status": "success",
            "data": {
                "label": label,
                "provenance": _source_provenance(
                    "openFDA Drug Labels", request, params, payload
                ),
            },
        }


@register_tool("VSDEnsemblServiceStatus")
class VSDEnsemblServiceStatus(BaseTool):
    """Return the typed status of the reviewed Ensembl REST endpoint."""

    ENDPOINT = "https://rest.ensembl.org/info/ping"

    def run(self, arguments=None, **_: Any):
        if arguments:
            raise ValueError("VSDEnsemblServiceStatus accepts no arguments")
        payload, request = _safe_get_json(self.ENDPOINT)
        if not isinstance(payload, dict) or payload.get("ping") not in (0, 1):
            raise VSDPolicyError(
                "Ensembl response did not match the reviewed ping schema"
            )
        return {
            "status": "success",
            "data": {
                "service": "Ensembl REST",
                "available": payload["ping"] == 1,
                "provenance": _source_provenance("Ensembl REST", request, {}, payload),
            },
        }
