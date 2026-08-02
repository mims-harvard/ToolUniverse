"""Administrator-controlled source discovery and review handoff for VSD.

This module discovers API contracts, not tools. Crawls are bounded to explicit
HTTPS seed hosts, reports are local and content-addressed, and transmission to
the ToolUniverse repository requires a separate reviewed bundle plus consent.
"""

from __future__ import annotations

import copy
import hashlib
import ipaddress
import json
import os
import re
import socket
import tempfile
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable
from urllib import robotparser
from urllib.parse import urljoin, urlsplit, urlunsplit

import requests
from bs4 import BeautifulSoup
from urllib3.util import Timeout as Urllib3Timeout

from .vsd_coverage import _registry_tools, _tool_hosts
from .vsd_demand import validate_proposal_export
from .vsd_tool import (
    VSDPolicyError,
    _PinnedHTTPSAdapter,
    _peer_address,
    _require_global_ip,
    _response_chunks,
)

_VERSION = 1
_MAX_SEEDS = 20
_MAX_PAGES = 100
_MAX_DEPTH = 4
_MAX_PAGE_BYTES = 1_000_000
_MAX_TOTAL_BYTES = 20_000_000
_MAX_LINKS_PER_PAGE = 500
_MAX_CANDIDATES = 500
_MAX_HANDOFF_CANDIDATES = 100
_MAX_REPORT_BYTES = 4_000_000
_MAX_ISSUE_BYTES = 60_000
_USER_AGENT = "ToolUniverse-VSD-Source-Review/1.0"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_ID_RE = re.compile(r"^[0-9a-f]{16}$")
_SOURCE_ID_RE = re.compile(r"^[a-z][a-z0-9_]{2,63}$")
_SAFE_TEXT_RE = re.compile(r"^[^\x00-\x1f\x7f]{3,500}$")
_SECRET_RE = re.compile(
    r"(?:api[_-]?key|access[_-]?token|password|secret|authorization)=|bearer%20",
    re.IGNORECASE,
)
_CONTRACT_SUFFIXES = {
    ".graphql": "graphql",
    ".graphqls": "graphql",
    ".gql": "graphql",
    ".postman_collection.json": "postman",
    ".wsdl": "wsdl",
    ".proto": "protobuf",
    ".mcp.json": "mcp",
}
_CONTENT_HINTS = {
    "application/graphql": "graphql",
    "application/vnd.oai.openapi+json": "openapi",
    "application/vnd.oai.openapi": "openapi",
    "application/wsdl+xml": "wsdl",
    "application/protobuf": "protobuf",
}
_SOURCE_FORMATS = {
    "openapi",
    "graphql",
    "asyncapi",
    "postman",
    "wsdl",
    "protobuf",
    "mcp",
}
_PATH_MARKERS = (
    ("openapi", "openapi"),
    ("swagger", "openapi"),
    ("asyncapi", "asyncapi"),
    ("postman", "postman"),
    ("graphql", "graphql"),
    ("wsdl", "wsdl"),
    ("mcp", "mcp"),
)
_CATALOG_PATH = Path(__file__).with_name("data") / "vsd_trusted_sources.json"
_Fetch = Callable[[str, float, int], tuple[bytes, dict[str, Any]]]


