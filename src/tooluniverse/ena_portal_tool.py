# ena_portal_tool.py
"""
ENA Portal API tool for ToolUniverse.

The European Nucleotide Archive (ENA) Portal API provides programmatic
access to search studies, samples, and sequences across the world's
largest nucleotide sequence repository. Supports taxonomy-based queries,
text searches, and field selection.

API: https://www.ebi.ac.uk/ena/portal/api
No authentication required. Free for all use.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

ENA_PORTAL_BASE_URL = "https://www.ebi.ac.uk/ena/portal/api"

# Patterns that indicate the user already wrote an ENA query expression
_ENA_QUERY_OPERATORS = ("=", "(", "tax_id", "tax_tree", "AND", "OR", "NOT")


def _normalize_ena_query(query: str) -> str:
    """Convert a plain-text search string to valid ENA Portal query syntax.

    If the query already contains ENA operators/field assignments it is
    returned unchanged.  Otherwise it is wrapped as
    ``description="<query>"`` which is the most permissive full-text field.
    """
    if any(op in query for op in _ENA_QUERY_OPERATORS):
        return query
    # Escape internal double-quotes and wrap
    escaped = query.replace('"', '\\"')
    return f'description="{escaped}"'


def _parse_search_limit(arguments: Dict[str, Any]) -> tuple[int | None, str | None]:
    """Validate ENA's limit without silently imposing a local result cap.

    The Portal API uses ``limit=0`` to mean "return every matching record".
    This is especially important because the endpoint has no offset parameter.
    """
    raw_limit = arguments.get("limit", 10)
    if isinstance(raw_limit, bool):
        return None, "limit must be a non-negative integer (0 retrieves all results)"
    try:
        limit = int(raw_limit)
    except (TypeError, ValueError):
        return None, "limit must be a non-negative integer (0 retrieves all results)"
    if isinstance(raw_limit, float) and not raw_limit.is_integer():
        return None, "limit must be a non-negative integer (0 retrieves all results)"
    if limit < 0:
        return None, "limit must be a non-negative integer (0 retrieves all results)"
    return limit, None


@register_tool("ENAPortalTool")
class ENAPortalTool(BaseTool):
    """
    Tool for querying the European Nucleotide Archive (ENA) Portal API.

    Supports searching for studies, samples, and sequences with flexible
    filtering by taxonomy, text content, and custom field selection.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 60)
        self.endpoint_type = tool_config.get("fields", {}).get(
            "endpoint_type", "search_studies"
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the ENA Portal API call."""
        try:
            return self._dispatch(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"ENA Portal API request timed out after {self.timeout} seconds",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to ENA Portal API. Check network connectivity.",
            }
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "error": f"ENA Portal API HTTP error: {e.response.status_code}",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error querying ENA Portal: {str(e)}",
            }

    def _dispatch(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint based on config."""
        if self.endpoint_type == "search_studies":
            return self._search_studies(arguments)
        elif self.endpoint_type == "search_samples":
            return self._search_samples(arguments)
        elif self.endpoint_type == "search_runs":
            return self._search_runs(arguments)
        elif self.endpoint_type == "count":
            return self._count(arguments)
        else:
            return {
                "status": "error",
                "error": f"Unknown endpoint_type: {self.endpoint_type}",
            }

    def _search_metadata(
        self, *, result_type: str, query: str, returned: int, limit: int, endpoint: str
    ) -> Dict[str, Any]:
        """Report exact ENA truncation and the official full-retrieval route."""
        total_results = None
        try:
            count_response = requests.get(
                f"{ENA_PORTAL_BASE_URL}/count",
                params={"result": result_type, "query": query},
                timeout=self.timeout,
            )
            count_response.raise_for_status()
            lines = count_response.text.strip().split("\n")
            total_results = int(lines[-1])
        except (requests.RequestException, TypeError, ValueError):
            # The search result remains useful if the separate count endpoint is down.
            pass

        all_results_requested = limit == 0
        truncated = (
            total_results > returned
            if total_results is not None
            else bool(not all_results_requested and returned >= limit)
        )
        suggested_limit = None
        if truncated:
            suggested_limit = (
                total_results
                if total_results is not None and total_results <= 100_000
                else 0
            )
        warning = None
        if truncated:
            warning = (
                "ENA Portal search does not support offset pagination. Rerun with "
                f"limit={suggested_limit}; limit=0 requests every matching record."
            )

        return {
            "source": "ENA Portal API",
            "query": query,
            "returned": returned,
            "total_results": total_results,
            "limit": limit,
            "has_more": truncated,
            "truncated": truncated,
            "truncation_known": total_results is not None,
            "suggested_limit": suggested_limit,
            "all_results_requested": all_results_requested,
            "complete": not truncated,
            "warning": warning,
            # Retained for compatibility. There is no local 1000-record ceiling now;
            # ENA's documented limit=0 route makes the complete result reachable.
            "retrieval_limit_reached": False,
            "endpoint": endpoint,
        }

    def _search_studies(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search ENA studies by text query or taxonomy."""
        raw_query = arguments.get("query", "")
        if not raw_query:
            return {
                "status": "error",
                "error": "query parameter is required (e.g., 'description=\"cancer\"' or 'tax_tree(9606)')",
            }
        query = _normalize_ena_query(raw_query)

        limit, limit_error = _parse_search_limit(arguments)
        if limit_error:
            return {"status": "error", "error": limit_error}
        assert limit is not None
        fields = arguments.get(
            "fields", "study_accession,study_title,center_name,first_public,description"
        )

        params = {
            "result": "study",
            "query": query,
            "limit": limit,
            "format": "json",
            "fields": fields,
        }

        response = requests.get(
            f"{ENA_PORTAL_BASE_URL}/search",
            params=params,
            timeout=self.timeout,
        )
        response.raise_for_status()
        raw = response.json()

        if isinstance(raw, dict) and "message" in raw:
            return {
                "status": "error",
                "error": f"ENA Portal API error: {raw['message']}",
            }

        results = list(raw if limit == 0 else raw[:limit])

        return {
            "status": "success",
            "data": results,
            "metadata": self._search_metadata(
                result_type="study",
                query=query,
                returned=len(results),
                limit=limit,
                endpoint="search/study",
            ),
        }

    def _search_samples(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search ENA samples by text query or taxonomy."""
        raw_query = arguments.get("query", "")
        if not raw_query:
            return {
                "status": "error",
                "error": "query parameter is required (e.g., 'tax_tree(9606)' or 'description=\"liver\"')",
            }
        query = _normalize_ena_query(raw_query)

        limit, limit_error = _parse_search_limit(arguments)
        if limit_error:
            return {"status": "error", "error": limit_error}
        assert limit is not None
        fields = arguments.get(
            "fields",
            "sample_accession,sample_alias,description,tax_id,scientific_name,first_public",
        )

        params = {
            "result": "sample",
            "query": query,
            "limit": limit,
            "format": "json",
            "fields": fields,
        }

        response = requests.get(
            f"{ENA_PORTAL_BASE_URL}/search",
            params=params,
            timeout=self.timeout,
        )
        response.raise_for_status()
        raw = response.json()

        if isinstance(raw, dict) and "message" in raw:
            return {
                "status": "error",
                "error": f"ENA Portal API error: {raw['message']}",
            }

        results = list(raw if limit == 0 else raw[:limit])

        return {
            "status": "success",
            "data": results,
            "metadata": self._search_metadata(
                result_type="sample",
                query=query,
                returned=len(results),
                limit=limit,
                endpoint="search/sample",
            ),
        }

    def _search_runs(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search ENA sequencing runs (read_run) and return FASTQ download URLs.

        Unlike study/sample search, the run domain is what gives downloadable
        FASTQ links (fastq_ftp/submitted_ftp/sra_ftp). The query is typically a
        taxonomy expression, e.g. tax_eq(1280) (Staphylococcus aureus) or
        tax_tree(562), optionally combined with library_strategy="WGS".
        """
        raw_query = arguments.get("query", "")
        if not raw_query:
            return {
                "status": "error",
                "error": (
                    "query parameter is required (e.g., 'tax_eq(1280)' or "
                    "'tax_tree(562) AND library_strategy=\"WGS\"')"
                ),
            }
        query = _normalize_ena_query(raw_query)

        limit, limit_error = _parse_search_limit(arguments)
        if limit_error:
            return {"status": "error", "error": limit_error}
        assert limit is not None
        fields = arguments.get(
            "fields",
            "run_accession,fastq_ftp,submitted_ftp,sra_ftp,fastq_md5,fastq_bytes,"
            "library_strategy,instrument_platform,read_count,scientific_name",
        )

        params = {
            "result": "read_run",
            "query": query,
            "limit": limit,
            "format": "json",
            "fields": fields,
        }

        response = requests.get(
            f"{ENA_PORTAL_BASE_URL}/search",
            params=params,
            timeout=self.timeout,
        )
        response.raise_for_status()
        raw = response.json()

        if isinstance(raw, dict) and "message" in raw:
            return {
                "status": "error",
                "error": f"ENA Portal API error: {raw['message']}",
            }

        results = (
            list(raw if limit == 0 else raw[:limit]) if isinstance(raw, list) else []
        )

        return {
            "status": "success",
            "data": results,
            "metadata": self._search_metadata(
                result_type="read_run",
                query=query,
                returned=len(results),
                limit=limit,
                endpoint="search/read_run",
            ),
        }

    def _count(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Count records matching a query in ENA."""
        query = arguments.get("query", "")
        result_type = arguments.get("result_type", "study")
        if not query:
            return {"status": "error", "error": "query parameter is required"}

        params = {
            "result": result_type,
            "query": query,
        }

        response = requests.get(
            f"{ENA_PORTAL_BASE_URL}/count",
            params=params,
            timeout=self.timeout,
        )
        response.raise_for_status()
        text = response.text.strip()

        # Response is "count\nNUMBER" format
        lines = text.split("\n")
        count_val = int(lines[-1]) if len(lines) > 1 else int(lines[0])

        return {
            "status": "success",
            "data": {
                "count": count_val,
                "result_type": result_type,
                "query": query,
            },
            "metadata": {
                "source": "ENA Portal API",
                "endpoint": "count",
            },
        }
