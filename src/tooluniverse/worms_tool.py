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

        encoded_query = urllib.parse.quote(query)
        url = f"{self.base_url}/AphiaRecordsByName/{encoded_query}"
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            if not response.text.strip():
                return {
                    "status": "success",
                    "data": [],
                    "url": url,
                    "message": "No results found for this query",
                }
            data = response.json()
        except Exception as e:
            return {"status": "error", "error": f"WoRMS API error: {str(e)}"}

        if isinstance(data, list) and len(data) > 0:
            limited_data = data[:5]
            return {
                "status": "success",
                "data": limited_data,
                "url": url,
                "count": len(limited_data),
                "total_found": len(data),
            }
        return {"status": "success", "data": data, "url": url}

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        operation = self._operation()
        if operation in _APHIA_OPERATIONS:
            return self._run_aphia_operation(operation, arguments)
        return self._run_search_by_name(arguments)