class VSDSourceIntelligenceError(ValueError):
    """Raised when source intelligence crosses a review or safety boundary."""


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise VSDSourceIntelligenceError("Artifact is not finite JSON") from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _timestamp(value: str | None = None) -> str:
    if value is None:
        return datetime.now(timezone.utc).isoformat()
    if not isinstance(value, str) or len(value) > 64:
        raise VSDSourceIntelligenceError("Timestamp must be bounded ISO-8601 text")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise VSDSourceIntelligenceError("Timestamp must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise VSDSourceIntelligenceError("Timestamp must include a timezone")
    return parsed.astimezone(timezone.utc).isoformat()


def _safe_text(value: Any, *, field: str, maximum: int = 500) -> str:
    text = str(value or "").strip()
    if not text or len(text) > maximum or not _SAFE_TEXT_RE.fullmatch(text):
        raise VSDSourceIntelligenceError(f"{field} must be printable bounded text")
    return text


def _normalize_host(host: str) -> str:
    try:
        return host.encode("idna").decode("ascii").casefold().rstrip(".")
    except UnicodeError as exc:
        raise VSDSourceIntelligenceError("Source host is not valid IDNA") from exc


def _canonical_url(value: Any, *, allowed_hosts: set[str] | None = None) -> str:
    if not isinstance(value, str) or not 1 <= len(value) <= 2048:
        raise VSDSourceIntelligenceError("Source URL must contain 1-2048 characters")
    if any(ord(character) < 32 for character in value):
        raise VSDSourceIntelligenceError("Source URL contains control characters")
    parsed = urlsplit(value)
    if (
        parsed.scheme.casefold() != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
        or parsed.query
    ):
        raise VSDSourceIntelligenceError(
            "Source URLs must use HTTPS without credentials, query, or fragment"
        )
    try:
        port = parsed.port
    except ValueError as exc:
        raise VSDSourceIntelligenceError("Source URL has an invalid port") from exc
    if port not in (None, 443):
        raise VSDSourceIntelligenceError("Source URLs may use only HTTPS port 443")
    host = _normalize_host(parsed.hostname)
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise VSDSourceIntelligenceError("IP-literal source URLs are prohibited")
    if allowed_hosts is not None and host not in allowed_hosts:
        raise VSDSourceIntelligenceError(
            "Discovered URL is outside explicit seed hosts"
        )
    path = re.sub(r"/{2,}", "/", parsed.path or "/")
    if _SECRET_RE.search(path):
        raise VSDSourceIntelligenceError("Credential-like source paths are prohibited")
    return urlunsplit(("https", host, path, "", ""))


def _public_addresses(host: str) -> tuple[str, ...]:
    try:
        records = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise VSDSourceIntelligenceError(
            f"Could not resolve source host {host!r}"
        ) from exc
    addresses = tuple(sorted({record[4][0] for record in records}))
    if not addresses:
        raise VSDSourceIntelligenceError("Source host resolved to no addresses")
    for address in addresses:
        try:
            _require_global_ip(address, context=f"Source host {host!r}")
        except ValueError as exc:
            raise VSDSourceIntelligenceError(str(exc)) from exc
    return addresses


def _fetch_https(
    url: str, timeout: float, max_bytes: int
) -> tuple[bytes, dict[str, Any]]:
    """Fetch one DNS-pinned HTTPS resource without redirects or compression."""
    normalized = _canonical_url(url)
    host = _normalize_host(urlsplit(normalized).hostname or "")
    addresses = _public_addresses(host)
    deadline = time.monotonic() + timeout
    session = requests.Session()
    session.trust_env = False
    session.mount("https://", _PinnedHTTPSAdapter(host, addresses[0]))
    try:
        response = session.get(
            normalized,
            headers={
                "Accept-Encoding": "identity",
                "User-Agent": _USER_AGENT,
                "Accept": "text/html,application/json,application/yaml,text/plain,*/*;q=0.1",
            },
            timeout=Urllib3Timeout(
                total=timeout, connect=min(5.0, timeout), read=timeout
            ),
            allow_redirects=False,
            stream=True,
        )
        try:
            peer_ip = _peer_address(response)
            _require_global_ip(peer_ip, context="Connected peer")
            if ipaddress.ip_address(peer_ip) != ipaddress.ip_address(addresses[0]):
                raise VSDSourceIntelligenceError(
                    "Connected peer did not match vetted DNS"
                )
            if response.status_code in {301, 302, 303, 307, 308}:
                raise VSDSourceIntelligenceError("Source redirects are not followed")
            response.raise_for_status()
            encoding = response.headers.get("Content-Encoding", "").casefold().strip()
            if encoding not in {"", "identity"}:
                raise VSDSourceIntelligenceError(
                    "Compressed source responses are prohibited"
                )
            declared = response.headers.get("Content-Length")
            if declared is not None and (
                not declared.isdigit() or int(declared) > max_bytes
            ):
                raise VSDSourceIntelligenceError("Source Content-Length is excessive")
            chunks: list[bytes] = []
            size = 0
            for chunk in _response_chunks(response, deadline=deadline):
                size += len(chunk)
                if size > max_bytes:
                    raise VSDSourceIntelligenceError(
                        "Source response exceeds byte limit"
                    )
                chunks.append(chunk)
            return b"".join(chunks), {
                "url": normalized,
                "status_code": response.status_code,
                "content_type": response.headers.get("Content-Type", "").casefold(),
                "response_bytes": size,
                "headers": {
                    str(key).casefold(): str(item)
                    for key, item in response.headers.items()
                },
                "peer_ip": peer_ip,
                "redirects": 0,
            }
        finally:
            response.close()
    except VSDPolicyError as exc:
        raise VSDSourceIntelligenceError(str(exc)) from exc
    except requests.Timeout as exc:
        raise VSDSourceIntelligenceError("Source request exceeded timeout") from exc
    except requests.RequestException as exc:
        raise VSDSourceIntelligenceError("Source request failed") from exc
    finally:
        session.close()


def _string_list(value: Any, *, field: str, maximum: int = 20) -> list[str]:
    if (
        not isinstance(value, list)
        or not 1 <= len(value) <= maximum
        or len(value) != len(set(value))
        or any(not isinstance(item, str) or not 1 <= len(item) <= 100 for item in value)
    ):
        raise VSDSourceIntelligenceError(f"{field} must contain unique bounded strings")
    return list(value)


def validate_trusted_source_catalog(value: Any) -> dict[str, Any]:
    """Validate the review catalog and its explicit non-execution boundary."""
    required = {
        "version",
        "catalog_state",
        "execution_allowed",
        "automatic_registration",
        "review_policy",
        "verified_on",
        "sources",
    }
    if not isinstance(value, dict) or set(value) != required:
        raise VSDSourceIntelligenceError("Trusted-source catalog structure is invalid")
    if (
        value["version"] != _VERSION
        or value["catalog_state"] != "eligible_for_human_candidate_review"
        or value["execution_allowed"] is not False
        or value["automatic_registration"] is not False
        or value["review_policy"]
        != "Catalog trust permits bounded discovery only; every operation still requires inspection, verification, approval, and publication."
    ):
        raise VSDSourceIntelligenceError("Trusted-source catalog weakens review policy")
    if _timestamp(value["verified_on"]) != value["verified_on"]:
        raise VSDSourceIntelligenceError("Catalog verification timestamp is invalid")
    sources = value.get("sources")
    if not isinstance(sources, list) or not 1 <= len(sources) <= 250:
        raise VSDSourceIntelligenceError(
            "Trusted-source catalog must contain 1-250 reviewed sources"
        )
    ids: set[str] = set()
    domains: set[str] = set()
    keys = {
        "source_id",
        "name",
        "organization",
        "domain",
        "documentation_url",
        "topics",
        "contract_formats",
        "access",
        "trust_basis",
        "review_state",
        "execution_allowed",
    }
    allowed_access = {"public", "registration", "controlled", "mixed"}
    allowed_formats = {
        "openapi",
        "rest",
        "graphql",
        "asyncapi",
        "postman",
        "wsdl",
        "protobuf",
        "mcp",
        "fhir",
        "sdmx",
        "ckan",
        "stac",
        "trs",
    }
    for source in sources:
        if not isinstance(source, dict) or set(source) != keys:
            raise VSDSourceIntelligenceError("Catalog contains an invalid source entry")
        source_id = source.get("source_id")
        domain = _normalize_host(str(source.get("domain") or ""))
        documentation_url = _canonical_url(source.get("documentation_url"))
        if (
            not isinstance(source_id, str)
            or not _SOURCE_ID_RE.fullmatch(source_id)
            or source_id in ids
            or domain in domains
            or urlsplit(documentation_url).hostname is None
        ):
            raise VSDSourceIntelligenceError(
                "Catalog source identity is invalid or duplicated"
            )
        if source["domain"] != domain:
            raise VSDSourceIntelligenceError("Catalog domains must be canonical")
        _safe_text(source["name"], field="source name", maximum=120)
        _safe_text(source["organization"], field="source organization", maximum=160)
        topics = _string_list(source["topics"], field="topics", maximum=12)
        formats = _string_list(
            source["contract_formats"], field="contract_formats", maximum=8
        )
        if not set(formats) <= allowed_formats or not topics:
            raise VSDSourceIntelligenceError(
                "Catalog formats or topics are unsupported"
            )
        if (
            source["access"] not in allowed_access
            or source["trust_basis"]
            not in {
                "official_government",
                "official_project",
                "official_standards_body",
            }
            or source["review_state"] != "trusted_for_candidate_discovery"
            or source["execution_allowed"] is not False
        ):
            raise VSDSourceIntelligenceError(
                "Catalog source crosses the execution boundary"
            )
        ids.add(source_id)
        domains.add(domain)
    return copy.deepcopy(value)


def load_trusted_source_catalog(path: str | Path | None = None) -> dict[str, Any]:
    source = Path(path) if path is not None else _CATALOG_PATH
    try:
        if source.stat().st_size > _MAX_REPORT_BYTES:
            raise VSDSourceIntelligenceError("Trusted-source catalog is too large")
        value = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise VSDSourceIntelligenceError(
            "Could not load trusted-source catalog"
        ) from exc
    return validate_trusted_source_catalog(value)


def configured_source_inventory(tooluniverse: Any) -> dict[str, Any]:
    """Inventory exact HTTPS hosts in built-in and runtime tool configurations."""
    tools = _registry_tools(tooluniverse)
    by_host: dict[str, set[str]] = {}
    for tool in tools:
        name = str(tool.get("name") or "")
        for host in _tool_hosts(tool):
            by_host.setdefault(host, set()).add(name)
    hosts = [
        {"host": host, "tools": sorted(names, key=str.casefold)}
        for host, names in sorted(by_host.items())
    ]
    body = {
        "format": "vsd_source_inventory_v1",
        "version": _VERSION,
        "tool_count": len(tools),
        "host_count": len(hosts),
        "hosts": hosts,
    }
    return {**body, "inventory_sha256": _digest(body)}


def validate_source_inventory(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {
        "format",
        "version",
        "tool_count",
        "host_count",
        "hosts",
        "inventory_sha256",
    }:
        raise VSDSourceIntelligenceError("Source inventory structure is invalid")
    body = {key: item for key, item in value.items() if key != "inventory_sha256"}
    if (
        value["format"] != "vsd_source_inventory_v1"
        or value["version"] != _VERSION
        or value["inventory_sha256"] != _digest(body)
        or value["host_count"] != len(value.get("hosts", []))
        or type(value["tool_count"]) is not int
        or value["tool_count"] < 0
    ):
        raise VSDSourceIntelligenceError("Source inventory identity is invalid")
    previous = ""
    for entry in value["hosts"]:
        if not isinstance(entry, dict) or set(entry) != {"host", "tools"}:
            raise VSDSourceIntelligenceError("Source inventory host is invalid")
        host = _normalize_host(str(entry["host"]))
        if host != entry["host"] or host <= previous:
            raise VSDSourceIntelligenceError("Source inventory hosts are not canonical")
        _string_list(entry["tools"], field="inventory tools", maximum=10_000)
        previous = host
    return copy.deepcopy(value)


def assess_catalog_coverage(catalog: Any, inventory: Any) -> dict[str, Any]:
    checked_catalog = validate_trusted_source_catalog(catalog)
    checked_inventory = validate_source_inventory(inventory)
    existing = {entry["host"]: entry["tools"] for entry in checked_inventory["hosts"]}
    rows = []
    for source in checked_catalog["sources"]:
        tools = existing.get(source["domain"], [])
        rows.append(
            {
                "source_id": source["source_id"],
                "domain": source["domain"],
                "coverage": "existing_host" if tools else "candidate_gap",
                "existing_tools": tools,
            }
        )
    body = {
        "format": "vsd_catalog_coverage_v1",
        "version": _VERSION,
        "catalog_source_count": len(rows),
        "existing_host_count": sum(row["coverage"] == "existing_host" for row in rows),
        "candidate_gap_count": sum(row["coverage"] == "candidate_gap" for row in rows),
        "inventory_sha256": checked_inventory["inventory_sha256"],
        "sources": rows,
    }
    return {**body, "coverage_sha256": _digest(body)}


def _format_hint(url: str, raw: bytes, content_type: str) -> tuple[str | None, str]:
    path = urlsplit(url).path.casefold()
    for suffix, hint in _CONTRACT_SUFFIXES.items():
        if path.endswith(suffix):
            return hint, "contract_suffix"
    for marker, hint in _PATH_MARKERS:
        if marker in path:
            return hint, "contract_path_marker"
    media_type = content_type.split(";", 1)[0].strip()
    if media_type in _CONTENT_HINTS:
        return _CONTENT_HINTS[media_type], "contract_content_type"
    prefix = raw[:200_000].lstrip()
    if prefix.startswith(b"<"):
        if re.search(rb"<(?:\w+:)?(?:definitions|description)\b", prefix):
            return "wsdl", "contract_content_marker"
    if re.search(rb"\bsyntax\s*=\s*['\"]proto[23]['\"]", prefix):
        return "protobuf", "contract_content_marker"
    try:
        document = json.loads(prefix.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None, ""
    if not isinstance(document, dict):
        return None, ""
    if "openapi" in document or "swagger" in document:
        return "openapi", "contract_content_marker"
    if "asyncapi" in document:
        return "asyncapi", "contract_content_marker"
    schema = str((document.get("info") or {}).get("schema") or "")
    if "schema.getpostman.com" in schema:
        return "postman", "contract_content_marker"
    if "__schema" in document or "__schema" in (document.get("data") or {}):
        return "graphql", "contract_content_marker"
    if any(key in document for key in ("mcpServers", "serverUrl", "tools")):
        return "mcp", "contract_content_marker"
    return None, ""


def _linked_urls(base_url: str, raw: bytes, content_type: str) -> list[tuple[str, str]]:
    media_type = content_type.split(";", 1)[0].strip()
    prefix = raw[:200].lstrip().lower()
    html_sniffed = prefix.startswith((b"<html", b"<!doctype html"))
    if media_type not in {"text/html", "application/xhtml+xml"} and not (
        media_type in {"", "text/plain"} and html_sniffed
    ):
        return []
    try:
        soup = BeautifulSoup(raw.decode("utf-8"), "html.parser")
    except UnicodeDecodeError:
        return []
    links: list[tuple[str, str]] = []
    for node in soup.find_all(["a", "link"], limit=_MAX_LINKS_PER_PAGE):
        href = node.get("href")
        if not isinstance(href, str) or not href.strip():
            continue
        rel = " ".join(str(item) for item in (node.get("rel") or []))
        evidence = "html_link"
        if any(
            term in rel.casefold()
            for term in ("service-desc", "describedby", "alternate")
        ):
            evidence = "metadata_link"
        links.append((urljoin(base_url, href.strip()), evidence))
    for script in soup.find_all(
        "script", attrs={"type": "application/ld+json"}, limit=20
    ):
        try:
            value = json.loads(script.get_text())
        except json.JSONDecodeError:
            continue
        pending = [value]
        while pending and len(links) < _MAX_LINKS_PER_PAGE:
            item = pending.pop()
            if isinstance(item, str) and item.startswith(("https://", "/")):
                links.append((urljoin(base_url, item), "jsonld_link"))
            elif isinstance(item, dict):
                pending.extend(item.values())
            elif isinstance(item, list):
                pending.extend(item[:100])
    return links[:_MAX_LINKS_PER_PAGE]


def _robots_policy(raw: bytes, robots_url: str) -> robotparser.RobotFileParser:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise VSDSourceIntelligenceError("robots.txt is not UTF-8") from exc
    parser = robotparser.RobotFileParser(robots_url)
    parser.parse(text.splitlines())
    return parser


def _candidate(
    *,
    url: str,
    format_hint: str,
    evidence: str,
    discovered_from: str,
    trusted_source: dict[str, Any] | None,
    existing_tools: list[str],
) -> dict[str, Any]:
    score = 20 + 10 + (25 if evidence == "contract_content_marker" else 15)
    if trusted_source is not None:
        score += 25
    if existing_tools:
        score -= 20
    body = {
        "url": url,
        "host": _normalize_host(urlsplit(url).hostname or ""),
        "format_hint": format_hint,
        "evidence": evidence,
        "discovered_from": discovered_from,
        "trusted_source_id": trusted_source["source_id"] if trusted_source else None,
        "quality_score": max(0, min(100, score)),
        "coverage": "existing_host" if existing_tools else "candidate_gap",
        "existing_tools": existing_tools,
        "approval_state": "unreviewed_source_candidate",
        "execution_allowed": False,
    }
    digest = _digest(body)
    return {**body, "candidate_id": digest[:16], "candidate_sha256": digest}


def crawl_source_candidates(
    seeds: Iterable[str],
    *,
    catalog: Any | None = None,
    inventory: Any | None = None,
    max_pages: int = 20,
    max_depth: int = 2,
    max_page_bytes: int = 500_000,
    max_total_bytes: int = 5_000_000,
    timeout_seconds: float = 15,
    respect_robots: bool = True,
    fetcher: _Fetch = _fetch_https,
    scanned_at: str | None = None,
) -> dict[str, Any]:
    """Crawl explicit seed hosts and return inert, deduplicated contract leads."""
    seed_list = list(seeds)
    if not 1 <= len(seed_list) <= _MAX_SEEDS or len(seed_list) != len(set(seed_list)):
        raise VSDSourceIntelligenceError("Provide 1-20 unique source seeds")
    if type(max_pages) is not int or not 1 <= max_pages <= _MAX_PAGES:
        raise VSDSourceIntelligenceError("max_pages must be between 1 and 100")
    if type(max_depth) is not int or not 0 <= max_depth <= _MAX_DEPTH:
        raise VSDSourceIntelligenceError("max_depth must be between 0 and 4")
    if type(max_page_bytes) is not int or not 1 <= max_page_bytes <= _MAX_PAGE_BYTES:
        raise VSDSourceIntelligenceError("max_page_bytes is out of range")
    if (
        type(max_total_bytes) is not int
        or not max_page_bytes <= max_total_bytes <= _MAX_TOTAL_BYTES
    ):
        raise VSDSourceIntelligenceError("max_total_bytes is out of range")
    if not isinstance(timeout_seconds, (int, float)) or not 1 <= timeout_seconds <= 60:
        raise VSDSourceIntelligenceError("timeout_seconds must be between 1 and 60")
    if type(respect_robots) is not bool or not respect_robots:
        raise VSDSourceIntelligenceError("robots.txt enforcement cannot be disabled")

    normalized_seeds = [_canonical_url(seed) for seed in seed_list]
    allowed_hosts = {
        _normalize_host(urlsplit(seed).hostname or "") for seed in normalized_seeds
    }
    checked_catalog = (
        validate_trusted_source_catalog(catalog) if catalog is not None else None
    )
    catalog_by_domain = {
        source["domain"]: source
        for source in (checked_catalog or {}).get("sources", [])
    }
    checked_inventory = (
        validate_source_inventory(inventory) if inventory is not None else None
    )
    tools_by_host = {
        entry["host"]: entry["tools"]
        for entry in (checked_inventory or {}).get("hosts", [])
    }
    robots: dict[str, robotparser.RobotFileParser] = {}
    robots_status: dict[str, str] = {}
    for host in sorted(allowed_hosts):
        robots_url = f"https://{host}/robots.txt"
        try:
            raw, metadata = fetcher(
                robots_url, timeout_seconds, min(max_page_bytes, 100_000)
            )
            if metadata.get("redirects") != 0 or metadata.get("url") != robots_url:
                raise VSDSourceIntelligenceError("robots.txt fetch changed URL")
            robots[host] = _robots_policy(raw, robots_url)
            robots_status[host] = "loaded"
        except VSDSourceIntelligenceError:
            parser = robotparser.RobotFileParser(robots_url)
            parser.parse([])
            robots[host] = parser
            robots_status[host] = "unavailable_default_allow"

    queue: deque[tuple[str, int, str]] = deque(
        (seed, 0, seed) for seed in normalized_seeds
    )
    queued = set(normalized_seeds)
    visited: set[str] = set()
    blocked: list[str] = []
    errors: list[dict[str, str]] = []
    candidate_by_url: dict[str, dict[str, Any]] = {}
    page_records: list[dict[str, Any]] = []
    total_bytes = 0
    while queue and len(visited) < max_pages:
        url, depth, discovered_from = queue.popleft()
        if url in visited:
            continue
        host = _normalize_host(urlsplit(url).hostname or "")
        if not robots[host].can_fetch(_USER_AGENT, url):
            blocked.append(url)
            visited.add(url)
            continue
        if total_bytes >= max_total_bytes:
            break
        remaining = min(max_page_bytes, max_total_bytes - total_bytes)
        try:
            raw, metadata = fetcher(url, timeout_seconds, remaining)
            if metadata.get("url") != url or metadata.get("redirects") != 0:
                raise VSDSourceIntelligenceError("Fetcher returned an unexpected URL")
            content_type = str(metadata.get("content_type") or "").casefold()
            size = len(raw)
            if size > remaining or metadata.get("response_bytes") != size:
                raise VSDSourceIntelligenceError(
                    "Fetcher returned inconsistent byte metadata"
                )
        except VSDSourceIntelligenceError as exc:
            errors.append({"url": url, "error": str(exc)[:300]})
            visited.add(url)
            continue
        visited.add(url)
        total_bytes += size
        hint, evidence = _format_hint(url, raw, content_type)
        if hint:
            candidate_by_url[url] = _candidate(
                url=url,
                format_hint=hint,
                evidence=evidence,
                discovered_from=discovered_from,
                trusted_source=catalog_by_domain.get(host),
                existing_tools=tools_by_host.get(host, []),
            )
        page_records.append(
            {
                "url": url,
                "depth": depth,
                "response_bytes": size,
                "content_type": content_type[:200],
                "content_sha256": hashlib.sha256(raw).hexdigest(),
                "contract_detected": hint is not None,
            }
        )
        if depth >= max_depth or len(candidate_by_url) >= _MAX_CANDIDATES:
            continue
        for linked, link_evidence in _linked_urls(url, raw, content_type):
            try:
                normalized = _canonical_url(linked, allowed_hosts=allowed_hosts)
            except VSDSourceIntelligenceError:
                continue
            linked_host = _normalize_host(urlsplit(normalized).hostname or "")
            if not robots[linked_host].can_fetch(_USER_AGENT, normalized):
                if normalized not in blocked:
                    blocked.append(normalized)
                continue
            linked_hint, _ = _format_hint(normalized, b"", "")
            if linked_hint and normalized not in candidate_by_url:
                candidate_by_url[normalized] = _candidate(
                    url=normalized,
                    format_hint=linked_hint,
                    evidence=link_evidence,
                    discovered_from=url,
                    trusted_source=catalog_by_domain.get(host),
                    existing_tools=tools_by_host.get(host, []),
                )
            if (
                normalized not in queued
                and len(queued) < max_pages * _MAX_LINKS_PER_PAGE
            ):
                queued.add(normalized)
                queue.append((normalized, depth + 1, url))

    candidates = sorted(
        candidate_by_url.values(),
        key=lambda item: (-item["quality_score"], item["url"]),
    )[:_MAX_CANDIDATES]
    body = {
        "format": "vsd_source_scan_v1",
        "version": _VERSION,
        "scanned_at": _timestamp(scanned_at),
        "seeds": sorted(normalized_seeds),
        "allowed_hosts": sorted(allowed_hosts),
        "limits": {
            "max_pages": max_pages,
            "max_depth": max_depth,
            "max_page_bytes": max_page_bytes,
            "max_total_bytes": max_total_bytes,
            "timeout_seconds": timeout_seconds,
        },
        "robots_enforced": True,
        "robots_status": robots_status,
        "pages_visited": len(visited),
        "pages_fetched": len(page_records),
        "response_bytes": total_bytes,
        "blocked_count": len(blocked),
        "blocked_urls": sorted(blocked),
        "error_count": len(errors),
        "errors": errors,
        "candidate_count": len(candidates),
        "candidate_gap_count": sum(
            item["coverage"] == "candidate_gap" for item in candidates
        ),
        "existing_host_count": sum(
            item["coverage"] == "existing_host" for item in candidates
        ),
        "pages": page_records,
        "candidates": candidates,
        "approval_state": "unreviewed_source_scan",
        "execution_allowed": False,
        "transmission": "none; scan is local until an administrator prepares and explicitly submits a reviewed handoff",
    }
    digest = _digest(body)
    return {**body, "scan_id": digest[:16], "scan_sha256": digest}


def validate_source_scan(value: Any) -> dict[str, Any]:
    scan_keys = {
        "format",
        "version",
        "scanned_at",
        "seeds",
        "allowed_hosts",
        "limits",
        "robots_enforced",
        "robots_status",
        "pages_visited",
        "pages_fetched",
        "response_bytes",
        "blocked_count",
        "blocked_urls",
        "error_count",
        "errors",
        "candidate_count",
        "candidate_gap_count",
        "existing_host_count",
        "pages",
        "candidates",
        "approval_state",
        "execution_allowed",
        "transmission",
        "scan_id",
        "scan_sha256",
    }
    if not isinstance(value, dict) or set(value) != scan_keys:
        raise VSDSourceIntelligenceError("Source scan must be an object")
    body = {
        key: item
        for key, item in value.items()
        if key not in {"scan_id", "scan_sha256"}
    }
    digest = _digest(body)
    seeds = value.get("seeds")
    allowed_hosts = value.get("allowed_hosts")
    limits = value.get("limits")
    robots_status = value.get("robots_status")
    pages = value.get("pages")
    candidates = value.get("candidates")
    blocked_urls = value.get("blocked_urls")
    errors = value.get("errors")
    if (
        value.get("format") != "vsd_source_scan_v1"
        or value.get("version") != _VERSION
        or value.get("approval_state") != "unreviewed_source_scan"
        or value.get("execution_allowed") is not False
        or value.get("robots_enforced") is not True
        or value.get("scan_sha256") != digest
        or value.get("scan_id") != digest[:16]
        or value.get("transmission")
        != "none; scan is local until an administrator prepares and explicitly submits a reviewed handoff"
        or not isinstance(seeds, list)
        or not 1 <= len(seeds) <= _MAX_SEEDS
        or seeds != sorted(set(seeds))
        or not isinstance(allowed_hosts, list)
        or allowed_hosts != sorted(set(allowed_hosts))
        or not allowed_hosts
        or not isinstance(limits, dict)
        or set(limits)
        != {
            "max_pages",
            "max_depth",
            "max_page_bytes",
            "max_total_bytes",
            "timeout_seconds",
        }
        or not isinstance(robots_status, dict)
        or set(robots_status) != set(allowed_hosts)
        or any(
            status not in {"loaded", "unavailable_default_allow"}
            for status in robots_status.values()
        )
        or not isinstance(pages, list)
        or not isinstance(candidates, list)
        or not isinstance(blocked_urls, list)
        or not isinstance(errors, list)
        or value.get("candidate_count") != len(candidates)
        or value.get("pages_fetched") != len(pages)
        or value.get("blocked_count") != len(blocked_urls)
        or value.get("error_count") != len(errors)
        or value.get("candidate_gap_count")
        != sum(item.get("coverage") == "candidate_gap" for item in candidates)
        or value.get("existing_host_count")
        != sum(item.get("coverage") == "existing_host" for item in candidates)
        or type(value.get("pages_visited")) is not int
        or value["pages_visited"] < len(pages)
        or type(value.get("response_bytes")) is not int
        or value["response_bytes"] < 0
    ):
        raise VSDSourceIntelligenceError(
            "Source scan identity or safety state is invalid"
        )
    _timestamp(value["scanned_at"])
    host_set = set(allowed_hosts)
    for host in allowed_hosts:
        if _normalize_host(host) != host:
            raise VSDSourceIntelligenceError("Source scan hosts are not canonical")
    for seed in seeds:
        _canonical_url(seed, allowed_hosts=host_set)
    if (
        type(limits["max_pages"]) is not int
        or not 1 <= limits["max_pages"] <= _MAX_PAGES
        or type(limits["max_depth"]) is not int
        or not 0 <= limits["max_depth"] <= _MAX_DEPTH
        or type(limits["max_page_bytes"]) is not int
        or not 1 <= limits["max_page_bytes"] <= _MAX_PAGE_BYTES
        or type(limits["max_total_bytes"]) is not int
        or not limits["max_page_bytes"] <= limits["max_total_bytes"] <= _MAX_TOTAL_BYTES
        or not isinstance(limits["timeout_seconds"], (int, float))
        or not 1 <= limits["timeout_seconds"] <= 60
    ):
        raise VSDSourceIntelligenceError("Source scan limits are invalid")
    for url in blocked_urls:
        _canonical_url(url, allowed_hosts=host_set)
    for error in errors:
        if not isinstance(error, dict) or set(error) != {"url", "error"}:
            raise VSDSourceIntelligenceError("Source scan error is invalid")
        _canonical_url(error["url"], allowed_hosts=host_set)
        _safe_text(error["error"], field="scan error", maximum=300)
    page_keys = {
        "url",
        "depth",
        "response_bytes",
        "content_type",
        "content_sha256",
        "contract_detected",
    }
    page_bytes = 0
    for page in pages:
        if not isinstance(page, dict) or set(page) != page_keys:
            raise VSDSourceIntelligenceError("Source scan page is invalid")
        _canonical_url(page["url"], allowed_hosts=host_set)
        if (
            type(page["depth"]) is not int
            or not 0 <= page["depth"] <= limits["max_depth"]
            or type(page["response_bytes"]) is not int
            or not 0 <= page["response_bytes"] <= limits["max_page_bytes"]
            or not isinstance(page["content_type"], str)
            or len(page["content_type"]) > 200
            or not _SHA256_RE.fullmatch(str(page["content_sha256"]))
            or type(page["contract_detected"]) is not bool
        ):
            raise VSDSourceIntelligenceError("Source scan page metadata is invalid")
        page_bytes += page["response_bytes"]
    if page_bytes != value["response_bytes"]:
        raise VSDSourceIntelligenceError("Source scan byte accounting is invalid")
    seen: set[str] = set()
    candidate_keys = {
        "url",
        "host",
        "format_hint",
        "evidence",
        "discovered_from",
        "trusted_source_id",
        "quality_score",
        "coverage",
        "existing_tools",
        "approval_state",
        "execution_allowed",
        "candidate_id",
        "candidate_sha256",
    }
    for candidate in candidates:
        if not isinstance(candidate, dict) or set(candidate) != candidate_keys:
            raise VSDSourceIntelligenceError("Source scan candidate is invalid")
        candidate_body = {
            key: item
            for key, item in candidate.items()
            if key not in {"candidate_id", "candidate_sha256"}
        }
        candidate_digest = _digest(candidate_body)
        if (
            candidate.get("candidate_sha256") != candidate_digest
            or candidate.get("candidate_id") != candidate_digest[:16]
            or candidate.get("candidate_id") in seen
            or candidate.get("approval_state") != "unreviewed_source_candidate"
            or candidate.get("execution_allowed") is not False
            or candidate.get("format_hint") not in _SOURCE_FORMATS
            or candidate.get("evidence")
            not in {
                "contract_suffix",
                "contract_path_marker",
                "contract_content_type",
                "contract_content_marker",
                "html_link",
                "metadata_link",
                "jsonld_link",
            }
            or candidate.get("coverage") not in {"existing_host", "candidate_gap"}
            or type(candidate.get("quality_score")) is not int
            or not 0 <= candidate["quality_score"] <= 100
        ):
            raise VSDSourceIntelligenceError("Source candidate identity is invalid")
        candidate_url = _canonical_url(candidate.get("url"), allowed_hosts=host_set)
        _canonical_url(candidate.get("discovered_from"), allowed_hosts=host_set)
        if candidate.get("host") != _normalize_host(
            urlsplit(candidate_url).hostname or ""
        ):
            raise VSDSourceIntelligenceError("Source candidate host is invalid")
        trusted_source_id = candidate.get("trusted_source_id")
        if trusted_source_id is not None and (
            not isinstance(trusted_source_id, str)
            or not _SOURCE_ID_RE.fullmatch(trusted_source_id)
        ):
            raise VSDSourceIntelligenceError(
                "Source candidate trust identity is invalid"
            )
        tools = candidate.get("existing_tools")
        if not isinstance(tools, list) or tools != sorted(set(tools), key=str.casefold):
            raise VSDSourceIntelligenceError(
                "Source candidate tool coverage is invalid"
            )
        if (candidate["coverage"] == "existing_host") != bool(tools):
            raise VSDSourceIntelligenceError(
                "Source candidate coverage is inconsistent"
            )
        seen.add(candidate["candidate_id"])
    return copy.deepcopy(value)


def _atomic_write(path: Path, raw: bytes, *, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.stem}_", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def write_scan_report(
    scan: Any, directory: str | Path, *, replace: bool = False
) -> Path:
    checked = validate_source_scan(scan)
    root = Path(directory).expanduser()
    root.mkdir(parents=True, exist_ok=True)
    os.chmod(root, 0o700)
    destination = root / f"source-scan-{checked['scan_id']}.json"
    if destination.exists() and not replace:
        raise VSDSourceIntelligenceError("Source scan report already exists")
    raw = (
        json.dumps(checked, indent=2, sort_keys=True, ensure_ascii=True).encode("utf-8")
        + b"\n"
    )
    if len(raw) > _MAX_REPORT_BYTES:
        raise VSDSourceIntelligenceError("Source scan report exceeds 4 MB")
    _atomic_write(destination, raw)
    return destination


def snapshot_source_candidate(
    scan: Any,
    candidate_id: str,
    directory: str | Path,
    *,
    fetcher: _Fetch = _fetch_https,
    timeout_seconds: float = 15,
    max_bytes: int = 1_000_000,
) -> dict[str, Any]:
    """Fetch one selected contract into a local content-addressed snapshot."""
    checked = validate_source_scan(scan)
    matches = [
        item for item in checked["candidates"] if item["candidate_id"] == candidate_id
    ]
    if len(matches) != 1:
        raise VSDSourceIntelligenceError("Select exactly one source candidate")
    candidate = matches[0]
    raw, metadata = fetcher(candidate["url"], timeout_seconds, max_bytes)
    if metadata.get("url") != candidate["url"] or metadata.get("redirects") != 0:
        raise VSDSourceIntelligenceError("Snapshot fetch changed the reviewed URL")
    if len(raw) > max_bytes or metadata.get("response_bytes") != len(raw):
        raise VSDSourceIntelligenceError("Snapshot response exceeds its byte boundary")
    digest = hashlib.sha256(raw).hexdigest()
    suffix = {
        "openapi": ".openapi.json",
        "graphql": ".graphql",
        "asyncapi": ".asyncapi.yaml",
        "postman": ".postman_collection.json",
        "wsdl": ".wsdl",
        "protobuf": ".proto",
        "mcp": ".mcp.json",
    }[candidate["format_hint"]]
    root = Path(directory).expanduser()
    root.mkdir(parents=True, exist_ok=True)
    os.chmod(root, 0o700)
    destination = root / f"{digest}{suffix}"
    if destination.exists():
        if hashlib.sha256(destination.read_bytes()).hexdigest() != digest:
            raise VSDSourceIntelligenceError(
                "Existing snapshot failed digest verification"
            )
    else:
        _atomic_write(destination, raw)
    body = {
        "format": "vsd_source_snapshot_v1",
        "version": _VERSION,
        "scan_id": checked["scan_id"],
        "candidate_id": candidate_id,
        "source_url": candidate["url"],
        "format_hint": candidate["format_hint"],
        "content_sha256": digest,
        "response_bytes": len(raw),
        "snapshot_file": destination.name,
        "approval_state": "local_unreviewed_snapshot",
        "execution_allowed": False,
    }
    return {**body, "snapshot_sha256": _digest(body)}


def _validate_snapshot(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {
        "format",
        "version",
        "scan_id",
        "candidate_id",
        "source_url",
        "format_hint",
        "content_sha256",
        "response_bytes",
        "snapshot_file",
        "approval_state",
        "execution_allowed",
        "snapshot_sha256",
    }:
        raise VSDSourceIntelligenceError("Snapshot manifest is invalid")
    body = {key: item for key, item in value.items() if key != "snapshot_sha256"}
    if (
        value["format"] != "vsd_source_snapshot_v1"
        or value["version"] != _VERSION
        or value["approval_state"] != "local_unreviewed_snapshot"
        or value["execution_allowed"] is not False
        or not _SHA256_RE.fullmatch(str(value["content_sha256"]))
        or value["snapshot_sha256"] != _digest(body)
    ):
        raise VSDSourceIntelligenceError("Snapshot identity or safety state is invalid")
    return copy.deepcopy(value)


def write_snapshot_manifest(
    manifest: Any, destination: str | Path, *, replace: bool = False
) -> Path:
    """Persist the metadata needed to attach a selected snapshot to a handoff."""
    checked = _validate_snapshot(manifest)
    path = Path(destination).expanduser()
    if path.suffix.casefold() != ".json":
        raise VSDSourceIntelligenceError("Snapshot manifest must use a .json filename")
    if path.exists() and not replace:
        raise VSDSourceIntelligenceError("Snapshot manifest already exists")
    raw = (
        json.dumps(checked, indent=2, sort_keys=True, ensure_ascii=True).encode("utf-8")
        + b"\n"
    )
    _atomic_write(path, raw)
    return path


def prepare_core_handoff(
    scans: Iterable[Any],
    candidate_ids: Iterable[str],
    *,
    reviewed_by: str,
    decision_note: str,
    consent: bool,
    demand_export: Any | None = None,
    snapshots: Iterable[Any] = (),
    created_at: str | None = None,
) -> dict[str, Any]:
    """Build a sanitized local bundle for an explicit core-team handoff."""
    if consent is not True:
        raise VSDSourceIntelligenceError("Explicit handoff consent is required")
    reviewer = _safe_text(reviewed_by, field="reviewed_by", maximum=100)
    note = _safe_text(decision_note, field="decision_note", maximum=500)
    if len(note) < 20:
        raise VSDSourceIntelligenceError(
            "decision_note must contain at least 20 characters"
        )
    checked_scans = [validate_source_scan(scan) for scan in scans]
    if not 1 <= len(checked_scans) <= 20:
        raise VSDSourceIntelligenceError("Handoff requires 1-20 source scans")
    selected_ids = list(candidate_ids)
    if (
        not 1 <= len(selected_ids) <= _MAX_HANDOFF_CANDIDATES
        or len(selected_ids) != len(set(selected_ids))
        or any(
            not isinstance(item, str) or not _ID_RE.fullmatch(item)
            for item in selected_ids
        )
    ):
        raise VSDSourceIntelligenceError("Handoff candidate IDs are invalid")
    candidates_by_id = {
        candidate["candidate_id"]: candidate
        for scan in checked_scans
        for candidate in scan["candidates"]
    }
    if set(selected_ids) - set(candidates_by_id):
        raise VSDSourceIntelligenceError("Handoff selected an unknown candidate")
    checked_snapshots = [_validate_snapshot(item) for item in snapshots]
    snapshots_by_candidate = {item["candidate_id"]: item for item in checked_snapshots}
    if len(snapshots_by_candidate) != len(checked_snapshots):
        raise VSDSourceIntelligenceError(
            "Handoff snapshots contain duplicate candidates"
        )
    if set(snapshots_by_candidate) - set(selected_ids):
        raise VSDSourceIntelligenceError("Handoff contains an unselected snapshot")
    selected = []
    for candidate_id in selected_ids:
        item = candidates_by_id[candidate_id]
        snapshot = snapshots_by_candidate.get(candidate_id)
        selected.append(
            {
                "candidate_id": candidate_id,
                "url": item["url"],
                "format_hint": item["format_hint"],
                "evidence": item["evidence"],
                "trusted_source_id": item["trusted_source_id"],
                "quality_score": item["quality_score"],
                "coverage": item["coverage"],
                "existing_tools": item["existing_tools"],
                "snapshot_content_sha256": snapshot["content_sha256"]
                if snapshot
                else None,
                "execution_allowed": False,
            }
        )
    proposals: list[dict[str, Any]] = []
    demand_sha256 = None
    if demand_export is not None:
        validate_proposal_export(demand_export)
        proposals = copy.deepcopy(demand_export["proposals"][:20])
        demand_sha256 = demand_export["export_sha256"]
    body = {
        "format": "vsd_core_handoff_v1",
        "version": _VERSION,
        "created_at": _timestamp(created_at),
        "review": {"reviewed_by": reviewer, "decision_note": note, "consent": True},
        "scan_ids": sorted({scan["scan_id"] for scan in checked_scans}),
        "candidates": selected,
        "demand_export_sha256": demand_sha256,
        "demand_proposals": proposals,
        "execution_allowed": False,
        "transmission": "none; this sanitized bundle is local until submit_core_handoff is called with confirm=True",
    }
    digest = _digest(body)
    return {**body, "handoff_id": digest[:16], "handoff_sha256": digest}


def validate_core_handoff(value: Any) -> dict[str, Any]:
    handoff_keys = {
        "format",
        "version",
        "created_at",
        "review",
        "scan_ids",
        "candidates",
        "demand_export_sha256",
        "demand_proposals",
        "execution_allowed",
        "transmission",
        "handoff_id",
        "handoff_sha256",
    }
    if not isinstance(value, dict) or set(value) != handoff_keys:
        raise VSDSourceIntelligenceError("Core handoff must be an object")
    body = {
        key: item
        for key, item in value.items()
        if key not in {"handoff_id", "handoff_sha256"}
    }
    digest = _digest(body)
    if (
        value.get("format") != "vsd_core_handoff_v1"
        or value.get("version") != _VERSION
        or value.get("execution_allowed") is not False
        or value.get("review", {}).get("consent") is not True
        or value.get("handoff_sha256") != digest
        or value.get("handoff_id") != digest[:16]
        or not 1 <= len(value.get("candidates", [])) <= _MAX_HANDOFF_CANDIDATES
        or value.get("transmission")
        != "none; this sanitized bundle is local until submit_core_handoff is called with confirm=True"
    ):
        raise VSDSourceIntelligenceError("Core handoff identity or consent is invalid")
    _timestamp(value["created_at"])
    review = value["review"]
    if not isinstance(review, dict) or set(review) != {
        "reviewed_by",
        "decision_note",
        "consent",
    }:
        raise VSDSourceIntelligenceError("Core handoff review is invalid")
    _safe_text(review["reviewed_by"], field="reviewed_by", maximum=100)
    note = _safe_text(review["decision_note"], field="decision_note", maximum=500)
    if len(note) < 20 or _SECRET_RE.search(note):
        raise VSDSourceIntelligenceError("Core handoff decision note is invalid")
    scan_ids = value["scan_ids"]
    if (
        not isinstance(scan_ids, list)
        or not 1 <= len(scan_ids) <= 20
        or scan_ids != sorted(set(scan_ids))
        or any(
            not isinstance(item, str) or not _ID_RE.fullmatch(item) for item in scan_ids
        )
    ):
        raise VSDSourceIntelligenceError("Core handoff scan provenance is invalid")
    if value.get("demand_proposals"):
        # Reconstructing the entire demand export is impossible by design; proposals
        # were already validated before their review metadata was omitted.
        if not isinstance(
            value["demand_export_sha256"], str
        ) or not _SHA256_RE.fullmatch(value["demand_export_sha256"]):
            raise VSDSourceIntelligenceError(
                "Core handoff demand provenance is invalid"
            )
    elif value.get("demand_export_sha256") is not None:
        raise VSDSourceIntelligenceError(
            "Core handoff demand provenance is inconsistent"
        )
    candidate_keys = {
        "candidate_id",
        "url",
        "format_hint",
        "evidence",
        "trusted_source_id",
        "quality_score",
        "coverage",
        "existing_tools",
        "snapshot_content_sha256",
        "execution_allowed",
    }
    candidate_ids: set[str] = set()
    for item in value["candidates"]:
        if not isinstance(item, dict) or set(item) != candidate_keys:
            raise VSDSourceIntelligenceError("Core handoff candidate is invalid")
        if (
            item.get("execution_allowed") is not False
            or not isinstance(item.get("candidate_id"), str)
            or not _ID_RE.fullmatch(item["candidate_id"])
            or item["candidate_id"] in candidate_ids
            or item.get("format_hint") not in _SOURCE_FORMATS
            or item.get("evidence")
            not in {
                "contract_suffix",
                "contract_path_marker",
                "contract_content_type",
                "contract_content_marker",
                "html_link",
                "metadata_link",
                "jsonld_link",
            }
            or type(item.get("quality_score")) is not int
            or not 0 <= item["quality_score"] <= 100
            or item.get("coverage") not in {"existing_host", "candidate_gap"}
        ):
            raise VSDSourceIntelligenceError("Core handoff candidate became executable")
        _canonical_url(item.get("url"))
        trusted_source_id = item.get("trusted_source_id")
        if trusted_source_id is not None and (
            not isinstance(trusted_source_id, str)
            or not _SOURCE_ID_RE.fullmatch(trusted_source_id)
        ):
            raise VSDSourceIntelligenceError("Core handoff trust identity is invalid")
        tools = item.get("existing_tools")
        if not isinstance(tools, list) or tools != sorted(set(tools), key=str.casefold):
            raise VSDSourceIntelligenceError("Core handoff tool coverage is invalid")
        if (item["coverage"] == "existing_host") != bool(tools):
            raise VSDSourceIntelligenceError("Core handoff coverage is inconsistent")
        snapshot_sha256 = item.get("snapshot_content_sha256")
        if snapshot_sha256 is not None and (
            not isinstance(snapshot_sha256, str)
            or not _SHA256_RE.fullmatch(snapshot_sha256)
        ):
            raise VSDSourceIntelligenceError(
                "Core handoff snapshot identity is invalid"
            )
        candidate_ids.add(item["candidate_id"])
    proposals = value["demand_proposals"]
    if not isinstance(proposals, list) or len(proposals) > 20:
        raise VSDSourceIntelligenceError("Core handoff demand proposals are invalid")
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
            raise VSDSourceIntelligenceError("Core handoff demand proposal is invalid")
        if not isinstance(proposal.get("proposal_id"), str) or not _ID_RE.fullmatch(
            proposal["proposal_id"]
        ):
            raise VSDSourceIntelligenceError(
                "Core handoff proposal identity is invalid"
            )
        summary = _safe_text(
            proposal.get("public_summary"), field="public_summary", maximum=240
        )
        if len(summary) < 10 or _SECRET_RE.search(summary):
            raise VSDSourceIntelligenceError("Core handoff proposal summary is invalid")
    return copy.deepcopy(value)


def write_core_handoff(
    handoff: Any, destination: str | Path, *, replace: bool = False
) -> Path:
    """Persist one validated handoff locally; this function never transmits it."""
    checked = validate_core_handoff(handoff)
    path = Path(destination).expanduser()
    if path.suffix.casefold() != ".json":
        raise VSDSourceIntelligenceError("Core handoff must use a .json filename")
    if path.exists() and not replace:
        raise VSDSourceIntelligenceError("Core handoff already exists")
    raw = (
        json.dumps(checked, indent=2, sort_keys=True, ensure_ascii=True).encode("utf-8")
        + b"\n"
    )
    if len(raw) > _MAX_REPORT_BYTES:
        raise VSDSourceIntelligenceError("Core handoff exceeds 4 MB")
    _atomic_write(path, raw)
    return path


def render_core_issue(handoff: Any) -> tuple[str, str]:
    checked = validate_core_handoff(handoff)
    title = f"VSD source candidates: {len(checked['candidates'])} reviewed leads ({checked['handoff_id']})"
    lines = [
        "## Reviewed source candidates",
        "",
        f"Bundle: `{checked['handoff_id']}`",
        f"Reviewer: {checked['review']['reviewed_by']}",
        f"Decision: {checked['review']['decision_note']}",
        "",
        "These are inert discovery leads. No tool was generated, registered, approved, or executed by this handoff.",
        "",
        "| Candidate | Format | Score | Coverage | Snapshot | URL |",
        "|---|---:|---:|---|---|---|",
    ]
    for item in checked["candidates"]:
        snapshot = (
            item["snapshot_content_sha256"][:12]
            if item["snapshot_content_sha256"]
            else "not captured"
        )
        lines.append(
            f"| `{item['candidate_id']}` | {item['format_hint']} | {item['quality_score']} | "
            f"{item['coverage']} | `{snapshot}` | {item['url']} |"
        )
    if checked["demand_proposals"]:
        lines.extend(["", "## Sanitized unmet demand", ""])
        for proposal in checked["demand_proposals"]:
            lines.append(
                f"- `{proposal['proposal_id']}` (priority {proposal['priority_score']}): "
                f"{proposal['public_summary']}"
            )
    lines.extend(
        [
            "",
            "## Required next steps",
            "",
            "1. Confirm the source and terms with a human maintainer.",
            "2. Inspect the pinned contract snapshot and select an exact read-only operation.",
            "3. Verify credentials, schemas, rate limits, pagination, and representative responses.",
            "4. Use the existing approval and publication workflow before registration.",
        ]
    )
    body = "\n".join(lines) + "\n"
    if len(body.encode("utf-8")) > _MAX_ISSUE_BYTES:
        raise VSDSourceIntelligenceError("Rendered handoff issue exceeds 60 KB")
    return title, body


def _github_issue_request(token: str, title: str, body: str) -> dict[str, Any]:
    host = "api.github.com"
    addresses = _public_addresses(host)
    session = requests.Session()
    session.trust_env = False
    session.mount("https://", _PinnedHTTPSAdapter(host, addresses[0]))
    deadline = time.monotonic() + 20
    try:
        response = session.post(
            "https://api.github.com/repos/mims-harvard/ToolUniverse/issues",
            headers={
                "Accept": "application/vnd.github+json",
                "Accept-Encoding": "identity",
                "Authorization": f"Bearer {token}",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": _USER_AGENT,
            },
            json={"title": title, "body": body},
            timeout=Urllib3Timeout(total=20, connect=5, read=20),
            allow_redirects=False,
            stream=True,
        )
        try:
            peer_ip = _peer_address(response)
            _require_global_ip(peer_ip, context="Connected GitHub peer")
            if ipaddress.ip_address(peer_ip) != ipaddress.ip_address(addresses[0]):
                raise VSDSourceIntelligenceError(
                    "Connected GitHub peer did not match vetted DNS"
                )
            if response.status_code != 201 or response.is_redirect:
                raise VSDSourceIntelligenceError("GitHub issue submission failed")
            declared = response.headers.get("Content-Length")
            if declared is not None and (
                not declared.isdigit() or int(declared) > 100_000
            ):
                raise VSDSourceIntelligenceError("GitHub response is excessive")
            chunks: list[bytes] = []
            total = 0
            for chunk in _response_chunks(response, deadline=deadline):
                total += len(chunk)
                if total > 100_000:
                    raise VSDSourceIntelligenceError("GitHub response is excessive")
                chunks.append(chunk)
            try:
                payload = json.loads(b"".join(chunks).decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise VSDSourceIntelligenceError(
                    "GitHub issue response is not JSON"
                ) from exc
            if not isinstance(payload, dict):
                raise VSDSourceIntelligenceError(
                    "GitHub issue response is not an object"
                )
            return payload
        finally:
            response.close()
    except VSDPolicyError as exc:
        raise VSDSourceIntelligenceError(str(exc)) from exc
    except requests.RequestException as exc:
        raise VSDSourceIntelligenceError("GitHub issue submission failed") from exc
    finally:
        session.close()


def submit_core_handoff(
    handoff: Any,
    *,
    confirm: bool,
    token_env: str = "TOOLUNIVERSE_VSD_GITHUB_TOKEN",
    requester: Callable[[str, str, str], dict[str, Any]] = _github_issue_request,
) -> dict[str, Any]:
    """Submit one reviewed bundle to the fixed core repository issue endpoint."""
    checked = validate_core_handoff(handoff)
    if confirm is not True:
        raise VSDSourceIntelligenceError("Explicit submit confirmation is required")
    if token_env != "TOOLUNIVERSE_VSD_GITHUB_TOKEN":
        raise VSDSourceIntelligenceError(
            "GitHub token must use the fixed VSD environment name"
        )
    token = os.environ.get(token_env)
    if (
        not isinstance(token, str)
        or not 20 <= len(token) <= 4096
        or token != token.strip()
        or any(ord(character) < 33 or ord(character) > 126 for character in token)
    ):
        raise VSDSourceIntelligenceError(
            "GitHub token environment variable is missing or invalid"
        )
    title, body = render_core_issue(checked)
    try:
        payload = requester(token, title, body)
    except requests.RequestException as exc:
        raise VSDSourceIntelligenceError("GitHub issue submission failed") from exc
    issue_number = payload.get("number") if isinstance(payload, dict) else None
    issue_url = payload.get("html_url") if isinstance(payload, dict) else None
    if (
        type(issue_number) is not int
        or not isinstance(issue_url, str)
        or not issue_url.startswith(
            "https://github.com/mims-harvard/ToolUniverse/issues/"
        )
    ):
        raise VSDSourceIntelligenceError("GitHub issue response identity is invalid")
    return {
        "status": "success",
        "data": {
            "handoff_id": checked["handoff_id"],
            "repository": "mims-harvard/ToolUniverse",
            "issue_number": issue_number,
            "issue_url": issue_url,
            "submitted": True,
        },
    }
