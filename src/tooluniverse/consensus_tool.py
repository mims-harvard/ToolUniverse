import os

import requests

from .base_tool import BaseTool
from .http_utils import request_with_retry
from .tool_registry import register_tool

_BOOL_PARAMS = (
    "human",
    "controlled",
    "exclude_preprints",
    "medical_mode",
    "open_access",
    "include_semantic_score",
    "include_full_text_chunks",
)
_PASSTHROUGH_PARAMS = (
    "year_min",
    "year_max",
    "month_min",
    "month_max",
    "study_types",
    "sample_size_min",
    "sjr_min",
    "sjr_max",
    "citation_min",
    "domain",
    "country",
    "journal_name",
    "publisher_name",
    "page",
)


@register_tool("ConsensusTool")
class ConsensusTool(BaseTool):
    """
    Search 220M+ peer-reviewed papers via the Consensus API.

    API key is required and read from the CONSENSUS_API_KEY environment
    variable. Request one at: https://consensus.app/home/api
    """

    def __init__(self, tool_config, base_url="https://api.consensus.app/v1/search"):
        super().__init__(tool_config)
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})

    def run(self, arguments):
        query = arguments.get("query")
        if not query:
            return {"status": "error", "error": "`query` parameter is required."}

        api_key = os.environ.get("CONSENSUS_API_KEY", "")
        if not api_key:
            return {
                "status": "error",
                "error": (
                    "CONSENSUS_API_KEY environment variable is not set. "
                    "Request a key at https://consensus.app/home/api."
                ),
            }

        params = {"query": query}
        for name in _BOOL_PARAMS:
            value = arguments.get(name)
            if value is not None:
                params[name] = "true" if value else "false"
        for name in _PASSTHROUGH_PARAMS:
            value = arguments.get(name)
            if value is not None:
                params[name] = value

        try:
            response = request_with_retry(
                self.session,
                "GET",
                self.base_url,
                params=params,
                headers={"x-api-key": api_key},
                timeout=30,
            )
        except requests.RequestException as exc:
            return {"status": "error", "error": f"Request failed: {exc}"}

        if response.status_code == 401:
            return {
                "status": "error",
                "error": "Consensus rejected the API key (401 Not authenticated).",
            }
        if response.status_code != 200:
            return {
                "status": "error",
                "error": f"Consensus API returned {response.status_code}: {response.reason}",
                "retryable": response.status_code in (429, 500, 502, 503, 504),
            }

        try:
            payload = response.json()
        except ValueError:
            return {
                "status": "error",
                "error": "Consensus API returned a non-JSON response.",
            }

        results = payload.get("results", [])
        return {
            "status": "success",
            "data": results,
            "metadata": {
                "query": query,
                "returned": len(results),
                "page": payload.get("page"),
                "page_size": payload.get("page_size"),
                "is_end": payload.get("is_end"),
                "next_page": payload.get("next_page"),
            },
        }
