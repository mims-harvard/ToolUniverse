"""Demand-driven discovery of non-executable public data API candidates."""

from __future__ import annotations

import hashlib
import html
import json
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlsplit

from .base_tool import BaseTool
from .tool_registry import register_tool
from .vsd_tool import VSDPolicyError, _safe_get_json

_CATALOG_ENDPOINT = "https://api.us.socrata.com/api/catalog/v1"
_DATASET_ID_RE = re.compile(r"^[a-z0-9]{4}-[a-z0-9]{4}$")
_HOST_RE = re.compile(
    r"^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$"
)
_TOKEN_RE = re.compile(r"[a-z0-9]+")
_HTML_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")
_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "api",
        "data",
        "dataset",
        "for",
        "from",
        "in",
        "of",
        "on",
        "the",
        "to",
        "with",
    }
)
_TYPE_NAMES = {
    "Calendar date": "string",
    "Checkbox": "boolean",
    # SODA JSON serializes arbitrary-precision numeric values as strings.
    "Money": "string",
    "Number": "string",
    "Point": "object",
    "Text": "string",
}


class VSDDiscoveryError(VSDPolicyError):
    """Raised when catalog input or output violates the discovery contract."""


def _bounded_text(value: Any, maximum: int) -> str:
    if value is None:
        return ""
    text = html.unescape(_HTML_TAG_RE.sub(" ", str(value)))
    text = _WHITESPACE_RE.sub(" ", text).strip()
    return "".join(character for character in text if ord(character) >= 32)[:maximum]


def _tokens(value: Any) -> set[str]:
    return {
        token
        for token in _TOKEN_RE.findall(_bounded_text(value, 10_000).casefold())
        if token not in _STOPWORDS and len(token) > 1
    }


def _candidate_endpoint(domain: Any, dataset_id: Any) -> str | None:
    host = str(domain or "").strip().lower().rstrip(".")
    identifier = str(dataset_id or "").strip().lower()
    if not _HOST_RE.fullmatch(host) or not _DATASET_ID_RE.fullmatch(identifier):
        return None
    return f"https://{host}/resource/{identifier}.json"


def _field_hints(resource: dict[str, Any]) -> list[dict[str, str]]:
    names = resource.get("columns_name") or []
    fields = resource.get("columns_field_name") or []
    types = resource.get("columns_datatype") or []
    descriptions = resource.get("columns_description") or []
    if not all(
        isinstance(items, list) for items in (names, fields, types, descriptions)
    ):
        return []
    output: list[dict[str, str]] = []
    for index, field in enumerate(fields[:50]):
        if not isinstance(field, str) or not re.fullmatch(
            r"^[a-zA-Z][a-zA-Z0-9_]{0,127}$", field
        ):
            continue
        provider_type = types[index] if index < len(types) else "Text"
        output.append(
            {
                "field": field,
                "label": _bounded_text(
                    names[index] if index < len(names) else field, 120
                ),
                "provider_type": _bounded_text(provider_type, 80),
                "json_type": _TYPE_NAMES.get(str(provider_type), "string"),
                "description": _bounded_text(
                    descriptions[index] if index < len(descriptions) else "", 300
                ),
            }
        )
    return output


def _score_candidate(query: str, candidate: dict[str, Any]) -> dict[str, float]:
    query_tokens = _tokens(query)
    searchable = " ".join(
        [
            candidate["name"],
            candidate["description"],
            " ".join(candidate["tags"]),
            " ".join(
                f"{field['label']} {field['field']}" for field in candidate["fields"]
            ),
        ]
    )
    matched = query_tokens & _tokens(searchable)
    coverage = len(matched) / max(1, len(query_tokens))
    exact_phrase = float(query.casefold() in searchable.casefold())
    api_ready = float(bool(candidate["api_endpoint"] and candidate["fields"]))
    official = float(candidate["provenance_label"] == "official")
    government = float(
        (urlsplit(candidate["api_endpoint"] or "").hostname or "").endswith(".gov")
    )
    total = (
        0.55 * coverage
        + 0.10 * exact_phrase
        + 0.20 * api_ready
        + 0.10 * official
        + 0.05 * government
    )
    return {
        "query_coverage": round(coverage, 4),
        "exact_phrase": exact_phrase,
        "api_ready": api_ready,
        "official_catalog_label": official,
        "government_domain": government,
        "total": round(total, 4),
    }


