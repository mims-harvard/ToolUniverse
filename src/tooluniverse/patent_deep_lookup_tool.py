"""USPTO Patent Deep Lookup --- batch pipeline that chains all patent tools.

Metadata
--------
name:          patent_deep_lookup_tool
version:       1.0.0
owner:         ToolUniverse
last_reviewed: 2026-04-17

WHY THIS SHAPE
--------------
Patent analysis is never one API call.  FTO, portfolio review, and prior-art
mapping all require *multiple* data slices per patent: metadata, ownership chain,
claim text, prosecution history, and AI-extracted citations.  Calling five tools
in a loop is fragile and slow.  This tool wraps that loop into a single call with
explicit module selection, built-in rate-limit handling, and result aggregation.

Flow
----
    patent_numbers OR search_query
        |
        v
    _resolve_patent_numbers()  -->  list[(raw, app_number)]
        OR
    _search_for_app_numbers()  -->  list[(query_hit, app_number)]
        |
        v
    for each app_number:
        for each module in include:
            _fetch_module(app_number, module)  -->  partial dict
        |
        v
    aggregate into [{patent_number, modules: {module: data}}]

Role / Module contract
----------------------
- Accepts a list of patent numbers (any format) OR a search query string.
- ``include`` selects which analyses to run (default: metadata only).
- Returns one result object per patent with requested module data attached.

Inputs:  ``{"patent_numbers": ["US9629826B2"], "include": ["metadata", "claims"]}``
Outputs: ``{"status": "success", "data": {"results": [...]}}``

Environment variables
---------------------
- ``USPTO_API_KEY`` --- required for ODP authentication (X-API-KEY header).

Callers
-------
- Agents doing batch FTO, portfolio review, or prior-art landscape analysis.

Usage example
-------------
    from tooluniverse.patent_deep_lookup_tool import PatentDeepLookupTool
    tool = PatentDeepLookupTool({"name": "USPTO_patent_deep_lookup"})
    result = tool.run({
        "patent_numbers": ["US9629826B2"],
        "include": ["metadata", "claims"],
    })
"""

# --- Imports ---
import logging
import os
import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .base_tool import BaseTool
from .tool_registry import register_tool

# --- Constants ---

VALID_MODULES = {
    "metadata",
    "assignment",
    "claims",
    "transactions",
    "enriched_citations",
}
MAX_PATENTS = 50
DEFAULT_LIMIT = 10
BACKOFF_SECONDS = 5
MAX_RETRIES = 3
BASE_URL = "https://api.uspto.gov/api/v1"

logger = logging.getLogger(__name__)


# --- Helpers (private) ---


def _cap(value: int | None, default: int, maximum: int) -> int:
    """Clamp an optional integer to [1, maximum], falling back to default."""
    if value is None:
        return default
    return max(1, min(int(value), maximum))


# --- Public API ---


