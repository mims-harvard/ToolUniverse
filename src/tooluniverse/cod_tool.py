"""
COD Tool - Crystallography Open Database

Extends BaseRESTTool with parameter aliases and client-side result limiting
for the COD REST API. The COD JSON API does not support server-side result
limiting, so truncation is applied after fetching.

API: https://www.crystallography.net/cod/result?format=json
No authentication required. CC0 license.
"""

from typing import Dict, Any
from .base_rest_tool import BaseRESTTool
from .tool_registry import register_tool


@register_tool("CODTool")
class CODTool(BaseRESTTool):
    """
    Tool for querying the Crystallography Open Database (COD).

    Adds user-friendly aliases and client-side result limiting:
    - query -> text
    - spacegroup -> sg
    - cod_id -> id
    - max_results / results -> client-side truncation
    """

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        args = dict(arguments)

        # Resolve aliases before passing to BaseRESTTool
        alias_map = {
            "query": "text",
            "spacegroup": "sg",
            "cod_id": "id",
            "max_results": "results",
        }
        for alias, canonical in alias_map.items():
            if alias in args and canonical not in args:
                args[canonical] = args.pop(alias)
            elif alias in args:
                args.pop(alias)

        # Extract limit before calling parent (COD JSON API ignores it)
        limit = args.pop("results", None)

        result = super().run(args)

        # Apply client-side result limiting
        if limit is not None and result.get("status") == "success":
            data = result.get("data")
            if isinstance(data, list) and len(data) > int(limit):
                result["total_before_limit"] = len(data)
                result["data"] = data[: int(limit)]
                result["count"] = int(limit)

        return result