def _normalize_result(query: str, item: Any) -> dict[str, Any] | None:
    if not isinstance(item, dict):
        return None
    resource = item.get("resource")
    metadata = item.get("metadata")
    classification = item.get("classification")
    if not isinstance(resource, dict) or not isinstance(metadata, dict):
        return None
    if resource.get("type") != "dataset":
        return None
    endpoint = _candidate_endpoint(metadata.get("domain"), resource.get("id"))
    if endpoint is None:
        return None
    fields = _field_hints(resource)
    if not fields:
        return None
    classification = classification if isinstance(classification, dict) else {}
    raw_tags = [
        *(classification.get("tags") or []),
        *(classification.get("domain_tags") or []),
    ]
    tags = sorted(
        {
            _bounded_text(tag, 80)
            for tag in raw_tags
            if isinstance(tag, (str, int, float)) and _bounded_text(tag, 80)
        }
    )[:30]
    candidate = {
        "candidate_id": hashlib.sha256(endpoint.encode("utf-8")).hexdigest()[:16],
        "name": _bounded_text(resource.get("name"), 200),
        "description": _bounded_text(resource.get("description"), 800),
        "api_endpoint": endpoint,
        "documentation_url": _bounded_text(
            item.get("permalink") or item.get("link"), 2048
        ),
        "catalog_domain": _bounded_text(metadata.get("domain"), 253),
        "dataset_id": str(resource.get("id")),
        "updated_at": _bounded_text(resource.get("updatedAt"), 80),
        "provenance_label": _bounded_text(resource.get("provenance"), 80),
        "tags": tags,
        "fields": fields,
        "metadata_trust": "untrusted_catalog_metadata",
        "approval_state": "unreviewed_candidate",
        "execution_allowed": False,
    }
    candidate["score"] = _score_candidate(query, candidate)
    return candidate


def discover_api_candidates(
    query: str, *, limit: int, catalog_payload: Any
) -> list[dict[str, Any]]:
    """Normalize and rank one bounded Socrata catalog response."""
    if not isinstance(catalog_payload, dict):
        raise VSDDiscoveryError("Catalog response must be an object")
    results = catalog_payload.get("results")
    if not isinstance(results, list) or len(results) > 100:
        raise VSDDiscoveryError("Catalog response contained an invalid result list")
    candidates = [
        candidate
        for item in results
        if (candidate := _normalize_result(query, item)) is not None
    ]
    deduplicated = {candidate["api_endpoint"]: candidate for candidate in candidates}
    ranked = sorted(
        deduplicated.values(),
        key=lambda candidate: (
            -candidate["score"]["total"],
            candidate["name"].casefold(),
            candidate["api_endpoint"],
        ),
    )
    return ranked[:limit]


@register_tool("VSDDiscoverAPICandidates")
class VSDDiscoverAPICandidates(BaseTool):
    """Search explicit public catalogs and return non-executable candidates."""

    def __init__(self, tool_config, tooluniverse=None):
        super().__init__(tool_config)
        self.tooluniverse = tooluniverse

    def run(self, arguments=None, **_: Any):
        arguments = arguments or {}
        query = _bounded_text(arguments.get("query"), 200)
        if len(query) < 2:
            raise VSDDiscoveryError("query must contain 2-200 characters")
        limit = arguments.get("limit", 10)
        if (
            isinstance(limit, bool)
            or not isinstance(limit, int)
            or not 1 <= limit <= 20
        ):
            raise VSDDiscoveryError("limit must be an integer between 1 and 20")
        raw_providers = arguments.get("providers")
        if raw_providers is not None:
            from .vsd_catalog_providers import (
                PROVIDER_ORDER,
                discover_multi_catalog_candidates,
            )

            if (
                not isinstance(raw_providers, list)
                or not 1 <= len(raw_providers) <= len(PROVIDER_ORDER)
                or len(raw_providers) != len(set(raw_providers))
                or any(provider not in PROVIDER_ORDER for provider in raw_providers)
            ):
                raise VSDDiscoveryError(
                    "providers must contain 1-5 unique supported provider IDs"
                )
            exclude_registered = arguments.get("exclude_registered", True)
            if type(exclude_registered) is not bool:
                raise VSDDiscoveryError("exclude_registered must be a boolean")
            return {
                "status": "success",
                "data": discover_multi_catalog_candidates(
                    query,
                    providers=list(raw_providers),
                    limit=limit,
                    fetch_json=_safe_get_json,
                    socrata_normalizer=discover_api_candidates,
                    tooluniverse=self.tooluniverse,
                    exclude_registered=exclude_registered,
                ),
            }
        catalog_limit = min(50, max(10, limit * 3))
        payload, request = _safe_get_json(
            _CATALOG_ENDPOINT,
            {"q": query, "only": "datasets", "limit": catalog_limit},
            timeout=20,
        )
        candidates = discover_api_candidates(
            query, limit=limit, catalog_payload=payload
        )
        return {
            "status": "success",
            "data": {
                "query": query,
                "candidates": candidates,
                "candidate_count": len(candidates),
                "catalog_result_count": payload.get("resultSetSize"),
                "boundary": (
                    "Candidates are untrusted catalog metadata. They are not approved, "
                    "probed, executable, or scientific endorsements."
                ),
                "provenance": {
                    "provider": "Socrata Open Data API Catalog",
                    "endpoint": _CATALOG_ENDPOINT,
                    "query_params": {
                        "q": query,
                        "only": "datasets",
                        "limit": catalog_limit,
                    },
                    "retrieved_at": datetime.now(timezone.utc).isoformat(),
                    "http_status": request["status_code"],
                    "content_type": request["content_type"],
                    "response_bytes": request["response_bytes"],
                    "redirects": request["redirects"],
                    "payload_sha256": hashlib.sha256(
                        json.dumps(
                            payload,
                            sort_keys=True,
                            separators=(",", ":"),
                            ensure_ascii=True,
                        ).encode("utf-8")
                    ).hexdigest(),
                },
            },
        }


__all__ = [
    "VSDDiscoverAPICandidates",
    "VSDDiscoveryError",
    "discover_api_candidates",
]
