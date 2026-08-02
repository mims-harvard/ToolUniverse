"""Normalized, non-executable discovery across reviewed public catalogs."""

from __future__ import annotations

import hashlib
import html
import json
import os
import re
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from .vsd_tool import VSDPolicyError

PROVIDER_ORDER = (
    "socrata",
    "datagov",
    "data_europa",
    "ckan_data_gov_uk",
    "apis_guru",
)

_ENDPOINTS = {
    "socrata": "https://api.us.socrata.com/api/catalog/v1",
    "datagov": "https://api.gsa.gov/technology/datagov/v4/search",
    "data_europa": "https://data.europa.eu/api/hub/search/search",
    "ckan_data_gov_uk": (
        "https://ckan.publishing.service.gov.uk/api/3/action/package_search"
    ),
    "apis_guru": "https://api.apis.guru/v2/list.json",
}
_PROVIDER_LABELS = {
    "socrata": "Socrata Open Data API Catalog",
    "datagov": "Data.gov Catalog API",
    "data_europa": "European Data Portal Hub Search",
    "ckan_data_gov_uk": "Data.gov.uk CKAN Catalog",
    "apis_guru": "APIs.guru OpenAPI Directory",
}
_TOKEN_RE = re.compile(r"[a-z0-9]+")
_HTML_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")
_HOST_RE = re.compile(
    r"^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$"
)
_SOCRATA_VIEW_RE = re.compile(
    r"^https://(?P<host>[a-z0-9.-]+)/api/views/(?P<id>[a-z0-9]{4}-[a-z0-9]{4})/?$",
    re.IGNORECASE,
)
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
_FORMAT_HINTS = {
    "application/json": ("json", "rest"),
    "application/geo+json": ("json", "rest"),
    "application/vnd.geo+json": ("json", "rest"),
    "application/xml": ("xml", "rest"),
    "text/xml": ("xml", "rest"),
    "text/csv": ("csv", "rest"),
}


class VSDCatalogProviderError(VSDPolicyError):
    """Raised when one catalog payload violates its bounded provider contract."""


def _bounded_text(value: Any, maximum: int) -> str:
    if value is None:
        return ""
    text = html.unescape(_HTML_TAG_RE.sub(" ", str(value)))
    text = _WHITESPACE_RE.sub(" ", text).strip()
    return "".join(character for character in text if ord(character) >= 32)[:maximum]


def _tokens(value: Any) -> set[str]:
    return {
        token
        for token in _TOKEN_RE.findall(_bounded_text(value, 20_000).casefold())
        if token not in _STOPWORDS and len(token) > 1
    }


def _localized(value: Any) -> str:
    if isinstance(value, str):
        return value
    if not isinstance(value, dict):
        return ""
    for key in ("en", "en-gb", "en-us"):
        if isinstance(value.get(key), str):
            return value[key]
    return next((item for item in value.values() if isinstance(item, str)), "")


def _text_list(value: Any, *, maximum: int = 30) -> list[str]:
    if not isinstance(value, list):
        return []
    return sorted(
        {
            text
            for item in value[: maximum * 2]
            if (text := _bounded_text(_localized(item), 100))
        },
        key=str.casefold,
    )[:maximum]


def _https_url(value: Any) -> str:
    text = _bounded_text(value, 2048)
    if not text:
        return ""
    try:
        parsed = urlsplit(text)
        port = parsed.port
    except ValueError:
        return ""
    host = (parsed.hostname or "").casefold().rstrip(".")
    if (
        parsed.scheme.casefold() != "https"
        or not _HOST_RE.fullmatch(host)
        or parsed.username is not None
        or parsed.password is not None
        or port not in {None, 443}
        or parsed.fragment
    ):
        return ""
    return urlunsplit(("https", host, parsed.path or "/", parsed.query, ""))


def _media_contract(media_type: Any, format_name: Any) -> tuple[str, str] | None:
    media = _bounded_text(media_type, 120).casefold().split(";", 1)[0].strip()
    label = _bounded_text(format_name, 120).casefold()
    if media in _FORMAT_HINTS:
        return _FORMAT_HINTS[media]
    if media.endswith("+json") or "geojson" in label or label == "json":
        return "json", "rest"
    if media.endswith("+xml") or label in {"xml", "rdf/xml"}:
        return "xml", "rest"
    if label in {"csv", "comma-separated values"}:
        return "csv", "rest"
    if "api" in label or "rest" in label or "json" in label:
        return "json", "rest"
    return None


