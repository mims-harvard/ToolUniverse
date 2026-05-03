import requests
import urllib.parse
from typing import Any, Dict
from .base_tool import BaseTool
from .tool_registry import register_tool


@register_tool("WoRMSRESTTool")
class WoRMSRESTTool(BaseTool):
    def __init__(self, tool_config: Dict):
        super().__init__(tool_config)
        self.base_url = "https://www.marinespecies.org/rest"
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})
        self.timeout = 30

    def _build_url(self, args: Dict[str, Any]) -> str:
        url = self.tool_config["fields"]["endpoint"]
        for k, v in args.items():
            url = url.replace(f"{{{k}}}", str(v))
        return url

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        try:
            # Build URL with proper encoding
            query = arguments.get("query", "")
            if not query:
                return {"status": "error", "error": "Query parameter is required"}

            # URL encode the query
            encoded_query = urllib.parse.quote(query)
            url = (
                f"https://www.marinespecies.org/rest/AphiaRecordsByName/{encoded_query}"
            )

            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()

            # Check if response is empty
            if not response.text.strip():
                return {
                    "status": "success",
                    "data": [],
                    "url": url,
                    "message": "No results found for this query",
                }

            data = response.json()

            # WoRMS returns array of species, extract first few results
            if isinstance(data, list) and len(data) > 0:
                # Limit results to first 5 for better performance
                limited_data = data[:5]
                return {
                    "status": "success",
                    "data": limited_data,
                    "url": url,
                    "count": len(limited_data),
                    "total_found": len(data),
                }
            else:
                return {"status": "success", "data": data, "url": url}
        except Exception as e:
            return {"status": "error", "error": f"WoRMS API error: {str(e)}"}