@register_tool("PatentDeepLookupTool")
class PatentDeepLookupTool(BaseTool):
    """Batch pipeline that chains patent resolver, claims, and DSAPI tools."""

    def __init__(
        self,
        tool_config: dict,
        api_key: str | None = None,
        base_url: str = BASE_URL,
    ) -> None:
        super().__init__(tool_config)
        self.base_url = base_url

        # Read key at init time (not module level) so monkeypatch works in tests
        self.api_key = api_key or os.environ.get("USPTO_API_KEY")
        if not self.api_key:
            raise ValueError(
                "USPTO_API_KEY environment variable is required. "
                "Get one at https://developer.uspto.gov"
            )

        self.headers = {"X-API-KEY": self.api_key, "Accept": "application/json"}

        # Retry on server errors only --- we handle 429 manually for logging
        self.session = requests.Session()
        retry = Retry(
            total=5,
            status_forcelist=[500, 502, 503, 504],
            backoff_factor=5,
            raise_on_status=False,
        )
        self.session.mount("https://", HTTPAdapter(max_retries=retry))

    # -- validation helpers --

    def _validate_include(self, include: list[str] | None) -> list[str]:
        """Return a validated module list, defaulting to ['metadata']."""
        if not include:
            return ["metadata"]
        return list(include)

    def _apply_limit(self, limit: int | None) -> int:
        """Cap the patent count at MAX_PATENTS, default to DEFAULT_LIMIT."""
        return _cap(limit, DEFAULT_LIMIT, MAX_PATENTS)

    # -- HTTP helper with manual 429 backoff --

    def _api_get(
        self, url: str, params: dict | None = None, timeout: int = 60
    ) -> requests.Response:
        """GET with manual 429 retry so we can log each backoff."""
        for attempt in range(MAX_RETRIES + 1):
            resp = self.session.get(
                url, headers=self.headers, params=params, timeout=timeout
            )

            if resp.status_code != 429:
                return resp

            # 429 Too Many Requests --- back off and retry
            if attempt < MAX_RETRIES:
                logger.warning(
                    "USPTO 429 rate limit, sleeping %ds (attempt %d/%d)",
                    BACKOFF_SECONDS,
                    attempt + 1,
                    MAX_RETRIES,
                )
                time.sleep(BACKOFF_SECONDS)

        # Exhausted retries on 429 --- return last response so caller sees the error
        return resp

    # -- resolution helpers --

    def _resolve_patent_numbers(self, raw_numbers: list[str]) -> list[dict]:
        """Resolve each raw patent number via PatentResolverTool.

        Returns list of dicts with keys: raw, app_number, error.
        """
        # Lazy import to avoid circular dependency at module level
        from .patent_resolver_tool import PatentResolverTool

        resolver = PatentResolverTool(
            {"name": "USPTO_patent_number_to_application"},
            api_key=self.api_key,
        )

        results = []
        for raw in raw_numbers:
            outcome = resolver.run({"patent_number": raw})
            if outcome.get("status") == "error":
                results.append(
                    {
                        "raw": raw,
                        "app_number": None,
                        "error": outcome.get("error", "Resolution failed"),
                    }
                )
            else:
                app_num = outcome.get("data", {}).get("applicationNumberText", "")
                results.append(
                    {
                        "raw": raw,
                        "app_number": app_num,
                        "error": None,
                        "metadata": outcome.get("data"),
                    }
                )
        return results

    def _search_for_app_numbers(self, search_query: str, limit: int) -> list[dict]:
        """Run an ODP search query and extract application numbers from hits."""
        resp = self._api_get(
            f"{self.base_url}/patent/applications/search",
            params={"q": search_query, "limit": limit},
        )
        resp.raise_for_status()

        results = []
        for entry in resp.json().get("patentFileWrapperDataBag", []):
            meta = entry.get("applicationMetaData", {})
            app_num = meta.get("applicationNumberText", "")
            if app_num:
                results.append(
                    {
                        "raw": search_query,
                        "app_number": app_num,
                        "error": None,
                        "metadata": meta,
                    }
                )
        return results

    # -- per-module fetchers --

    def _fetch_metadata(self, app_number: str) -> dict:
        """Fetch application metadata from /meta-data endpoint."""
        resp = self._api_get(
            f"{self.base_url}/patent/applications/{app_number}/meta-data"
        )
        resp.raise_for_status()
        bag = resp.json().get("patentFileWrapperDataBag", [])
        if not bag:
            return {"error": f"No metadata found for {app_number}"}
        return bag[0].get("applicationMetaData", {})

    def _fetch_assignment(self, app_number: str) -> dict:
        """Fetch ownership/assignment chain from /assignment endpoint."""
        resp = self._api_get(
            f"{self.base_url}/patent/applications/{app_number}/assignment"
        )
        resp.raise_for_status()
        return resp.json()

    def _fetch_claims(self, app_number: str) -> dict:
        """Delegate to PatentClaimsTool for XML download + parsing."""
        from .patent_claims_tool import PatentClaimsTool

        claims_tool = PatentClaimsTool(
            {"name": "USPTO_get_patent_claims"},
            api_key=self.api_key,
        )
        result = claims_tool.run({"applicationNumberText": app_number})
        if result.get("status") == "error":
            return {"error": result.get("error", "Claims extraction failed")}
        return result.get("data", {})

    def _fetch_transactions(self, app_number: str) -> dict:
        """Fetch prosecution transaction history."""
        resp = self._api_get(
            f"{self.base_url}/patent/applications/{app_number}/transactions"
        )
        resp.raise_for_status()
        return resp.json()

    def _fetch_enriched_citations(self, app_number: str) -> dict:
        """Delegate to DSAPITool for AI-extracted citation data."""
        from .dsapi_tool import DSAPITool

        dsapi_tool = DSAPITool(
            {
                "name": "USPTO_search_enriched_citations",
                "api_endpoint": "patent/oa/enriched_cited_reference_metadata/v3/records",
            },
            api_key=self.api_key,
        )
        result = dsapi_tool.run({"query": f"patentApplicationNumber:{app_number}"})
        if result.get("status") == "error":
            return {"error": result.get("error", "Citation lookup failed")}
        return result.get("data", {})

    # -- module dispatcher --

    _MODULE_DISPATCH = {
        "metadata": "_fetch_metadata",
        "assignment": "_fetch_assignment",
        "claims": "_fetch_claims",
        "transactions": "_fetch_transactions",
        "enriched_citations": "_fetch_enriched_citations",
    }

    def _fetch_module(self, app_number: str, module: str) -> dict:
        """Dispatch to the right fetcher for a given module name."""
        method_name = self._MODULE_DISPATCH.get(module)
        if not method_name:
            return {"error": f"Unknown module: {module}"}
        try:
            return getattr(self, method_name)(app_number)
        except requests.exceptions.RequestException as exc:
            return {"error": f"{module} fetch failed: {exc}"}

    # -- public interface --

    def run(self, arguments: dict | None = None) -> dict:
        """Execute the batch patent analysis pipeline."""
        arguments = arguments or {}

        patent_numbers = arguments.get("patent_numbers")
        search_query = arguments.get("search_query", "").strip()
        include = arguments.get("include")
        limit = self._apply_limit(arguments.get("limit"))

        # --- Validate inputs ---

        # Must provide at least one input source
        if not patent_numbers and not search_query:
            return self.tool_error(
                "Provide patent_numbers (list) or search_query (string).",
                error_type="ValidationError",
                suggestion="Example: {'patent_numbers': ['US9629826B2']} "
                "or {'search_query': 'applicationMetaData.patentNumber:9629826'}",
            )

        # Empty list is also invalid
        if patent_numbers is not None and len(patent_numbers) == 0:
            return self.tool_error(
                "patent_numbers list is empty.",
                error_type="ValidationError",
                suggestion="Provide at least one patent number.",
            )

        # Validate module names
        include = self._validate_include(include)
        invalid = [m for m in include if m not in VALID_MODULES]
        if invalid:
            return self.tool_error(
                f"Invalid include modules: {', '.join(invalid)}",
                error_type="ValidationError",
                suggestion=f"Valid modules: {', '.join(sorted(VALID_MODULES))}",
            )

        # --- Resolve patent numbers ---
        try:
            if patent_numbers:
                # Cap the list length before resolving
                capped = patent_numbers[:limit]
                resolved = self._resolve_patent_numbers(capped)
            else:
                resolved = self._search_for_app_numbers(search_query, limit)
        except requests.exceptions.RequestException as exc:
            return self.tool_error(
                f"USPTO API request failed during resolution: {exc}",
                error_type="NetworkError",
                suggestion="Check USPTO_API_KEY and network connectivity.",
            )

        # --- Fetch requested modules for each patent ---
        results = []
        for entry in resolved:
            app_number = entry.get("app_number")
            record: dict = {"patent_number": entry["raw"], "app_number": app_number}

            if not app_number:
                record["error"] = entry.get("error", "Could not resolve patent number")
                results.append(record)
                continue

            # If resolver already gave us metadata and we need it, reuse it
            modules: dict = {}
            if "metadata" in include and entry.get("metadata"):
                modules["metadata"] = entry["metadata"]

            # Fetch remaining requested modules
            for module in include:
                if module in modules:
                    continue  # already populated (e.g. metadata from resolver)
                modules[module] = self._fetch_module(app_number, module)

            record["modules"] = modules
            results.append(record)

        return {
            "status": "success",
            "data": {
                "patent_count": len(results),
                "modules_requested": include,
                "results": results,
            },
        }
