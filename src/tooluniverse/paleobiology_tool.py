import requests
from typing import Any, Dict
from .base_tool import BaseTool
from .tool_registry import register_tool


@register_tool("PaleobiologyRESTTool")
class PaleobiologyRESTTool(BaseTool):
    def __init__(self, tool_config: Dict):
        super().__init__(tool_config)
        self.base_url = "https://paleobiodb.org/data1.2"
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
            url = self._build_url(arguments)
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            return {"status": "success", "data": data, "url": url}
        except Exception as e:
            return {"status": "error", "error": f"Paleobiology API error: {str(e)}"}
