from __future__ import annotations

import time
from copy import deepcopy
from typing import Any, Dict

import requests

# ------------------------------------------------------------------------------
# Host-specific overrides and requirements
# ------------------------------------------------------------------------------

HOST_OVERRIDES: Dict[str, Dict[str, Any]] = {
    # Ensembl requires a concrete resource; expose the JSON heartbeat by default.
    "rest.ensembl.org": {
        "endpoint": "https://rest.ensembl.org/info/ping",
        "default_headers": {"Accept": "application/json"},
        "notes": "Ensembl REST base requires explicit resource. '/info/ping' provides a JSON heartbeat.",
    },
    "api.fda.gov": {
        "default_params": {"limit": 5},
        "default_headers": {"Accept": "application/json"},
    },
    "data.cdc.gov": {
        "default_params": {"$limit": 5},
        "default_headers": {"Accept": "application/json"},
    },
}

HOST_REQUIREMENTS: Dict[str, Dict[str, Any]] = {
    "api.nal.usda.gov": {
        "requires_api_key": True,
        "notes": "USDA FoodData Central requires an api_key query parameter.",
    },
    "www.ncdc.noaa.gov": {
        "requires_api_key": True,
        "notes": "NOAA CDO API requires a token header. See https://www.ncdc.noaa.gov/cdo-web/webservices/v2",
        "default_headers": {"token": ""},
    },
    "clinicaltrialsapi.cancer.gov": {
        "requires_api_key": True,
        "notes": "ClinicalTrials API requires authenticated access for JSON responses.",
    },
    "findtreatment.samhsa.gov": {
        "requires_manual_params": True,
        "notes": "SAMHSA locator needs query parameters (e.g., state, lat/long) to return JSON.",
    },
}


# ------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------

def _derive_endpoint(candidate: Dict[str, Any]) -> str:
    endpoint = candidate.get("endpoint") or candidate.get("url")
    if endpoint:
        return str(endpoint)

    base_url = candidate.get("base_url")
    routes = candidate.get("endpoints") or []
    if base_url and isinstance(routes, list) and routes:
        first = routes[0]
        path = str(first.get("path") or "/")
        if not base_url.endswith("/") and not path.startswith("/"):
            return f"{base_url}/{path}"
        if base_url.endswith("/") and path.startswith("/"):
            return f"{base_url.rstrip('/')}{path}"
        return f"{base_url}{path}"

    if base_url:
        return str(base_url)

    raise ValueError("candidate.endpoint or candidate.url is required")


def _apply_overrides(candidate: Dict[str, Any], cfg: Dict[str, Any]) -> None:
    host = (candidate.get("host") or "").lower()

    overrides = HOST_OVERRIDES.get(host)
    if overrides:
        fields = cfg.setdefault("fields", {})
        if overrides.get("endpoint"):
            cfg["endpoint"] = overrides["endpoint"]
            fields["base_url"] = overrides["endpoint"]
        if overrides.get("default_params"):
            cfg.setdefault("default_params", {}).update(overrides["default_params"])
            fields.setdefault("default_params", {}).update(overrides["default_params"])
        if overrides.get("default_headers"):
            cfg.setdefault("default_headers", {}).update(overrides["default_headers"])
            fields.setdefault("headers", {}).update(overrides["default_headers"])
        if overrides.get("notes"):
            cfg.setdefault("metadata", {}).setdefault("notes", []).append(overrides["notes"])

    requirements = HOST_REQUIREMENTS.get(host)
    if requirements:
        meta = cfg.setdefault("metadata", {})
        meta.setdefault("requirements", {}).update(
            {
                key: value
                for key, value in requirements.items()
                if key not in {"default_headers"}
            }
        )
        if requirements.get("default_headers"):
            cfg.setdefault("default_headers", {}).update(requirements["default_headers"])
            cfg.setdefault("fields", {}).setdefault("headers", {}).update(requirements["default_headers"])


# ------------------------------------------------------------------------------
# Public helpers used by VSD tools
# ------------------------------------------------------------------------------

