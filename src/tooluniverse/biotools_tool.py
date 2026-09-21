"""bio.tools registry search with sensible matching.

bio.tools treats an unquoted multi-word filter as a loose match on any of its words,
so ``operation=Variant calling`` matched 4,165 tools (the exact EDAM operation has
1,015) and ``topic=Functional genomics`` likewise. Multi-word ``operation`` and
``topic`` values are therefore sent as exact phrases. Relevance ordering for text
queries is a separate, config-level default (``sort=score`` in the tool's fields).

bio.tools also ignores ``size`` and always answers with a page of 50 tools, five
times the documented default of 10. ``page`` and ``size`` are therefore applied
here: a window of ``size`` tools starting at ``(page - 1) * size`` is cut out of the
50-tool server pages that cover it.
"""

from typing import Any, Dict

from .base_rest_tool import BaseRESTTool
from .tool_registry import register_tool


@register_tool("BioToolsRESTTool")
class BioToolsRESTTool(BaseRESTTool):
    """BaseRESTTool that sends multi-word EDAM operation/topic terms as phrases."""

    _PHRASE_PARAMS = ("operation", "topic")

    def _build_params(self, args: Dict[str, Any]) -> Dict[str, Any]:
        params = super()._build_params(args)
        for key in self._PHRASE_PARAMS:
            value = params.get(key)
            if isinstance(value, str):
                value = value.strip()
                already_quoted = value.startswith('"') and value.endswith('"')
                if " " in value and not already_quoted:
                    params[key] = f'"{value}"'
        return params

    _SERVER_PAGE = 50

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        props = self.tool_config.get("parameter", {}).get("properties", {})
        if "size" not in props:
            return super().run(arguments)
        size = self._positive(arguments.get("size"), props["size"].get("default", 10))
        size = min(size, self._SERVER_PAGE)
        page = self._positive(arguments.get("page"), 1)
        start = (page - 1) * size
        first = start // self._SERVER_PAGE + 1
        last = (start + size - 1) // self._SERVER_PAGE + 1

        tools, result = [], None
        for server_page in range(first, last + 1):
            result = super().run({**arguments, "page": server_page, "size": size})
            data = result.get("data")
            if result.get("status") != "success" or not isinstance(data, dict):
                return result
            if "list" not in data:
                return result
            tools.extend(data["list"])
            if not data.get("next"):
                break
        skip = start - (first - 1) * self._SERVER_PAGE
        data = result["data"]
        total = data.get("count") or 0
        data["list"] = tools[skip : skip + size]
        data["previous"] = f"?page={page - 1}&size={size}" if page > 1 else None
        data["next"] = f"?page={page + 1}&size={size}" if start + size < total else None
        result["count"] = len(data["list"])
        return result

    @staticmethod
    def _positive(value, default):
        try:
            return max(1, int(value))
        except (TypeError, ValueError):
            return int(default)
