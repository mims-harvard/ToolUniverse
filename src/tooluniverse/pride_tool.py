import requests
from typing import Any, Dict
from .base_tool import BaseTool
from .http_utils import request_with_retry
from .tool_registry import register_tool


@register_tool("PRIDERESTTool")
class PRIDERESTTool(BaseTool):
    def __init__(self, tool_config: Dict):
        super().__init__(tool_config)
        self.base_url = "https://www.ebi.ac.uk/pride/ws/archive/v2"
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})
        self.timeout = 30

    def _build_url(self, args: Dict[str, Any]) -> str:
        url = self.tool_config["fields"]["endpoint"]
        for k, v in args.items():
            url = url.replace(f"{{{k}}}", str(v))

        # Fix-R12C-1: page_size is declared as a schema parameter but PRIDE's
        # search endpoint takes it as the query-string `pageSize` arg, not a
        # {page_size} placeholder in the endpoint template -- it was never
        # substituted anywhere and silently dropped. Append it explicitly,
        # falling back to the schema's own advertised default of 20 when the
        # caller omits it (confirmed live: PRIDE defaults to 100/page
        # otherwise, not the documented 20).
        if "page_size" in self.tool_config.get("parameter", {}).get("properties", {}):
            page_size = args.get("page_size", 20)
            separator = "&" if "?" in url else "?"
            url = f"{url}{separator}pageSize={page_size}"
        return url

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        url = None
        try:
            url = self._build_url(arguments)
            response = request_with_retry(
                self.session, "GET", url, timeout=self.timeout, max_attempts=3
            )
            if response.status_code != 200:
                error = "PRIDE API error"
                # Fix-R12C-3: PRIDE returns a bare HTTP 404 with an empty
                # body for any unrecognized identifier (e.g. a gene symbol
                # passed where a UniProt accession or PXD accession is
                # expected), so there is no upstream detail to surface --
                # the previous generic message gave no hint the identifier
                # itself was the problem.
                if response.status_code == 404:
                    error = (
                        "PRIDE API error: no record found for this identifier "
                        "(HTTP 404) -- check that it matches the ID format "
                        "this tool expects (see the tool's description)"
                    )
                return {
                    "status": "error",
                    "error": error,
                    "url": url,
                    "status_code": response.status_code,
                    "detail": (response.text or "")[:500],
                }
            data = response.json()
            return {"status": "success", "data": data, "url": url}
        except Exception as e:
            return {
                "status": "error",
                "error": f"PRIDE API error: {str(e)}",
                "url": url,
            }