def _score_candidate(query: str, candidate: dict[str, Any]) -> dict[str, float]:
    query_tokens = _tokens(query)
    searchable = " ".join(
        [
            candidate["name"],
            candidate["description"],
            candidate["publisher"],
            " ".join(candidate["tags"]),
            " ".join(
                f"{field.get('label', '')} {field.get('field', '')}"
                for field in candidate["fields"]
            ),
        ]
    )
    matched = query_tokens & _tokens(searchable)
    coverage = len(matched) / max(1, len(query_tokens))
    exact_phrase = float(query.casefold() in searchable.casefold())
    api_ready = float(bool(candidate["specification_url"] or candidate["api_endpoint"]))
    contract_available = float(bool(candidate["specification_url"]))
    official = float(
        candidate["provenance_label"]
        in {"official", "government_catalog", "official_openapi_directory"}
    )
    host = urlsplit(
        candidate["api_endpoint"]
        or candidate["specification_url"]
        or candidate["documentation_url"]
    ).hostname
    government = float(bool(host and (host.endswith((".gov", ".gov.uk")))))
    metadata_completeness = (
        sum(bool(candidate[field]) for field in ("publisher", "license", "updated_at"))
        / 3
    )
    total = (
        0.5 * coverage
        + 0.05 * exact_phrase
        + 0.15 * api_ready
        + 0.1 * contract_available
        + 0.08 * official
        + 0.05 * government
        + 0.07 * metadata_completeness
    )
    return {
        "matched_query_terms": len(matched),
        "query_term_count": len(query_tokens),
        "query_coverage": round(coverage, 4),
        "exact_phrase": exact_phrase,
        "api_ready": api_ready,
        "contract_available": contract_available,
        "official_catalog_label": official,
        "government_domain": government,
        "metadata_completeness": round(metadata_completeness, 4),
        "total": round(total, 4),
    }


def _is_relevant(query: str, candidate: dict[str, Any]) -> bool:
    query_term_count = candidate["score"]["query_term_count"]
    minimum_matches = 2 if query_term_count > 3 else 1
    return candidate["score"]["matched_query_terms"] >= minimum_matches


def _candidate(
    query: str,
    *,
    provider: str,
    record_id: Any,
    name: Any,
    description: Any,
    api_endpoint: Any = "",
    specification_url: Any = "",
    documentation_url: Any = "",
    publisher: Any = "",
    license_value: Any = "",
    updated_at: Any = "",
    tags: Any = None,
    fields: Any = None,
    media_type: Any = "",
    response_format: str = "json",
    interface_type: str = "rest",
    provenance_label: str,
    candidate_kind: str = "data_endpoint",
) -> dict[str, Any] | None:
    endpoint = _https_url(api_endpoint)
    specification = _https_url(specification_url)
    if not endpoint and not specification:
        return None
    documentation = _https_url(documentation_url)
    identity = specification or endpoint
    normalized_fields = fields if isinstance(fields, list) else []
    normalized_fields = [
        item for item in normalized_fields[:50] if isinstance(item, dict)
    ]
    record = _bounded_text(record_id, 500)
    candidate = {
        "candidate_id": hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16],
        "candidate_kind": candidate_kind,
        "name": _bounded_text(name, 200),
        "description": _bounded_text(description, 800),
        "api_endpoint": endpoint,
        "specification_url": specification,
        "documentation_url": documentation,
        "catalog_provider": provider,
        "catalog_domain": urlsplit(_ENDPOINTS[provider]).hostname or "",
        "catalog_record_id": record,
        "dataset_id": record,
        "publisher": _bounded_text(publisher, 300),
        "license": _bounded_text(_localized(license_value), 500),
        "updated_at": _bounded_text(updated_at, 100),
        "provenance_label": provenance_label,
        "tags": _text_list(tags),
        "fields": normalized_fields,
        "media_type": _bounded_text(media_type, 120),
        "response_format": response_format,
        "interface_type": interface_type,
        "catalog_sources": [
            {
                "provider": provider,
                "record_id": record,
                "documentation_url": documentation,
            }
        ],
        "metadata_trust": "untrusted_catalog_metadata",
        "approval_state": "unreviewed_candidate",
        "execution_allowed": False,
    }
    candidate["score"] = _score_candidate(query, candidate)
    return candidate


