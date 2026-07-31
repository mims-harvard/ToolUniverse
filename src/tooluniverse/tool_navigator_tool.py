from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

from .execute_function import ToolUniverse
from .tool_registry import register_tool
from .vsd_registry import load_catalog


def _tokenize(text: str) -> List[str]:
    return [t for t in (text or "").lower().split() if t]


def _score(query_tokens: List[str], name: str, description: str) -> float:
    haystack = f"{name} {description}".lower()
    score = 0.0
    for token in query_tokens:
        if token in haystack:
            score += 2.0
    score += sum(1.0 for token in query_tokens if any(word.startswith(token) for word in haystack.split()))
    return score


def _format_tool(tool: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "name": tool.get("name"),
        "type": tool.get("type"),
        "description": tool.get("description"),
        "tool_type": tool.get("tool_type"),
        "category": tool.get("category"),
        "source": tool.get("source"),
    }


@register_tool("ToolNavigatorTool")
class ToolNavigatorTool:
    """
    Search ToolUniverse's catalog (built-in + VSD) to help agents discover relevant tools.
    """

    name = "ToolNavigatorTool"
    description = "Search ToolUniverse/Navigated catalog for tools matching a query."
    input_schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "limit": {"type": "integer", "default": 10, "minimum": 1, "maximum": 50},
            "categories": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional list of categories to include.",
            },
            "include_vsd": {
                "type": "boolean",
                "default": True,
                "description": "Include dynamically registered VSD tools in the search.",
            },
        },
        "required": ["query"],
        "additionalProperties": False,
    }

    def __init__(self) -> None:
        self._tooluniverse = ToolUniverse()

    def _load_base_tools(self) -> List[Dict[str, Any]]:
        if not getattr(self._tooluniverse, "all_tools", None):
            self._tooluniverse.load_tools()
        return list(getattr(self._tooluniverse, "all_tools", []))

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        query = (arguments.get("query") or "").strip()
        if not query:
            return {"ok": False, "error": "query is required"}

        limit = int(arguments.get("limit") or 10)
        include_vsd = bool(arguments.get("include_vsd", True))
        categories = arguments.get("categories")
        if categories and not isinstance(categories, list):
            categories = [categories]
        categories = [c.lower() for c in categories or []]

        tools = self._load_base_tools()
        if include_vsd:
            for cfg in load_catalog().values():
                tools.append(
                    {
                        "name": cfg.get("name"),
                        "type": "DynamicREST",
                        "description": (cfg.get("metadata") or {}).get("description"),
                        "tool_type": "dynamic_rest",
                        "category": "vsd",
                        "source": (cfg.get("metadata") or {}).get("source"),
                    }
                )

        query_tokens = _tokenize(query)
        scored: List[tuple[float, Dict[str, Any]]] = []
        for tool in tools:
            if categories and (tool.get("category") or "").lower() not in categories:
                continue
            score = _score(query_tokens, tool.get("name", ""), tool.get("description", ""))
            if score > 0:
                scored.append((score, tool))

        scored.sort(key=lambda item: item[0], reverse=True)
        best = [_format_tool(tool) | {"score": round(score, 3)} for score, tool in scored[:limit]]

        return {"ok": True, "query": query, "results": best, "total": len(scored)}
