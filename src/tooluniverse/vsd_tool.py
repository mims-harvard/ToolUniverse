from __future__ import annotations

from typing import Any, Dict, Optional, List
from urllib.parse import urlparse

from .tool_registry import register_tool
from .vsd_registry import load_catalog, save_catalog, upsert_tool
from .dynamic_rest_runner import refresh_generated_registry, remove_generated_tool
from .vsd_utils import build_config, probe_config, stamp_metadata
from .harvest.static_catalog import harvest as harvest_static

GENERIC_HARVEST_SCHEMA = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "Free-text search term passed to the harvest catalog.",
        },
        "limit": {
            "type": "integer",
            "minimum": 1,
            "maximum": 50,
            "default": 5,
            "description": "Maximum number of candidates to return.",
        },
        "urls": {
            "type": "array",
            "items": {"type": "string", "format": "uri"},
            "description": "Optional explicit URLs to wrap as manual candidates (skips catalog search).",
        },
    },
    "additionalProperties": False,
}

GENERIC_HARVEST_CONFIG = {
    "name": "GenericHarvestTool",
    "description": "Search the harvest catalog (or wrap manual URLs) to produce candidate API endpoints.",
    "type": "GenericHarvestTool",
    "category": "special_tools",
    "parameter": GENERIC_HARVEST_SCHEMA,
}

VERIFIED_SOURCE_REGISTER_SCHEMA = {
    "type": "object",
    "properties": {
        "tool_name": {"type": "string"},
        "tool_type": {"type": "string", "default": "dynamic_rest"},
        "candidate": {"type": "object"},
        "default_params": {"type": "object"},
        "default_headers": {"type": "object"},
        "force": {"type": "boolean", "default": False},
    },
    "required": ["tool_name", "candidate"],
}

VERIFIED_SOURCE_REGISTER_CONFIG = {
    "name": "VerifiedSourceRegisterTool",
    "description": "Register a DynamicREST tool into the verified-source catalog after probing it.",
    "type": "VerifiedSourceRegisterTool",
    "category": "special_tools",
    "parameter": VERIFIED_SOURCE_REGISTER_SCHEMA,
}

VERIFIED_SOURCE_DISCOVERY_CONFIG = {
    "name": "VerifiedSourceDiscoveryTool",
    "description": "List the tools currently stored in the verified-source catalog.",
    "type": "VerifiedSourceDiscoveryTool",
    "category": "special_tools",
    "parameter": {
        "type": "object",
        "properties": {},
        "additionalProperties": False,
    },
}

VERIFIED_SOURCE_REMOVE_SCHEMA = {
    "type": "object",
    "properties": {
        "tool_name": {"type": "string"},
    },
    "required": ["tool_name"],
}

VERIFIED_SOURCE_REMOVE_CONFIG = {
    "name": "VerifiedSourceRemoveTool",
    "description": "Remove a generated tool from the verified-source catalog.",
    "type": "VerifiedSourceRemoveTool",
    "category": "special_tools",
    "parameter": VERIFIED_SOURCE_REMOVE_SCHEMA,
}


@register_tool("GenericHarvestTool", config=GENERIC_HARVEST_CONFIG)
class GenericHarvestTool:
    name = "GenericHarvestTool"
    description = "Harvest candidate API endpoints from the static catalog or wrap manual URLs."
    input_schema = GENERIC_HARVEST_SCHEMA

    def __init__(self, tool_config: Optional[Dict[str, Any]] = None) -> None:
        self.tool_config = tool_config or {}

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        query = (arguments.get("query") or "").strip()
        limit_value = arguments.get("limit", 5)
        try:
            limit = int(limit_value)
        except (TypeError, ValueError):
            limit = 5
        limit = max(1, min(limit, 50))
        urls = arguments.get("urls") or []

        candidates: List[Dict[str, Any]] = []

        if urls:
            for idx, raw_url in enumerate(urls):
                if not raw_url:
                    continue
                parsed = urlparse(str(raw_url))
                host = parsed.netloc.lower()
                base_url = f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme and parsed.netloc else raw_url
                name = host or f"manual_candidate_{idx + 1}"
                candidates.append(
                    {
                        "name": name,
                        "endpoint": raw_url,
                        "url": raw_url,
                        "base_url": base_url,
                        "host": host,
                        "source": "manual_urls",
                        "description": arguments.get("description") or "",
                        "trust": 0.5,
                        "health": {"ok": None, "status": None, "checked": "manual"},
                    }
                )
        else:
            extra_args = {k: v for k, v in arguments.items() if k not in {"query", "limit", "urls"}}
            candidates = harvest_static(query=query, limit=limit, **extra_args)

        return {
            "ok": True,
            "query": query,
            "count": len(candidates),
            "candidates": candidates,
        }