def _require_results(value: Any, *, provider: str, maximum: int = 100) -> list[Any]:
    if not isinstance(value, list) or len(value) > maximum:
        raise VSDCatalogProviderError(
            f"{provider} catalog response contained an invalid result list"
        )
    return value


def normalize_datagov(query: str, payload: Any) -> tuple[list[dict[str, Any]], int]:
    if not isinstance(payload, dict):
        raise VSDCatalogProviderError("datagov catalog response must be an object")
    results = _require_results(payload.get("results"), provider="datagov")
    candidates: list[dict[str, Any]] = []
    for item in results:
        if not isinstance(item, dict):
            continue
        dcat = item.get("dcat") if isinstance(item.get("dcat"), dict) else {}
        record_id = dcat.get("identifier") or item.get("identifier") or item.get("slug")
        title = dcat.get("title") or item.get("title")
        description = dcat.get("description") or item.get("description")
        publisher = (
            dcat.get("publisher") or item.get("organization") or item.get("publisher")
        )
        if isinstance(publisher, dict):
            publisher = publisher.get("name") or publisher.get("slug")
        tags = dcat.get("keyword") or item.get("keyword") or []
        documentation = dcat.get("landingPage")
        if not documentation and item.get("slug"):
            documentation = f"https://catalog.data.gov/dataset/{item['slug']}"
        distributions = dcat.get("distribution") or []
        if isinstance(distributions, list):
            for index, distribution in enumerate(distributions[:20]):
                if not isinstance(distribution, dict):
                    continue
                endpoint = distribution.get("accessURL") or distribution.get(
                    "downloadURL"
                )
                contract = _media_contract(
                    distribution.get("mediaType"), distribution.get("format")
                )
                if contract is None:
                    continue
                response_format, interface_type = contract
                candidate = _candidate(
                    query,
                    provider="datagov",
                    record_id=f"{record_id or item.get('slug', '')}#{index}",
                    name=distribution.get("title") or title,
                    description=distribution.get("description") or description,
                    api_endpoint=endpoint,
                    documentation_url=documentation,
                    publisher=publisher,
                    license_value=dcat.get("license"),
                    updated_at=dcat.get("modified") or item.get("last_harvested_date"),
                    tags=tags,
                    media_type=distribution.get("mediaType")
                    or distribution.get("format"),
                    response_format=response_format,
                    interface_type=interface_type,
                    provenance_label="government_catalog",
                )
                if candidate:
                    candidates.append(candidate)
        identifier = _https_url(record_id)
        match = _SOCRATA_VIEW_RE.fullmatch(identifier)
        if match:
            endpoint = (
                f"https://{match.group('host')}/resource/{match.group('id')}.json"
            )
            candidate = _candidate(
                query,
                provider="datagov",
                record_id=record_id,
                name=title,
                description=description,
                api_endpoint=endpoint,
                documentation_url=documentation,
                publisher=publisher,
                license_value=dcat.get("license"),
                updated_at=dcat.get("modified") or item.get("last_harvested_date"),
                tags=tags,
                media_type="application/json",
                provenance_label="government_catalog",
            )
            if candidate:
                candidates.append(candidate)
    return candidates, len(results)


def normalize_ckan(query: str, payload: Any) -> tuple[list[dict[str, Any]], int]:
    if not isinstance(payload, dict) or payload.get("success") is not True:
        raise VSDCatalogProviderError("CKAN catalog response must be successful")
    result = payload.get("result")
    if not isinstance(result, dict):
        raise VSDCatalogProviderError("CKAN catalog response result is invalid")
    results = _require_results(result.get("results"), provider="CKAN")
    candidates: list[dict[str, Any]] = []
    for item in results:
        if not isinstance(item, dict):
            continue
        organization = item.get("organization")
        publisher = (
            organization.get("title") or organization.get("name")
            if isinstance(organization, dict)
            else ""
        )
        tags = [
            entry.get("display_name") or entry.get("name")
            for entry in item.get("tags", [])[:30]
            if isinstance(entry, dict)
        ]
        documentation = (
            f"https://data.gov.uk/dataset/{item['name']}" if item.get("name") else ""
        )
        for index, resource in enumerate((item.get("resources") or [])[:20]):
            if not isinstance(resource, dict):
                continue
            contract = _media_contract(resource.get("mimetype"), resource.get("format"))
            if contract is None:
                continue
            response_format, interface_type = contract
            candidate = _candidate(
                query,
                provider="ckan_data_gov_uk",
                record_id=f"{item.get('id') or item.get('name') or ''}#{index}",
                name=resource.get("name") or item.get("title"),
                description=resource.get("description") or item.get("notes"),
                api_endpoint=resource.get("url"),
                documentation_url=documentation,
                publisher=publisher,
                license_value=item.get("license_title") or item.get("license_url"),
                updated_at=item.get("metadata_modified"),
                tags=tags,
                media_type=resource.get("mimetype") or resource.get("format"),
                response_format=response_format,
                interface_type=interface_type,
                provenance_label="government_catalog",
            )
            if candidate:
                candidates.append(candidate)
    count = result.get("count")
    return candidates, count if isinstance(count, int) else len(results)


