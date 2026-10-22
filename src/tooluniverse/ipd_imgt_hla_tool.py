"""IPD-IMGT/HLA Database Tool via EMBL-EBI IPD API.

The IPD-IMGT/HLA Database provides a specialist sequence database for the
human major histocompatibility complex (MHC) -- HLA alleles -- and a registry
of cell lines with their HLA typing. This wrapper is keyless and returns JSON.

API base: https://www.ebi.ac.uk/cgi-bin/ipd/api/

The search endpoints use a filter DSL passed in the ``query`` parameter, e.g.
``startsWith(name,"A*01:01")``, ``contains(name,"A*01")``, ``eq(name,"A*01:01:01:01")``.
This tool builds that DSL for the user from a plain name/query string so callers
never have to write the filter expression themselves.
"""

import requests
from typing import Any, Dict
from urllib.parse import parse_qs, quote, urlparse
from .base_tool import BaseTool
from .tool_registry import register_tool

IPD_IMGT_HLA_BASE_URL = "https://www.ebi.ac.uk/cgi-bin/ipd/api/"

# Filter-DSL operators supported by the IPD API for string fields.
_VALID_MATCH_MODES = {"startsWith", "contains", "eq"}


@register_tool("IPDIMGTHLATool")
class IPDIMGTHLATool(BaseTool):
    """IPD-IMGT/HLA tool: search HLA alleles, fetch allele detail, search cells."""

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.base_url = IPD_IMGT_HLA_BASE_URL
        self.timeout = 30

    # ------------------------------------------------------------------
    # HTTP helpers
    # ------------------------------------------------------------------
    def _make_request(self, endpoint: str, params: Dict[str, Any]) -> Any:
        """GET an IPD endpoint and return parsed JSON, or an error envelope.

        ``params`` may contain a pre-built ``query`` value that is already a
        filter-DSL string; it is URL-encoded by requests automatically.
        Never raises -- network/parse failures are returned as error dicts.
        """
        url = self.base_url + endpoint
        try:
            response = requests.get(
                url,
                params=params,
                headers={"Accept": "application/json"},
                timeout=self.timeout,
            )
            if response.status_code == 404:
                return {"status": "error", "error": "not_found", "_http": 404}
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {
                "status": "error",
                "error": f"Failed to query IPD-IMGT/HLA API: {e}",
                "endpoint": endpoint,
            }
        except ValueError as e:
            return {
                "status": "error",
                "error": f"Failed to parse IPD-IMGT/HLA response as JSON: {e}",
                "endpoint": endpoint,
            }

    @staticmethod
    def _is_api_error(api_response: Any) -> bool:
        return isinstance(api_response, dict) and api_response.get("status") == "error"

    @staticmethod
    def _build_filter(field: str, value: str, match: str) -> str:
        """Build a filter-DSL expression, e.g. startsWith(name,"A*01:01").

        The value is wrapped in double quotes as the API requires. Any embedded
        double quotes in the user value are stripped to keep the expression valid.
        """
        if match not in _VALID_MATCH_MODES:
            match = "startsWith"
        safe_value = str(value).replace('"', "")
        return f'{match}({field},"{safe_value}")'

    @staticmethod
    def _clamp_limit(value: Any) -> int:
        """Coerce a user-supplied limit into the 1..100 range (default 10)."""
        try:
            return max(1, min(int(value), 100))
        except (TypeError, ValueError):
            return 10

    @staticmethod
    def _validate_paging(arguments: Dict[str, Any]) -> Any:
        """Validate IPD's bounded page size and opaque cursor without coercion."""
        limit = arguments.get("limit", 10)
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
            return {"status": "error", "error": "limit must be an integer from 1 to 100"}
        cursor = arguments.get("cursor")
        if cursor is not None and (not isinstance(cursor, str) or not cursor.strip()):
            return {"status": "error", "error": "cursor must be a non-empty string"}
        return limit, cursor.strip() if isinstance(cursor, str) else None

    @staticmethod
    def _cursor_from_link(link: Any, direction: str) -> Any:
        """Extract an opaque next/previous token from IPD's relative link."""
        if not isinstance(link, str) or not link:
            return None
        values = parse_qs(urlparse(link).query).get(direction, [])
        return values[0] if values else None

    @staticmethod
    def _resolve_match(arguments: Dict[str, Any], default: str) -> Any:
        """Return the requested match mode, or an error dict if it is invalid."""
        match = arguments.get("match", default)
        if match not in _VALID_MATCH_MODES:
            return {
                "status": "error",
                "error": f"Invalid match mode '{match}'. "
                f"Use one of: {', '.join(sorted(_VALID_MATCH_MODES))}",
            }
        return match

    # ------------------------------------------------------------------
    # Operations
    # ------------------------------------------------------------------
    def _search_hla_alleles(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search HLA alleles by name prefix/substring (e.g. 'A*01:01')."""
        name = str(arguments.get("name", "")).strip()
        if not name:
            return {"status": "error", "error": "name parameter is required"}

        # The IPD-IMGT/HLA `name` field is stored without the "HLA-" locus
        # prefix (e.g. "A*02:01:01:01"), but that prefixed form is exactly
        # what sibling HLA tools like VDJDB return (mhc.a: "HLA-A*02:01")
        # -- confirmed live that passing it straight through silently
        # matched zero alleles. Strip it so a natural cross-tool chain
        # (VDJDB output -> this tool's input) works.
        if name.upper().startswith("HLA-"):
            name = name[4:]

        match = self._resolve_match(arguments, "startsWith")
        if self._is_api_error(match):
            return match

        paging = self._validate_paging(arguments)
        if self._is_api_error(paging):
            return paging
        limit, cursor = paging
        query = self._build_filter("name", name, match)
        params = {"query": query, "limit": limit}
        if cursor:
            params["next"] = cursor
        api_response = self._make_request("allele", params)
        if self._is_api_error(api_response):
            return api_response

        data = api_response.get("data", []) if isinstance(api_response, dict) else []
        meta = api_response.get("meta", {}) if isinstance(api_response, dict) else {}
        alleles = [
            {"accession": d.get("accession"), "name": d.get("name")}
            for d in data
            if isinstance(d, dict)
        ]
        next_cursor = self._cursor_from_link(meta.get("next"), "next")
        previous_cursor = self._cursor_from_link(meta.get("prev"), "prev")
        total = meta.get("total")
        total_is_exact = isinstance(total, int) and not isinstance(total, bool)

        return {
            "status": "success",
            "data": {
                "alleles": alleles,
                "count": len(alleles),
                "total": total if total_is_exact else None,
                "limit": limit,
                "cursor": cursor,
                "has_more": next_cursor is not None,
                "next_cursor": next_cursor,
                "previous_cursor": previous_cursor,
                "result_set_complete": bool(
                    cursor is None and total_is_exact and len(alleles) == total
                ),
            },
            "metadata": {
                "query": query,
                "match": match,
                "source": "IPD-IMGT/HLA (EMBL-EBI)",
                "returned": len(alleles),
                "total_results": total if total_is_exact else None,
                "total_results_is_exact": total_is_exact,
                "pagination_scope": "ipd_opaque_next_cursor",
            },
        }

    def _get_hla_allele(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch the full record for an HLA allele accession (e.g. 'HLA00001')."""
        accession = str(arguments.get("accession", "")).strip()
        if not accession:
            return {"status": "error", "error": "accession parameter is required"}

        api_response = self._make_request(f"allele/{quote(accession, safe='')}", {})
        if self._is_api_error(api_response):
            if api_response.get("_http") == 404:
                return {
                    "status": "error",
                    "error": f"No HLA allele found for accession: {accession}",
                }
            return api_response

        if not isinstance(api_response, dict) or not api_response.get("accession"):
            return {
                "status": "error",
                "error": f"No HLA allele found for accession: {accession}",
            }
        if str(api_response["accession"]).upper() != accession.upper():
            return {
                "status": "error",
                "error": (
                    "IPD-IMGT/HLA allele identity mismatch: requested "
                    f"{accession}, received {api_response['accession']}"
                ),
            }

        return {
            "status": "success",
            "data": api_response,
            "metadata": {
                "accession": accession,
                "source": "IPD-IMGT/HLA (EMBL-EBI)",
            },
        }

    def _search_cells(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search IPD cell lines by a field value (default field: primary_name)."""
        query_text = str(arguments.get("query", "")).strip()
        if not query_text:
            return {"status": "error", "error": "query parameter is required"}

        field = str(arguments.get("field", "primary_name")).strip() or "primary_name"
        match = self._resolve_match(arguments, "contains")
        if self._is_api_error(match):
            return match

        paging = self._validate_paging(arguments)
        if self._is_api_error(paging):
            return paging
        limit, cursor = paging
        query = self._build_filter(field, query_text, match)
        params = {"query": query, "limit": limit}
        if cursor:
            params["next"] = cursor
        api_response = self._make_request("cell", params)
        if self._is_api_error(api_response):
            return api_response

        data = api_response.get("data", []) if isinstance(api_response, dict) else []
        meta = api_response.get("meta", {}) if isinstance(api_response, dict) else {}
        cells = [d for d in data if isinstance(d, dict)]
        next_cursor = self._cursor_from_link(meta.get("next"), "next")
        previous_cursor = self._cursor_from_link(meta.get("prev"), "prev")
        total = meta.get("total")
        total_is_exact = isinstance(total, int) and not isinstance(total, bool)

        return {
            "status": "success",
            "data": {
                "cells": cells,
                "count": len(cells),
                "total": total if total_is_exact else None,
                "limit": limit,
                "cursor": cursor,
                "has_more": next_cursor is not None,
                "next_cursor": next_cursor,
                "previous_cursor": previous_cursor,
                "result_set_complete": bool(
                    cursor is None and total_is_exact and len(cells) == total
                ),
            },
            "metadata": {
                "query": query,
                "field": field,
                "match": match,
                "source": "IPD-IMGT/HLA cells (EMBL-EBI)",
                "returned": len(cells),
                "total_results": total if total_is_exact else None,
                "total_results_is_exact": total_is_exact,
                "pagination_scope": "ipd_opaque_next_cursor",
            },
        }

    _OPERATION_MAP = {
        "search_hla_alleles": "_search_hla_alleles",
        "get_hla_allele": "_get_hla_allele",
        "search_cells": "_search_cells",
    }

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch to the operation derived from the tool config name."""
        arguments = arguments or {}
        tool_name = self.tool_config.get("name", "")

        for key, method_name in self._OPERATION_MAP.items():
            if key in tool_name:
                return getattr(self, method_name)(arguments)

        return {"status": "error", "error": f"Unknown operation for tool: {tool_name}"}
