"""ToolUniverse page URL tool — returns the public web page URL for any tool by name."""

import json
import os
from typing import Any, Dict, Optional

from .base_tool import BaseTool
from .tool_registry import register_tool

_INDEX_PATH = os.path.join(os.path.dirname(__file__), "data", "tool_page_index.json")
_SITE_BASE = "https://aiscientist.tools"

_index_cache: Optional[Dict[str, str]] = None


def _load_index() -> Dict[str, str]:
    global _index_cache
    if _index_cache is None:
        with open(_INDEX_PATH) as f:
            _index_cache = json.load(f)
    return _index_cache


@register_tool("ToolUniversePageTool")
class ToolUniversePageTool(BaseTool):
    """Return the public ToolUniverse web page URL for a tool by its name."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        tool_name = arguments.get("tool_name", "")
        if not tool_name:
            return {"status": "error", "error": "Parameter 'tool_name' is required."}

        try:
            index = _load_index()
        except FileNotFoundError:
            return {
                "status": "error",
                "error": "tool_page_index.json not found — reinstall ToolUniverse.",
            }
        except Exception as e:
            return {"status": "error", "error": f"Failed to load tool index: {e}"}

        uid = index.get(tool_name)
        if uid is None:
            return {
                "status": "error",
                "error": f"Tool '{tool_name}' not found in ToolUniverse registry.",
                "hint": "Use Tool_RAG or Tool_Finder to discover available tool names.",
            }

        url = f"{_SITE_BASE}/tool/{uid}"
        return {
            "status": "success",
            "data": {
                "tool_name": tool_name,
                "url": url,
            },
        }