def normalize_data_europa(query: str, payload: Any) -> tuple[list[dict[str, Any]], int]:
    if not isinstance(payload, dict) or not isinstance(payload.get("result"), dict):
        raise VSDCatalogProviderError("data_europa catalog response is invalid")
    result = payload["result"]
    results = _require_results(result.get("results"), provider="data_europa")
    candidates: list[dict[str, Any]] = []
    for item in results:
        if not isinstance(item, dict):
            continue
        publisher = item.get("publisher")
        if isinstance(publisher, dict):
            publisher = publisher.get("name")
        tags = [
            _localized(category.get("label") or category.get("title"))
            for category in (item.get("categories") or [])[:30]
            if isinstance(category, dict)
        ]
        documentation = item.get("resource")
        for index, distribution in enumerate((item.get("distributions") or [])[:20]):
            if not isinstance(distribution, dict):
                continue
            format_value = distribution.get("format")
            if isinstance(format_value, dict):
                format_value = format_value.get("label") or format_value.get("id")
            media_type = distribution.get("media_type") or distribution.get("mediaType")
            contract = _media_contract(media_type, format_value)
            if contract is None:
                continue
            urls = (
                distribution.get("access_url") or distribution.get("download_url") or []
            )
            if isinstance(urls, str):
                urls = [urls]
            endpoint = next((_https_url(url) for url in urls if _https_url(url)), "")
            response_format, interface_type = contract
            candidate = _candidate(
                query,
                provider="data_europa",
                record_id=f"{item.get('id') or item.get('resource') or ''}#{index}",
                name=_localized(distribution.get("title"))
                or _localized(item.get("title")),
                description=_localized(distribution.get("description"))
                or _localized(item.get("description")),
                api_endpoint=endpoint,
                documentation_url=documentation,
                publisher=publisher,
                license_value=distribution.get("license"),
                updated_at=item.get("modified")
                or (item.get("catalog_record") or {}).get("modified"),
                tags=tags,
                media_type=media_type or format_value,
                response_format=response_format,
                interface_type=interface_type,
                provenance_label="government_catalog",
            )
            if candidate:
                candidates.append(candidate)
    count = result.get("count")
    return candidates, count if isinstance(count, int) else len(results)


def normalize_apis_guru(query: str, payload: Any) -> tuple[list[dict[str, Any]], int]:
    if not isinstance(payload, dict) or len(payload) > 5000:
        raise VSDCatalogProviderError("apis_guru catalog response is invalid")
    candidates: list[dict[str, Any]] = []
    for provider_name, entry in payload.items():
        if not isinstance(provider_name, str) or not isinstance(entry, dict):
            continue
        versions = entry.get("versions")
        preferred = entry.get("preferred")
        if not isinstance(versions, dict) or not isinstance(preferred, str):
            continue
        version = versions.get(preferred)
        if not isinstance(version, dict):
            continue
        info = version.get("info") if isinstance(version.get("info"), dict) else {}
        external = (
            version.get("externalDocs")
            if isinstance(version.get("externalDocs"), dict)
            else {}
        )
        categories = info.get("x-apisguru-categories") or []
        if isinstance(categories, str):
            categories = [categories]
        candidate = _candidate(
            query,
            provider="apis_guru",
            record_id=f"{provider_name}:{preferred}",
            name=info.get("title") or provider_name,
            description=info.get("description"),
            specification_url=version.get("swaggerUrl"),
            documentation_url=external.get("url") or version.get("link"),
            publisher=provider_name.split(":", 1)[0],
            license_value=(info.get("license") or {}).get("name")
            if isinstance(info.get("license"), dict)
            else "",
            updated_at=version.get("updated") or version.get("added"),
            tags=categories,
            media_type="application/vnd.oai.openapi+json",
            response_format="json",
            interface_type="openapi",
            provenance_label="official_openapi_directory",
            candidate_kind="openapi_specification",
        )
        if candidate and _is_relevant(query, candidate):
            candidates.append(candidate)
    return candidates, len(payload)


