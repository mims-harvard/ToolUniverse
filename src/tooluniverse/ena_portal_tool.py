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
        self.timeout = tool_config.get("timeout", 30)
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
        elif self.endpoint_type == "count":
            return self._count(arguments)
        else:
            return {
                "status": "error",
                "error": f"Unknown endpoint_type: {self.endpoint_type}",
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

        limit = min(arguments.get("limit", 10), 100)
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

        results = []
        for item in raw[:limit]:
            results.append(item)

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "source": "ENA Portal API",
                "query": query,
                "returned": len(results),
                "endpoint": "search/study",
            },
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

        limit = min(arguments.get("limit", 10), 100)
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

        results = []
        for item in raw[:limit]:
            results.append(item)

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "source": "ENA Portal API",
                "query": query,
                "returned": len(results),
                "endpoint": "search/sample",
            },
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
