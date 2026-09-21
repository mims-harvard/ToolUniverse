"""bio.tools registry search with sensible matching.

bio.tools treats an unquoted multi-word filter as a loose match on any of its words,
so ``operation=Variant calling`` matched 4,165 tools (the exact EDAM operation has
1,015) and ``topic=Functional genomics`` likewise. Multi-word ``operation`` and
``topic`` values are therefore sent as exact phrases. Relevance ordering for text
queries is a separate, config-level default (``sort=score`` in the tool's fields).
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