def _augment_socrata(candidate: dict[str, Any]) -> dict[str, Any]:
    augmented = dict(candidate)
    augmented.update(
        {
            "candidate_kind": "data_endpoint",
            "specification_url": "",
            "catalog_provider": "socrata",
            "catalog_record_id": candidate.get("dataset_id", ""),
            "publisher": candidate.get("catalog_domain", ""),
            "license": "",
            "media_type": "application/json",
            "response_format": "json",
            "interface_type": "soda",
            "catalog_sources": [
                {
                    "provider": "socrata",
                    "record_id": candidate.get("dataset_id", ""),
                    "documentation_url": candidate.get("documentation_url", ""),
                }
            ],
        }
    )
    augmented["score"] = _score_candidate("", augmented)
    return augmented


def normalize_provider_payload(
    provider: str,
    query: str,
    payload: Any,
    *,
    socrata_normalizer: Callable[..., list[dict[str, Any]]] | None = None,
    limit: int = 20,
) -> tuple[list[dict[str, Any]], int]:
    if provider == "socrata":
        if socrata_normalizer is None:
            raise VSDCatalogProviderError("Socrata normalizer is required")
        candidates = socrata_normalizer(query, limit=limit, catalog_payload=payload)
        augmented = [_augment_socrata(candidate) for candidate in candidates]
        for candidate in augmented:
            candidate["score"] = _score_candidate(query, candidate)
        count = payload.get("resultSetSize") if isinstance(payload, dict) else None
        relevant = [item for item in augmented if _is_relevant(query, item)]
        return relevant, count if isinstance(count, int) else len(relevant)
    if provider == "datagov":
        candidates, count = normalize_datagov(query, payload)
        return [item for item in candidates if _is_relevant(query, item)], count
    if provider == "data_europa":
        candidates, count = normalize_data_europa(query, payload)
        return [item for item in candidates if _is_relevant(query, item)], count
    if provider == "ckan_data_gov_uk":
        candidates, count = normalize_ckan(query, payload)
        return [item for item in candidates if _is_relevant(query, item)], count
    if provider == "apis_guru":
        return normalize_apis_guru(query, payload)
    raise VSDCatalogProviderError(f"Unsupported catalog provider {provider!r}")


def _request_plan(provider: str, query: str, limit: int) -> dict[str, Any]:
    catalog_limit = min(50, max(5, limit * 3))
    if provider == "socrata":
        return {
            "endpoint": _ENDPOINTS[provider],
            "params": {"q": query, "only": "datasets", "limit": catalog_limit},
            "headers": {},
            "max_response_bytes": 1_000_000,
            "credential_ref": None,
        }
    if provider == "datagov":
        credential_ref = "TOOLUNIVERSE_DATAGOV_API_KEY"
        key = os.environ.get(credential_ref) or "DEMO_KEY"
        return {
            "endpoint": _ENDPOINTS[provider],
            "params": {"q": query, "size": catalog_limit},
            "headers": {"X-Api-Key": key},
            "max_response_bytes": 1_000_000,
            "credential_ref": credential_ref if key != "DEMO_KEY" else "DEMO_KEY",
        }
    if provider == "data_europa":
        return {
            "endpoint": _ENDPOINTS[provider],
            # Hub Search responses contain large embedded DCAT records. Ten
            # results remain below the transport ceiling in live validation.
            "params": {"q": query, "limit": min(10, catalog_limit)},
            "headers": {},
            "max_response_bytes": 1_000_000,
            "credential_ref": None,
        }
    if provider == "ckan_data_gov_uk":
        return {
            "endpoint": _ENDPOINTS[provider],
            "params": {"q": query, "rows": catalog_limit},
            "headers": {},
            "max_response_bytes": 1_000_000,
            "credential_ref": None,
        }
    if provider == "apis_guru":
        return {
            "endpoint": _ENDPOINTS[provider],
            "params": {},
            "headers": {},
            "max_response_bytes": 10_000_000,
            "credential_ref": None,
        }
    raise VSDCatalogProviderError(f"Unsupported catalog provider {provider!r}")


