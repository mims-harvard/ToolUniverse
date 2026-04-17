"""USPTO DSAPI (Decision Support API) tool for Office Action endpoints.

Metadata
--------
Module : dsapi_tool.py
Type   : DSAPITool (registered via @register_tool)
Parent : BaseTool

WHY THIS SHAPE
--------------
The USPTO Open Data Portal exposes two distinct endpoint families:

  1. REST/GET endpoints  -- handled by USPTOOpenDataPortalTool
  2. DSAPI/POST endpoints -- handled HERE by DSAPITool

DSAPI endpoints differ in every HTTP dimension:
  - Method : POST (not GET)
  - Body   : form-encoded (not query params or JSON)
  - Query  : Lucene syntax (not OpenSearch DSL)
  - Pagination : start/rows (Solr-style, not offset/limit)
  - Response : wrapped in {"response": {numFound, start, docs}}

A separate class keeps each concern isolated rather than overloading
USPTOOpenDataPortalTool with conditional branches.

Flow
----
    caller
      |
      v
    run(arguments)
      |-- validate: query present?
      |-- map: query->criteria, offset->start, limit->rows
      |-- POST form-encoded to USPTO API
      |-- unwrap {"response": ...} envelope
      v
    {status, data}

Role    : HTTP adapter -- translates agent-friendly params to DSAPI wire format
Inputs  : arguments dict with query (required), offset, limit (optional)
Outputs : {status: "success"|"error", data: {numFound, start, docs}}

Environment variables
---------------------
USPTO_API_KEY : Required. Obtain from https://developer.uspto.gov

Callers
-------
ToolUniverse.run_one_function() via tool_config["type"] == "DSAPITool"

Usage
-----
    tool = DSAPITool(config_from_dsapi_tools_json)
    result = tool.run({"query": "patentApplicationNumber:14966067"})
"""

import os

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .base_tool import BaseTool
from .tool_registry import register_tool

# --- Constants ---

_BASE_URL = "https://api.uspto.gov/api/v1"
_DEFAULT_ROWS = 25
_DEFAULT_START = 0


# --- Public API ---


@register_tool("DSAPITool")
class DSAPITool(BaseTool):
    """HTTP adapter for USPTO DSAPI (Office Action) POST endpoints."""

    def __init__(
        self,
        tool_config: dict,
        api_key: str | None = None,
        base_url: str = _BASE_URL,
    ) -> None:
        super().__init__(tool_config)
        self.base_url = base_url

        # Read key at init time (not module level) so monkeypatch works in tests
        api_key = api_key or os.environ.get("USPTO_API_KEY")
        if not api_key:
            raise ValueError(
                "USPTO_API_KEY environment variable is required. "
                "Get one at https://developer.uspto.gov"
            )

        self.headers = {"X-API-KEY": api_key, "Accept": "application/json"}

        # Retry strategy matches USPTOOpenDataPortalTool for consistency
        self.session = requests.Session()
        retry = Retry(
            total=5,
            status_forcelist=[429, 500, 502, 503, 504],
            backoff_factor=5,
            raise_on_status=False,
        )
        self.session.mount("https://", HTTPAdapter(max_retries=retry))

    def run(self, arguments: dict | None = None) -> dict:
        """Execute a DSAPI POST request.

        Maps agent-friendly parameter names to DSAPI wire format:
          query  -> criteria  (Lucene query string)
          offset -> start     (Solr pagination start)
          limit  -> rows      (Solr page size)
        """
        arguments = arguments or {}

        # --- Validate ---
        query = arguments.get("query")
        if not query:
            return self.tool_error(
                "Missing required parameter 'query'.",
                suggestion="Provide a Lucene query, e.g. 'patentApplicationNumber:14966067'",
            )

        endpoint = self.tool_config.get("api_endpoint")
        if not endpoint:
            return self.tool_error("No api_endpoint in tool configuration.")

        # --- Map params to DSAPI wire format ---
        form_data = {
            "criteria": query,
            "start": arguments.get("offset", _DEFAULT_START),
            "rows": arguments.get("limit", _DEFAULT_ROWS),
        }

        # --- Execute ---
        url = f"{self.base_url}/{endpoint}"
        try:
            # DSAPI requires form-encoded POST (data=), NOT json=
            response = self.session.post(
                url,
                headers=self.headers,
                data=form_data,
                timeout=30,
            )
            response.raise_for_status()
            body = response.json()
        except requests.exceptions.RequestException as exc:
            return self.tool_error(
                f"DSAPI request failed: {exc}",
                error_type="ToolUnavailableError",
            )

        # --- Unwrap Solr envelope ---
        inner = body.get("response", body)
        return {
            "status": "success",
            "data": {
                "numFound": inner.get("numFound", 0),
                "start": inner.get("start", 0),
                "docs": inner.get("docs", []),
            },
        }