def build_config(
    candidate: Dict[str, Any],
    tool_type: str = "dynamic_rest",
    default_params: Dict[str, Any] | None = None,
    default_headers: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """
    Produce a DynamicREST-style configuration dictionary from a harvest candidate.
    """
    endpoint = _derive_endpoint(candidate)
    method = str(candidate.get("method") or candidate.get("http_method") or "GET").upper()
    merged_params = deepcopy(candidate.get("default_params") or candidate.get("params") or {})
    merged_headers = deepcopy(candidate.get("default_headers") or candidate.get("headers") or {})

    # Allow overrides provided via arguments
    if default_params:
        merged_params.update(default_params)
    if default_headers:
        merged_headers.update(default_headers)

    # Determine implementation class
    declared_type = str(candidate.get("tool_type") or tool_type or "").lower()
    impl_type = "GenericRESTTool"
    if declared_type in {"graphql", "genericgraphqltool", "graph_ql"} or endpoint.endswith(".graphql"):
        impl_type = "GenericGraphQLTool"

    # Provide a permissive parameter schema with defaults from known params
    parameter_schema: Dict[str, Any] = deepcopy(candidate.get("parameter_schema") or candidate.get("parameter") or {})
    if not parameter_schema:
        properties = {
            key: {"description": f"Override default query parameter '{key}'", "default": value}
            for key, value in merged_params.items()
        }
        parameter_schema = {
            "type": "object",
            "properties": properties,
            "additionalProperties": True,
        }

    fields: Dict[str, Any] = {
        "base_url": endpoint,
        "method": method,
        "default_params": merged_params,
        "headers": merged_headers,
    }

    cfg: Dict[str, Any] = {
        "type": impl_type,
        "description": candidate.get("description") or "",
        "fields": fields,
        "parameter": parameter_schema,
        "metadata": {
            "source": candidate.get("source"),
            "trust": candidate.get("trust"),
            "health": candidate.get("health"),
            "doc_url": candidate.get("doc_url"),
            "description": candidate.get("description"),
            "host": candidate.get("host"),
        },
        "vsd": candidate,
        # Backwards compatibility fields expected by older utilities
        "tool_type": candidate.get("tool_type") or tool_type or "dynamic_rest",
        "endpoint": endpoint,
        "method": method,
        "default_params": merged_params,
        "default_headers": merged_headers,
        "auth": candidate.get("auth") or {"type": "none"},
    }

    response_key = candidate.get("response_key")
    if response_key:
        cfg["response_key"] = response_key

    _apply_overrides(candidate, cfg)

    return cfg


def probe_config(cfg: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a lightweight HTTP request to validate the generated configuration.
    Returns diagnostic information including HTTP status and a JSON snippet if available.
    """
    fields = cfg.get("fields") or {}
    url = cfg.get("endpoint") or fields.get("base_url")
    method = (fields.get("method") or cfg.get("method") or "GET").upper()
    params = deepcopy(fields.get("default_params") or cfg.get("default_params") or {})
    headers = deepcopy(fields.get("headers") or cfg.get("default_headers") or {})
    headers.setdefault("Accept", "application/json")

    try:
        if method == "GET":
            resp = requests.get(url, params=params, headers=headers, timeout=20)
        else:
            resp = requests.request(method, url, json=params, headers=headers, timeout=20)
    except Exception as exc:
        return {"ok": False, "error": str(exc), "stage": "request"}

    content_type = resp.headers.get("Content-Type", "")
    preview = resp.text[:400] if resp.text else ""
    sample = None
    has_json = False

    if "json" in content_type.lower():
        try:
            payload = resp.json()
            has_json = True
            if isinstance(payload, list):
                sample = payload[:1]
            elif isinstance(payload, dict):
                sample = {k: payload[k] for i, k in enumerate(payload) if i < 5}
            else:
                sample = payload
        except Exception:
            has_json = False

    status_ok = resp.status_code < 400

    return {
        "ok": bool(status_ok and (has_json or "json" in content_type.lower())),
        "status": resp.status_code,
        "content_type": content_type,
        "has_json": has_json,
        "sample": sample,
        "preview": preview,
    }


def stamp_metadata(cfg: Dict[str, Any], probe: Dict[str, Any]) -> None:
    """
    Update metadata timestamps and probe results on a configuration dictionary.
    """
    metadata = cfg.setdefault("metadata", {})
    metadata["registered_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ")
    metadata["last_test"] = probe