def _provenance(
    provider: str,
    plan: dict[str, Any],
    request: dict[str, Any],
    payload: Any,
    *,
    retrieved_at: str | None = None,
) -> dict[str, Any]:
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return {
        "provider_id": provider,
        "provider": _PROVIDER_LABELS[provider],
        "endpoint": plan["endpoint"],
        "query_params": plan["params"],
        "request_header_names": sorted(plan["headers"]),
        "credential_ref": plan["credential_ref"],
        "retrieved_at": retrieved_at or datetime.now(timezone.utc).isoformat(),
        "http_status": request["status_code"],
        "content_type": request["content_type"],
        "response_bytes": request["response_bytes"],
        "redirects": request["redirects"],
        "payload_sha256": hashlib.sha256(encoded).hexdigest(),
    }


def _deduplicate(
    candidates: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], int]:
    deduplicated: dict[str, dict[str, Any]] = {}
    duplicate_count = 0
    for candidate in candidates:
        identity = candidate["specification_url"] or candidate["api_endpoint"]
        current = deduplicated.get(identity)
        if current is None:
            deduplicated[identity] = candidate
            continue
        duplicate_count += 1
        winner, other = (
            (candidate, current)
            if candidate["score"]["total"] > current["score"]["total"]
            else (current, candidate)
        )
        merged = dict(winner)
        sources = {
            (item["provider"], item["record_id"]): item
            for item in [*winner["catalog_sources"], *other["catalog_sources"]]
        }
        merged["catalog_sources"] = [sources[key] for key in sorted(sources)]
        deduplicated[identity] = merged
    ranked = sorted(
        deduplicated.values(),
        key=lambda item: (
            -item["score"]["total"],
            item["name"].casefold(),
            item["candidate_id"],
        ),
    )
    return ranked, duplicate_count


def _registry_deduplicate(
    candidates: list[dict[str, Any]], tooluniverse: Any
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int]:
    if tooluniverse is None:
        return candidates, [], 0
    from .vsd_coverage import (
        _operation_identity,
        _registry_tools,
        _resolve_normalized_capability,
        normalize_capability_request,
    )

    registry = _registry_tools(tooluniverse)
    kept: list[dict[str, Any]] = []
    duplicates: list[dict[str, Any]] = []
    for candidate in candidates:
        endpoint = candidate["api_endpoint"]
        parsed = urlsplit(endpoint)
        if not endpoint or parsed.query:
            candidate["registry_coverage"] = {
                "classification": "not_assessed",
                "matches": [],
                "reason": "No query-free operation endpoint was available.",
            }
            kept.append(candidate)
            continue
        fields = [
            str(field.get("field"))
            for field in candidate["fields"][:20]
            if field.get("field")
        ]
        request = normalize_capability_request(
            {
                "description": candidate["name"]
                or candidate["description"]
                or "catalog operation",
                "provider": parsed.hostname,
                "method": "GET",
                "endpoint": endpoint,
                "output_fields": fields,
            }
        )
        coverage = _resolve_normalized_capability(request, registry, limit=5)["data"]
        operation_identity = (
            "GET",
            (parsed.hostname or "").casefold().rstrip("."),
            re.sub(r"/+", "/", parsed.path or "/").rstrip("/") or "/",
        )
        exact_operation_names = sorted(
            {
                str(config.get("name"))
                for config in registry
                if _operation_identity(config) == operation_identity
                and config.get("name")
            },
            key=str.casefold,
        )
        classification = (
            "existing_exact" if exact_operation_names else coverage["classification"]
        )
        summary = {
            "classification": classification,
            "matches": exact_operation_names
            or [match["name"] for match in coverage["matches"]],
            "semantic_classification": coverage["classification"],
            "registry_sha256": coverage["registry_sha256"],
        }
        candidate["registry_coverage"] = summary
        if classification == "existing_exact":
            duplicates.append(
                {
                    "candidate_id": candidate["candidate_id"],
                    "identity": endpoint,
                    **summary,
                }
            )
        else:
            kept.append(candidate)
    return kept, duplicates, len(registry)


