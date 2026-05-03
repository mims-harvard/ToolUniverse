from __future__ import annotations
import re
import logging
import json
from typing import Dict, Optional, List
import requests

logger = logging.getLogger("OpenAPIUtils")

OPENAPI_HINTS = [
    "openapi.json",
    "openapi.yaml",
    "openapi.yml",
    "swagger.json",
    "swagger.yaml",
    "v3/api-docs",
]


def _root_of(url: str) -> str:
    base = url.split("?", 1)[0]
    base = re.sub(r"(#.*)$", "", base)
    base = re.sub(r"/+$", "", base)
    m = re.match(r"^https?://[^/]+", base)
    return m.group(0) if m else base


def find_openapi_from_url(any_url: str) -> Optional[str]:
    root = _root_of(any_url)
    # try /openapi.json etc. at root and one level up
    tries = [f"{root}/{hint}" for hint in OPENAPI_HINTS]
    # also try without trailing /api segment if present
    if root.endswith("/api"):
        base = root.rsplit("/", 1)[0]
        tries.extend(f"{base}/{hint}" for hint in OPENAPI_HINTS)
    for t in tries:
        try:
            r = requests.get(t, timeout=8)
            if r.status_code == 200 and (
                "json" in r.headers.get("Content-Type", "") or t.endswith(".json")
            ):
                # quick JSON sanity
                try:
                    j = r.json()
                    if "openapi" in j or "swagger" in j:
                        return t
                except Exception:
                    pass
            if r.status_code == 200 and (t.endswith(".yaml") or t.endswith(".yml")):
                return t
        except requests.RequestException:
            continue
    return None


def parse_openapi(spec_url: str) -> Dict:
    r = requests.get(spec_url, timeout=15)
    r.raise_for_status()
    text = r.text
    if spec_url.endswith((".yaml", ".yml")):
        try:
            import yaml
        except Exception as e:
            raise RuntimeError(
                "YAML support requires PyYAML: pip install pyyaml"
            ) from e
        spec = yaml.safe_load(text)
    else:
        spec = r.json()

    servers = spec.get("servers") or []
    base_url = (
        servers[0].get("url") if servers and isinstance(servers[0], dict) else None
    ) or None

    paths = spec.get("paths") or {}
    endpoints: List[Dict] = []
    for path, methods in paths.items():
        if not isinstance(methods, dict):
            continue
        for method, meta in methods.items():
            if method.upper() not in (
                "GET",
                "POST",
                "PUT",
                "PATCH",
                "DELETE",
                "OPTIONS",
                "HEAD",
            ):
                continue
            endpoints.append(
                {
                    "path": path,
                    "method": method.upper(),
                    "summary": (meta or {}).get("summary"),
                }
            )
    return {"base_url": base_url, "endpoints": endpoints}
