"""
COD Tool - Crystallography Open Database

Extends BaseRESTTool with strict aliases and recoverable client-side offset
pagination. The COD JSON API ignores limit, results, offset, and page, so the
complete upstream result is fetched and then paged without hiding records.

API: https://www.crystallography.net/cod/result?format=json
No authentication required. CC0 license.
"""

import re
from typing import Dict, Any
from .base_rest_tool import BaseRESTTool
from .tool_registry import register_tool


@register_tool("CODTool")
class CODTool(BaseRESTTool):
    """
    Tool for querying the Crystallography Open Database (COD).

    Adds user-friendly aliases and client-side pagination:
    - query -> text
    - spacegroup -> sg
    - cod_id -> id
    - max_results / results -> limit
    """

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        args = dict(arguments)

        tool_name = self.tool_config.get("name", "")
        is_get = tool_name == "COD_get_structure"
        allowed = (
            {"cod_id", "id"}
            if is_get
            else {
                "query",
                "text",
                "formula",
                "el1",
                "el2",
                "el3",
                "nel",
                "commonname",
                "mineral",
                "spacegroup",
                "sg",
                "sgNumber",
                "max_results",
                "results",
                "limit",
                "offset",
            }
        )
        unknown = sorted(set(args) - allowed)
        if unknown:
            return {
                "status": "error",
                "error": f"Unknown parameter(s): {', '.join(unknown)}",
            }

        # Resolve aliases before passing to BaseRESTTool
        alias_map = (
            {"cod_id": "id"}
            if is_get
            else {
                "query": "text",
                "spacegroup": "sg",
                "max_results": "limit",
                "results": "limit",
            }
        )
        for alias, canonical in alias_map.items():
            if alias not in args:
                continue
            alias_value = args.pop(alias)
            if canonical in args and args[canonical] != alias_value:
                return {
                    "status": "error",
                    "error": f"Conflicting values for {alias} and {canonical}",
                }
            args[canonical] = alias_value

        if is_get:
            cod_id = args.get("id")
            if not isinstance(cod_id, str) or not re.fullmatch(r"\d{7}", cod_id):
                return {
                    "status": "error",
                    "error": "id/cod_id must be a seven-digit COD entry ID",
                }
            result = super().run(args)
            if result.get("status") != "success":
                return result
            data = result.get("data")
            if not isinstance(data, list):
                return {"status": "error", "error": "COD returned malformed JSON data"}
            if not data:
                return {"status": "error", "error": f"COD entry not found: {cod_id}"}
            if len(data) > 1 or str(data[0].get("file")) != cod_id:
                return {
                    "status": "error",
                    "error": "COD response identity conflicts with the requested entry ID",
                }
            result["count"] = len(data)
            result["metadata"] = {
                "source": "Crystallography Open Database",
                "requested_cod_id": cod_id,
                "identity_verified": True,
                "source_record_complete": True,
            }
            return result

        limit = args.pop("limit", 100)
        offset = args.pop("offset", 0)
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 500:
            return {"status": "error", "error": "limit must be an integer from 1 to 500"}
        if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
            return {"status": "error", "error": "offset must be a non-negative integer"}

        filters = {key: value for key, value in args.items() if value not in (None, "")}
        if not filters:
            return {
                "status": "error",
                "error": "At least one crystallographic search filter is required",
            }

        result = super().run(args)

        if result.get("status") != "success":
            return result
        data = result.get("data")
        if not isinstance(data, list):
            return {"status": "error", "error": "COD returned malformed JSON data"}

        total = len(data)
        page = data[offset : offset + limit]
        next_offset = offset + len(page)
        has_more = next_offset < total
        result["data"] = page
        result["count"] = len(page)
        result["metadata"] = {
            "source": "Crystallography Open Database",
            "returned": len(page),
            "total_results": total,
            "total_results_is_exact": True,
            "limit": limit,
            "offset": offset,
            "has_more": has_more,
            "next_offset": next_offset if has_more else None,
            "result_set_complete": offset == 0 and len(page) == total,
            "filters_applied": filters,
            "upstream_pagination_supported": False,
            "upstream_full_result_fetched": True,
            "warning": (
                "Additional COD records exist; call again with next_offset."
                if has_more
                else None
            ),
        }

        return result
