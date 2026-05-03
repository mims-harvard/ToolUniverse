from __future__ import annotations

from typing import Any, Dict, Mapping

import requests

from .base_tool import BaseTool
from .http_utils import request_with_retry
from .tool_registry import register_tool


@register_tool("IEDBTool")
class IEDBTool(BaseTool):
    """
    Tool for interacting with the IEDB Query API (PostgREST).

    This tool is JSON-config driven: each tool config supplies
    `fields.endpoint` and (optionally) `fields.default_params` +
    `fields.shorthand_filters` to map
    friendly arguments into PostgREST filter expressions (e.g., `eq.123`,
    `ilike.*KVF*`).
    """

    QUERY_API_URL = "https://query-api.iedb.org"

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        fields = self.tool_config.get("fields") or {}
        endpoint = fields.get("endpoint")
        if not endpoint or not isinstance(endpoint, str):
            return {
                "status": "error",
                "error": "Tool misconfigured: missing fields.endpoint",
                "detail": (
                    "Expected tool_config.fields.endpoint (string) like "
                    "'/epitope_search'."
                ),
            }

        url = f"{self.QUERY_API_URL}{endpoint}"

        params: Dict[str, Any] = {}
        default_params = fields.get("default_params") or {}
        if isinstance(default_params, Mapping):
            params.update(default_params)

        # Common paging / projection knobs (PostgREST)
        if arguments.get("limit") is not None:
            params["limit"] = arguments.get("limit")
        if arguments.get("offset") is not None:
            params["offset"] = arguments.get("offset")
        if arguments.get("order"):
            params["order"] = arguments.get("order")

        select = arguments.get("select")
        if select:
            if isinstance(select, list):
                params["select"] = ",".join(str(x) for x in select if x)
            else:
                params["select"] = str(select)

        # Advanced filters: caller provides PostgREST expressions, e.g.:
        # {"linear_sequence": "ilike.*KVF*", "structure_type": "eq.Linear peptide"}
        raw_filters = arguments.get("filters") or {}
        if isinstance(raw_filters, Mapping):
            for k, v in raw_filters.items():
                if k and v is not None:
                    params[str(k)] = str(v)

        # Shorthand filters: map friendly args into PostgREST expressions.
        # Example in tool config:
        # "shorthand_filters": {"sequence_contains": {"column": "linear_sequence",
        #                                             "op": "ilike_contains"}}
        shorthand = fields.get("shorthand_filters") or {}
        if isinstance(shorthand, Mapping):
            for arg_name, spec in shorthand.items():
                if not arg_name:
                    continue
                val = arguments.get(arg_name)
                if val is None:
                    continue
                if not isinstance(spec, Mapping):
                    continue
                column = spec.get("column") or arg_name
                op = spec.get("op") or "eq"
                if op == "eq":
                    params[str(column)] = f"eq.{val}"
                elif op == "ilike_contains":
                    params[str(column)] = f"ilike.*{val}*"
                elif op == "raw":
                    params[str(column)] = str(val)

        timeout_s = fields.get("timeout", 30)
        try:
            resp = request_with_retry(
                requests,
                "GET",
                url,
                params=params,
                timeout=timeout_s,
            )

            if not (200 <= resp.status_code < 300):
                detail: Any
                try:
                    detail = resp.json()
                except Exception:
                    detail = resp.text[:2000]
                return {
                    "status": "error",
                    "url": resp.url,
                    "status_code": resp.status_code,
                    "error": "HTTP request failed",
                    "detail": detail,
                }

            try:
                data: Any = resp.json()
            except Exception:
                data = resp.text

            out: Dict[str, Any] = {
                "status": "success",
                "url": resp.url,
                "data": data,
            }
            if isinstance(data, list):
                out["count"] = len(data)
            return out

        except Exception as e:
            return {"status": "error", "url": url, "error": str(e)}