def discover_multi_catalog_candidates(
    query: str,
    *,
    providers: list[str],
    limit: int,
    fetch_json: Callable[..., tuple[Any, dict[str, Any]]],
    socrata_normalizer: Callable[..., list[dict[str, Any]]],
    tooluniverse: Any = None,
    exclude_registered: bool = True,
    retrieved_at: str | None = None,
) -> dict[str, Any]:
    if not isinstance(query, str) or not 2 <= len(query) <= 200:
        raise VSDCatalogProviderError("query must contain 2-200 characters")
    if (
        not isinstance(providers, list)
        or not 1 <= len(providers) <= len(PROVIDER_ORDER)
        or len(providers) != len(set(providers))
        or any(provider not in PROVIDER_ORDER for provider in providers)
    ):
        raise VSDCatalogProviderError(
            "providers must contain 1-5 unique supported provider IDs"
        )
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 20:
        raise VSDCatalogProviderError("limit must be an integer between 1 and 20")
    if type(exclude_registered) is not bool:
        raise VSDCatalogProviderError("exclude_registered must be a boolean")
    if retrieved_at is not None and (
        not isinstance(retrieved_at, str) or not 1 <= len(retrieved_at) <= 100
    ):
        raise VSDCatalogProviderError("retrieved_at must be a bounded string")
    all_candidates: list[dict[str, Any]] = []
    provider_results: list[dict[str, Any]] = []
    total_catalog_results = 0
    for provider in PROVIDER_ORDER:
        if provider not in providers:
            continue
        plan = _request_plan(provider, query, limit)
        try:
            kwargs: dict[str, Any] = {"timeout": 20}
            if plan["headers"]:
                kwargs["headers"] = plan["headers"]
            if plan["max_response_bytes"] != 1_000_000:
                kwargs["max_response_bytes"] = plan["max_response_bytes"]
            payload, request = fetch_json(
                plan["endpoint"], plan["params"] or None, **kwargs
            )
            candidates, result_count = normalize_provider_payload(
                provider,
                query,
                payload,
                socrata_normalizer=socrata_normalizer,
                limit=max(limit, 20),
            )
            total_catalog_results += result_count
            all_candidates.extend(candidates)
            provider_results.append(
                {
                    "provider_id": provider,
                    "status": "success",
                    "catalog_result_count": result_count,
                    "candidate_count": len(candidates),
                    "provenance": _provenance(
                        provider,
                        plan,
                        request,
                        payload,
                        retrieved_at=retrieved_at,
                    ),
                }
            )
        # Providers are isolated deliberately: one malformed catalog or transport
        # implementation must not erase verified results from the other catalogs.
        except Exception as exc:  # noqa: BLE001
            provider_results.append(
                {
                    "provider_id": provider,
                    "status": "failed",
                    "catalog_result_count": 0,
                    "candidate_count": 0,
                    "error": {
                        "type": type(exc).__name__,
                        "message": _bounded_text(exc, 300),
                    },
                }
            )

    candidates, cross_catalog_duplicates = _deduplicate(all_candidates)
    registry_duplicates: list[dict[str, Any]] = []
    registry_tool_count = 0
    if exclude_registered:
        candidates, registry_duplicates, registry_tool_count = _registry_deduplicate(
            candidates, tooluniverse
        )
    candidates = candidates[:limit]
    successful = sum(item["status"] == "success" for item in provider_results)
    if successful == 0:
        raise VSDCatalogProviderError("All requested catalog providers failed")
    return {
        "query": query,
        "requested_providers": providers,
        "candidates": candidates,
        "candidate_count": len(candidates),
        "catalog_result_count": total_catalog_results,
        "provider_results": provider_results,
        "successful_provider_count": successful,
        "failed_provider_count": len(provider_results) - successful,
        "cross_catalog_duplicate_count": cross_catalog_duplicates,
        "registered_duplicate_count": len(registry_duplicates),
        "registered_duplicates": registry_duplicates,
        "registry_tool_count": registry_tool_count,
        "boundary": (
            "Candidates are untrusted catalog metadata. They are not approved, "
            "probed, executable, or scientific endorsements. Catalog success and "
            "ranking do not bypass contract review, verification, or approval."
        ),
        "provenance": {
            "provider_count": len(provider_results),
            "successful_provider_count": successful,
            "providers": [
                item["provenance"]
                for item in provider_results
                if item["status"] == "success"
            ],
        },
    }


__all__ = [
    "PROVIDER_ORDER",
    "VSDCatalogProviderError",
    "discover_multi_catalog_candidates",
    "normalize_apis_guru",
    "normalize_ckan",
    "normalize_data_europa",
    "normalize_datagov",
    "normalize_provider_payload",
]
