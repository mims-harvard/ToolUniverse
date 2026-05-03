import requests
from typing import Any, Dict
from .base_tool import BaseTool
from .tool_registry import register_tool


@register_tool("JASPARRESTTool")
class JASPARRESTTool(BaseTool):
    def __init__(self, tool_config: Dict):
        super().__init__(tool_config)
        self.base_url = "https://jaspar.elixir.no/api/v1"
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
            fields_cfg = self.tool_config.get("fields", {}) or {}
            use_params = bool(fields_cfg.get("use_params", False))

            if use_params:
                # Treat endpoint as a base URL and pass arguments as query
                # params. This is useful for JASPAR endpoints that support many
                # optional query parameters (e.g., /matrix/?search=...).
                url = fields_cfg["endpoint"]
                params = {k: v for k, v in arguments.items() if v is not None}

                # Support path placeholders even in param mode
                # (e.g., /matrix/{base_id}/versions/).
                for k, v in list(params.items()):
                    ph = f"{{{k}}}"
                    if ph in url:
                        url = url.replace(ph, str(v))
                        params.pop(k, None)

                response = self.session.get(url, params=params, timeout=self.timeout)
            else:
                url = self._build_url(arguments)
                response = self.session.get(url, timeout=self.timeout)

            response.raise_for_status()
            data = response.json()
            return {"status": "success", "data": data, "url": response.url}
        except Exception as e:
            return {"status": "error", "error": f"JASPAR API error: {str(e)}"}
