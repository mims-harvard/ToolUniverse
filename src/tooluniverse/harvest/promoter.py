from __future__ import annotations
import os
import json
import tempfile
import shutil
from typing import Dict, Any, List

# Where we persist generated tool configs so DynamicREST (or your server boot)
# can load them. Mirrors your earlier logs (~/.tooluniverse/vsd/generated_tools.json).
VSD_DIR = os.path.join(os.path.expanduser("~"), ".tooluniverse", "vsd")
VSD_PATH = os.path.join(VSD_DIR, "generated_tools.json")


def _ensure_dir():
    os.makedirs(VSD_DIR, exist_ok=True)


def _read_json(path: str) -> Any:
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        return {}


def _atomic_write(path: str, data: Any):
    tmp_fd, tmp_path = tempfile.mkstemp(prefix="vsd_", suffix=".json")
    os.close(tmp_fd)
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    shutil.move(tmp_path, path)


def _slug(host: str) -> str:
    return (host or "unknown").lower().replace(".", "_").replace("-", "_")


def build_candidate_tool_json(c: Dict[str, Any]) -> Dict[str, Any]:
    # Minimal, UI-friendly payload for listing/debug
    return {
        "name": c.get("name"),
        "host": c.get("host"),
        "base_url": c.get("base_url"),
        "doc_url": c.get("doc_url"),
        "openapi_url": c.get("openapi_url"),
        "endpoints": c.get("endpoints"),
        "health": c.get("health"),
        "cors": c.get("cors"),
        "trust": c.get("trust"),
        "source": c.get("source"),
        "_rank_score": c.get("_rank_score"),
    }


def _dynamicrest_tool_config(c: Dict[str, Any]) -> Dict[str, Any]:
    """Produce a DynamicREST-style tool definition.
    Two modes:
      - OpenAPI mode (preferred): reference spec URL.
      - Manual mode: infer a few GET endpoints from verification results.
    """
    name = f"vsd_auto_{_slug(c.get('host') or '')}"
    base_url = c.get("base_url")
    openapi_url = c.get("openapi_url")
    endpoints = c.get("endpoints") or []

    cfg: Dict[str, Any] = {
        "name": name,
        "type": "DynamicREST",
        "base_url": base_url,
        "auth": c.get("auth") or {"type": "none"},
        "metadata": {
            "source": c.get("source"),
            "trust": c.get("trust"),
            "health": c.get("health"),
            "doc_url": c.get("doc_url"),
        },
    }
    if openapi_url:
        cfg["openapi"] = {"spec_url": openapi_url}
    elif endpoints:
        # Trim to a handful of GET endpoints
        routes: List[Dict[str, Any]] = []
        for ep in endpoints[:5]:
            routes.append(
                {
                    "method": ep.get("method") or "GET",
                    "path": ep.get("path") or "/",
                    "name": (ep.get("summary") or ep.get("path") or "endpoint")
                    .strip("/")
                    .replace("/", "_")[:64]
                    or "endpoint",
                }
            )
        cfg["routes"] = routes
    else:
        # Last resort: allow a generic GET on '/'
        cfg["routes"] = [{"method": "GET", "path": "/"}]
    return cfg


def promote_to_dynamicrest(c: Dict[str, Any]) -> str:
    """Append/Update the generated tool config file so your server can load it.
    Returns the registered tool name.
    """
    _ensure_dir()
    current = _read_json(VSD_PATH)
    if not isinstance(current, dict):
        current = {}

    cfg = _dynamicrest_tool_config(c)
    name = cfg.get("name") or "vsd_auto_unknown"
    current[name] = cfg
    _atomic_write(VSD_PATH, current)
    return name
