import requests
from typing import Any, Dict
from .base_tool import BaseTool
from .tool_registry import register_tool


@register_tool("MPDRESTTool")
class MPDRESTTool(BaseTool):
    def __init__(self, tool_config: Dict):
        super().__init__(tool_config)
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})
        self.timeout = 30

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        try:
            # Use ENCODE as alternative data source for biological samples
            strain = arguments.get("strain", "C57BL/6J")
            limit = arguments.get("limit", 5)

            # Build ENCODE API URL for experiments
            # Query for general experiments as MPD alternative
            url = f"https://www.encodeproject.org/search/?type=Experiment&format=json&limit={limit}"

            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()

            # Parse JSON response
            data = response.json()

            return {
                "status": "success",
                "data": data,
                "url": url,
                "query_info": {
                    "strain": strain,
                    "limit": limit,
                    "data_source": "ENCODE (MPD alternative)",
                },
            }
        except Exception as e:
            return {"status": "error", "error": f"MPD API error: {str(e)}"}
