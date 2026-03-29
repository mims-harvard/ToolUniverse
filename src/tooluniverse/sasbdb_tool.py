import requests
from typing import Any, Dict
from .base_tool import BaseTool
from .http_utils import request_with_retry
from .tool_registry import register_tool

BASE_URL = "https://www.sasbdb.org/rest-api"


@register_tool("SASBDBSearchTool")
class SASBDBSearchTool(BaseTool):
    """SASBDB search tool - lists entries by molecular type or all entries."""

    def __init__(self, tool_config: Dict):
        super().__init__(tool_config)
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})
        self.timeout = 30

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        mol_type = arguments.get("molecular_type")
        if mol_type:
            url = f"{BASE_URL}/entry/codes/molecular_type/{mol_type}/"
        else:
            url = f"{BASE_URL}/entry/codes/all/"
        try:
            resp = request_with_retry(
                self.session, "GET", url, timeout=self.timeout, max_attempts=3
            )
            if resp.status_code != 200:
                return {
                    "status": "error",
                    "error": f"SASBDB API error: HTTP {resp.status_code}",
                }
            return {"status": "success", "data": resp.json()}
        except Exception as e:
            return {"status": "error", "error": f"SASBDB API error: {e}"}


@register_tool("SASBDBTextSearchTool")
class SASBDBTextSearchTool(BaseTool):
    """SASBDB search by text query — routes to UniProt lookup or molecular-type listing."""

    def __init__(self, tool_config: Dict):
        super().__init__(tool_config)
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})
        self.timeout = 30

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        import re

        query = (
            arguments.get("query")
            or arguments.get("term")
            or arguments.get("molecular_type")
            or ""
        )
        # If it looks like a UniProt accession, search by UniProt
        if query and re.match(
            r"^[OPQ][0-9][A-Z0-9]{3}[0-9]$|^[A-NR-Z][0-9]([A-Z][A-Z0-9]{2}[0-9]){1,2}$",
            query,
        ):
            url = f"{BASE_URL}/entry/codes/uniprot/{query}/"
            try:
                resp = request_with_retry(
                    self.session, "GET", url, timeout=self.timeout, max_attempts=3
                )
                if resp.status_code == 200:
                    return {
                        "status": "success",
                        "data": resp.json(),
                        "note": f"Results retrieved for UniProt accession '{query}'.",
                    }
            except Exception as e:
                return {"status": "error", "error": f"SASBDB API error: {e}"}
        # Fall back to listing all entries with a note that text search is unavailable
        url = f"{BASE_URL}/entry/codes/all/"
        try:
            resp = request_with_retry(
                self.session, "GET", url, timeout=self.timeout, max_attempts=3
            )
            if resp.status_code != 200:
                return {
                    "status": "error",
                    "error": f"SASBDB API error: HTTP {resp.status_code}",
                }
            entries = resp.json()
            return {
                "status": "success",
                "data": entries,
                "note": (
                    f"SASBDB does not support free-text search. "
                    f"Returned all {len(entries)} published entries. "
                    f"To search by protein, provide a UniProt accession (e.g., 'P02769' for BSA). "
                    f"Use SASBDB_get_entry with a specific code (e.g., 'SASDCZ9') for details."
                ),
            }
        except Exception as e:
            return {"status": "error", "error": f"SASBDB API error: {e}"}


@register_tool("SASBDBRESTTool")
class SASBDBRESTTool(BaseTool):
    """SASBDB API tool for small-angle scattering (SAXS/SANS) data."""

    def __init__(self, tool_config: Dict):
        super().__init__(tool_config)
        self.session = requests.Session()
        self.session.headers.update(
            {"Accept": "application/json", "User-Agent": "ToolUniverse/1.0"}
        )
        self.timeout = 30

    def _build_url(self, args: Dict[str, Any]) -> str:
        """Build the full API URL, substituting path parameters."""
        url = self.tool_config["fields"]["endpoint"]
        for k, v in args.items():
            url = url.replace(f"{{{k}}}", str(v))
        return url

    def _build_query_params(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Return query parameters (those not used as path parameters)."""
        endpoint = self.tool_config["fields"]["endpoint"]
        return {
            k: v
            for k, v in args.items()
            if f"{{{k}}}" not in endpoint and v is not None
        }

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the SASBDB API request."""
        url = None
        try:
            url = self._build_url(arguments)
            params = self._build_query_params(arguments)

            response = request_with_retry(
                self.session,
                "GET",
                url,
                params=params or None,
                timeout=self.timeout,
                max_attempts=3,
            )

            if response.status_code != 200:
                return {
                    "status": "error",
                    "error": "SASBDB API error",
                    "url": url,
                    "status_code": response.status_code,
                    "detail": (response.text or "")[:500],
                }

            return {"status": "success", "data": response.json(), "url": url}

        except Exception as e:
            return {"status": "error", "error": f"SASBDB API error: {e}", "url": url}