@register_tool("VerifiedSourceRegisterTool", config=VERIFIED_SOURCE_REGISTER_CONFIG)
class VerifiedSourceRegisterTool:
    name = "VerifiedSourceRegisterTool"
    description = "Register a DynamicREST tool in the verified-source directory"
    input_schema = VERIFIED_SOURCE_REGISTER_SCHEMA

    def __init__(self, tool_config: Optional[Dict[str, Any]] = None) -> None:
        self.tool_config = tool_config or {}

    def __call__(
        self,
        tool_name: str,
        candidate: Dict[str, Any],
        tool_type: str = "dynamic_rest",
        default_params: Dict[str, Any] | None = None,
        default_headers: Dict[str, Any] | None = None,
        force: bool = False,
    ) -> Dict[str, Any]:
        if not tool_name:
            raise ValueError("tool_name is required")

        cfg = build_config(
            candidate or {},
            tool_type=tool_type,
            default_params=default_params,
            default_headers=default_headers,
        )

        probe = probe_config(cfg)
        stamp_metadata(cfg, probe)

        if not probe.get("ok") and not force:
            return {
                "registered": False,
                "name": tool_name,
                "error": "Endpoint validation failed",
                "test": probe,
                "suggestion": "Provide default_params/default_headers or retry with force=True after ensuring credentials.",
            }

        cfg = upsert_tool(tool_name, cfg)
        refresh_generated_registry()

        return {"registered": True, "name": tool_name, "config": cfg}

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        return self.__call__(
            tool_name=arguments.get("tool_name"),
            candidate=arguments.get("candidate", {}),
            tool_type=arguments.get("tool_type", "dynamic_rest"),
            default_params=arguments.get("default_params"),
            default_headers=arguments.get("default_headers"),
            force=bool(arguments.get("force")),
        )


@register_tool("VerifiedSourceDiscoveryTool", config=VERIFIED_SOURCE_DISCOVERY_CONFIG)
class VerifiedSourceDiscoveryTool:
    name = "VerifiedSourceDiscoveryTool"
    description = "Return the Verified-Source catalog."

    def __init__(self, tool_config: Optional[Dict[str, Any]] = None) -> None:
        self.tool_config = tool_config or {}

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        catalog = load_catalog()
        return {"ok": True, "tools": list(catalog.values())}


@register_tool("VerifiedSourceRemoveTool", config=VERIFIED_SOURCE_REMOVE_CONFIG)
class VerifiedSourceRemoveTool:
    name = "VerifiedSourceRemoveTool"
    description = "Remove a generated tool from the Verified-Source catalog."
    input_schema = VERIFIED_SOURCE_REMOVE_SCHEMA

    def __init__(self, tool_config: Optional[Dict[str, Any]] = None) -> None:
        self.tool_config = tool_config or {}

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        tool_name = arguments.get("tool_name")
        if not tool_name:
            return {"removed": False, "error": "tool_name is required"}
        catalog = load_catalog()
        if tool_name not in catalog:
            return {"removed": False, "error": f"Unknown tool '{tool_name}'"}
        del catalog[tool_name]
        save_catalog(catalog)
        remove_generated_tool(tool_name)
        return {"removed": True, "name": tool_name}


def register(server):
    register_tool(VerifiedSourceRegisterTool.name, VerifiedSourceRegisterTool)
    register_tool(VerifiedSourceDiscoveryTool.name, VerifiedSourceDiscoveryTool)
    register_tool(VerifiedSourceRemoveTool.name, VerifiedSourceRemoveTool)

    server.add_tool(VerifiedSourceRegisterTool.name, VerifiedSourceRegisterTool())
    server.add_tool(VerifiedSourceDiscoveryTool.name, VerifiedSourceDiscoveryTool())
    server.add_tool(VerifiedSourceRemoveTool.name, VerifiedSourceRemoveTool())
    refresh_generated_registry()
