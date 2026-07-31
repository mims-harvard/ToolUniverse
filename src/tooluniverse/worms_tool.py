import requests
import urllib.parse
from typing import Any, Dict
from .base_tool import BaseTool
from .tool_registry import register_tool


# AphiaID-keyed enrichment operations. Each maps a `fields.operation` value to the
# WoRMS REST path that takes a single {AphiaID} path parameter and returns JSON.
_APHIA_OPERATIONS = {
    "classification": "AphiaClassificationByAphiaID",
    "vernaculars": "AphiaVernacularsByAphiaID",
    "distributions": "AphiaDistributionsByAphiaID",
    "synonyms": "AphiaSynonymsByAphiaID",
}


@register_tool("WoRMSRESTTool")
class WoRMSRESTTool(BaseTool):
    # Maximum number of records WoRMS returns from a single AphiaRecordsByName call.
    _PAGE_SIZE = 50

    def __init__(self, tool_config: Dict):
        super().__init__(tool_config)
        self.base_url = "https://www.marinespecies.org/rest"
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})
        self.timeout = 30

    def _operation(self) -> str:
        return self.tool_config.get("fields", {}).get("operation", "search_by_name")

    def _run_aphia_operation(
        self, operation: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Resolve an AphiaID to an enrichment resource (classification, vernaculars,
        distributions, synonyms). Returns the standard envelope and never raises."""
        aphia_id = arguments.get("AphiaID", arguments.get("aphia_id"))
        if aphia_id is None or str(aphia_id).strip() == "":
            return {"status": "error", "error": "AphiaID parameter is required"}
        try:
            aphia_id = int(aphia_id)
        except (TypeError, ValueError):
            return {
                "status": "error",
                "error": f"AphiaID must be an integer, got: {aphia_id!r}",
            }

        path = _APHIA_OPERATIONS[operation]
        url = f"{self.base_url}/{path}/{aphia_id}"
        try:
            response = self.session.get(url, timeout=self.timeout)
            # WoRMS returns HTTP 204 (no content) when a taxon has no records for
            # this resource. Treat that as a successful empty result.
            if response.status_code == 204 or not response.text.strip():
                empty = {} if operation == "classification" else []
                return {
                    "status": "success",
                    "data": empty,
                    "url": url,
                    "message": f"No {operation} records for AphiaID {aphia_id}",
                }
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            return {"status": "error", "error": f"WoRMS API error: {str(e)}"}

        result = {"status": "success", "data": data, "url": url, "AphiaID": aphia_id}
        if isinstance(data, list):
            result["count"] = len(data)
        return result

    def _run_search_by_name(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        query = arguments.get("query", "")
        if not query:
            return {"status": "error", "error": "Query parameter is required"}

        try:
            limit = int(arguments.get("limit", 20))
            offset = int(arguments.get("offset", 1))
        except (TypeError, ValueError):
            return {
                "status": "error",
                "error": (
                    "limit and offset must be integers, got "
                    f"limit={arguments.get('limit')!r}, "
                    f"offset={arguments.get('offset')!r}"
                ),
            }
        if limit < 1:
            return {"status": "error", "error": f"limit must be >= 1, got {limit}"}
        offset = max(offset, 1)

        encoded_query = urllib.parse.quote(query)
        base_url = f"{self.base_url}/AphiaRecordsByName/{encoded_query}"
        first_url = f"{base_url}?offset={offset}"

        # WoRMS caps every AphiaRecordsByName response at _PAGE_SIZE records and
        # pages with a 1-based `offset`. Walk pages until the caller's `limit` is
        # satisfied, fetching one record beyond it so `has_more` can be reported
        # without enumerating the entire result set.
        records: list = []
        page_offset = offset
        while len(records) <= limit:
            url = f"{base_url}?offset={page_offset}"
            try:
                response = self.session.get(url, timeout=self.timeout)
                # 204 / empty body = no (further) records for this query.
                if response.status_code == 204 or not response.text.strip():
                    break
                response.raise_for_status()
                page = response.json()
            except Exception as e:
                return {"status": "error", "error": f"WoRMS API error: {str(e)}"}
            if not isinstance(page, list) or not page:
                break
            records.extend(page)
            if len(page) < self._PAGE_SIZE:
                break
            page_offset += self._PAGE_SIZE

        if not records:
            return {
                "status": "success",
                "data": [],
                "url": first_url,
                "count": 0,
                "offset": offset,
                "limit": limit,
                "has_more": False,
                "message": "No results found for this query",
            }

        has_more = len(records) > limit
        page = records[:limit]
        return {
            "status": "success",
            "data": page,
            "url": first_url,
            "count": len(page),
            "offset": offset,
            "limit": limit,
            "has_more": has_more,
        }

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        operation = self._operation()
        if operation in _APHIA_OPERATIONS:
            return self._run_aphia_operation(operation, arguments)
        return self._run_search_by_name(arguments)
