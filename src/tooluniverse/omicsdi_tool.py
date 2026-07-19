# omicsdi_tool.py
"""OmicsDI dataset search tool for ToolUniverse.

OmicsDI's search endpoint silently ignores omics_type/organism/tissue when
sent as separate query params -- confirmed live (e.g. requesting
omics_type=Proteomics still returns Transcriptomics-dominated results).
The upstream API only respects these as Lucene clauses folded into the
`query` string itself (e.g. `query AND omics_type:"Proteomics"`), so this
tool builds that composite query before delegating to BaseRESTTool.
"""

from typing import Any, Dict

from .base_rest_tool import BaseRESTTool
from .tool_registry import register_tool

_FILTER_FIELDS = ("omics_type", "organism", "tissue")


@register_tool("OmicsDITool")
class OmicsDITool(BaseRESTTool):
    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        arguments = dict(arguments)
        query = arguments.get("query", "")
        clauses = [query] if query else []
        for field in _FILTER_FIELDS:
            value = arguments.pop(field, None)
            if value:
                clauses.append(f'{field}:"{value}"')
        if clauses:
            arguments["query"] = " AND ".join(clauses)
        return super().run(arguments)
