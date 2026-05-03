import requests
from typing import Any, Dict
from .base_tool import BaseTool
from .http_utils import request_with_retry
from .tool_registry import register_tool


@register_tool("EMDBRESTTool")
class EMDBRESTTool(BaseTool):
    def __init__(self, tool_config: Dict):
        super().__init__(tool_config)
        self.base_url = "https://www.ebi.ac.uk/emdb/api"
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})
        self.timeout = 30

    def _build_url(self, args: Dict[str, Any]) -> str:
        url = self.tool_config["fields"]["endpoint"]
        for k, v in args.items():
            url = url.replace(f"{{{k}}}", str(v))
        return url

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        url = None
        try:
            url = self._build_url(arguments)
            response = request_with_retry(
                self.session, "GET", url, timeout=self.timeout, max_attempts=3
            )
            if response.status_code != 200:
                return {
                    "status": "error",
                    "error": "EMDB API error",
                    "url": url,
                    "status_code": response.status_code,
                    "detail": (response.text or "")[:500],
                }
            data = response.json()
            return {"status": "success", "data": data, "url": url}
        except Exception as e:
            return {
                "status": "error",
                "error": f"EMDB API error: {str(e)}",
                "url": url,
            }
