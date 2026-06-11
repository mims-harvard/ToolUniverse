import requests
from typing import Dict, Any, Optional
from urllib.parse import urlencode
from .base_tool import BaseTool
from .tool_registry import register_tool

CDC_DATA_BASE_URL = "https://data.cdc.gov"


@register_tool("CDCRESTTool")
class CDCRESTTool(BaseTool):
    """CDC Data.CDC.gov REST API tool (Socrata-based open data portal)."""

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.endpoint_template = tool_config["fields"]["endpoint"]

    def _build_url(self, arguments: Dict[str, Any]) -> str:
        """Build the full CDC Data API URL with path parameters and query string."""
        endpoint = self.endpoint_template

        # Replace path parameters
        if "{dataset_id}" in endpoint:
            if "dataset_id" not in arguments:
                raise ValueError("dataset_id is required")
            endpoint = endpoint.replace("{dataset_id}", arguments["dataset_id"])

        url = f"{CDC_DATA_BASE_URL}{endpoint}"

        # Build query parameters (Socrata API format)
        query_params = {}

        # Handle search query
        if "search_query" in arguments and arguments["search_query"]:
            query_params["$q"] = arguments["search_query"]

        # Handle category
        if "category" in arguments and arguments["category"]:
            query_params["category"] = arguments["category"]

        # A full SoQL query string ($query) must carry its own LIMIT/OFFSET/etc;
        # Socrata rejects mixing $query with the discrete $limit/$where/... params.
        soql_query = arguments.get("soql_query")

        # Handle limit ($limit in Socrata)
        limit = arguments.get("limit", 50)
        if limit and not soql_query:
            query_params["$limit"] = (
                min(limit, 1000) if "views.json" in endpoint else min(limit, 50000)
            )

        # Handle offset ($offset in Socrata)
        offset = arguments.get("offset", 0)
        if offset and not soql_query:
            query_params["$offset"] = offset

        # Handle WHERE clause
        if "where_clause" in arguments and arguments["where_clause"]:
            query_params["$where"] = arguments["where_clause"]

        # Handle ORDER BY
        if "order_by" in arguments and arguments["order_by"]:
            query_params["$order"] = arguments["order_by"]

        # Handle SoQL aggregation parameters (Socrata SODA $select/$group).
        # These only take effect on the /resource/{id}.json endpoint; the legacy
        # /api/views/{id}/rows.json endpoint silently ignores them.
        if "select_clause" in arguments and arguments["select_clause"]:
            query_params["$select"] = arguments["select_clause"]

        if "group_clause" in arguments and arguments["group_clause"]:
            query_params["$group"] = arguments["group_clause"]

        if "having_clause" in arguments and arguments["having_clause"]:
            query_params["$having"] = arguments["having_clause"]

        # Full SoQL query string ($query). When provided it overrides the other
        # SoQL clauses, so drop them to avoid Socrata "cannot mix" errors.
        if soql_query:
            for clause in ("$select", "$where", "$group", "$having", "$order"):
                query_params.pop(clause, None)
            query_params["$query"] = soql_query

        # Add query string
        if query_params:
            url += "?" + urlencode(query_params)

        return url

    @staticmethod
    def _error(message: str) -> Dict[str, Any]:
        """Build a standard error envelope with a top-level ``error`` key.

        Keeps the legacy ``data.error`` field for backward compatibility while
        also exposing ``error`` at the top level so the return_schema oneOf
        error branch matches.
        """
        return {"status": "error", "error": message, "data": {"error": message}}

    def _make_request(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Make HTTP request to CDC Data API."""
        try:
            url = self._build_url(arguments)
        except ValueError as e:
            return self._error(str(e))

        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            return {
                "status": "success",
                "data": data,
                "metadata": {
                    "source": "CDC Data.CDC.gov",
                    "endpoint": url.split("?")[0],
                    "query": arguments,
                },
            }
        except requests.exceptions.RequestException as e:
            detail = ""
            resp_obj = getattr(e, "response", None)
            if resp_obj is not None:
                detail = f" ({(resp_obj.text or '')[:300]})"
            return self._error(f"Request failed: {str(e)}{detail}")
        except ValueError as e:
            return self._error(f"Failed to parse JSON: {str(e)}")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the CDC Data tool."""
        # Validate required parameters
        if "{dataset_id}" in self.endpoint_template:
            if "dataset_id" not in arguments:
                return self._error("dataset_id is required")

        return self._make_request(arguments)
