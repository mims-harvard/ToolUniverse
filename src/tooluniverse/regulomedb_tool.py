import requests
from typing import Any, Dict
from .base_tool import BaseTool
from .tool_registry import register_tool


@register_tool("RegulomeDBRESTTool")
class RegulomeDBRESTTool(BaseTool):
    def __init__(self, tool_config: Dict):
        super().__init__(tool_config)
        self.base_url = "https://regulomedb.org"
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})
        self.timeout = 30

    def _build_url(self, args: Dict[str, Any]) -> str:
        url = self.tool_config["fields"]["endpoint"]
        for k, v in args.items():
            url = url.replace(f"{{{k}}}", str(v))
        return url

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        # Accept 'variant' as alias for 'rsid' (used by RegulomeDB_get_score)
        if "rsid" not in arguments and arguments.get("variant"):
            arguments = dict(arguments, rsid=arguments["variant"])
        try:
            url = self._build_url(arguments)
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            raw = response.json()
        except Exception as e:
            return {"status": "error", "error": f"RegulomeDB API error: {str(e)}"}

        # Extract the key RegulomeDB fields; @graph contains raw ENCODE datasets
        # (hundreds of entries) and is not useful for most callers.
        variants = raw.get("variants", [])
        if not variants:
            return {
                "status": "error",
                "error": f"No RegulomeDB results for rsID '{arguments.get('rsid', '')}'",
            }

        result = {
            "rsid": arguments.get("rsid", ""),
            "assembly": raw.get("assembly"),
            "query_coordinates": raw.get("query_coordinates"),
            "regulome_score": raw.get("regulome_score"),
            "variants": variants,
            "features": raw.get("features"),
            "nearby_snps": raw.get("nearby_snps", [])[:10],
            "notifications": raw.get("notifications"),
            "total_supporting_datasets": len(raw.get("@graph", [])),
        }
        return {"status": "success", "data": result, "url": url}
