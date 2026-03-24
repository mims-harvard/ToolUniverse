"""Custom iCite tool that searches PubMed first, then enriches with iCite metrics.

The iCite API (https://icite.od.nih.gov/api/pubs) only supports PMID lookups,
not keyword search. This tool bridges the gap by first searching PubMed via
eSearch to get PMIDs, then fetching iCite citation metrics for those PMIDs.
"""

import os
import time
import threading
from typing import Any, Dict
from .base_rest_tool import BaseRESTTool
from .http_utils import request_with_retry
from .tool_registry import register_tool


@register_tool("ICiteSearchPublicationsTool")
class ICiteSearchPublicationsTool(BaseRESTTool):
    """Search PubMed by keyword, then enrich results with iCite citation metrics.

    The iCite API only accepts PMIDs — it has no keyword search endpoint.
    This tool first queries PubMed eSearch, then batch-fetches iCite metrics.
    """

    _last_request_time = 0.0
    _rate_limit_lock = threading.Lock()

    PUBMED_ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    ICITE_API = "https://icite.od.nih.gov/api/pubs"

    def _enforce_rate_limit(self) -> None:
        has_key = bool(os.environ.get("NCBI_API_KEY"))
        min_interval = 0.15 if has_key else 0.4
        with self._rate_limit_lock:
            now = time.time()
            elapsed = now - ICiteSearchPublicationsTool._last_request_time
            if elapsed < min_interval:
                time.sleep(min_interval - elapsed)
            ICiteSearchPublicationsTool._last_request_time = time.time()

    def _search_pubmed(self, query: str, limit: int) -> list:
        """Search PubMed eSearch and return list of PMID strings."""
        self._enforce_rate_limit()
        params = {
            "db": "pubmed",
            "term": query,
            "retmode": "json",
            "retmax": limit,
            "sort": "relevance",
        }
        api_key = os.environ.get("NCBI_API_KEY")
        if api_key:
            params["api_key"] = api_key

        resp = request_with_retry(
            self.session,
            "GET",
            self.PUBMED_ESEARCH,
            params=params,
            timeout=self.timeout,
            max_attempts=3,
        )
        if resp.status_code != 200:
            return []
        data = resp.json()
        return data.get("esearchresult", {}).get("idlist", [])

    def _fetch_icite(self, pmids: list) -> list:
        """Fetch iCite metrics for a list of PMIDs."""
        if not pmids:
            return []
        resp = request_with_retry(
            self.session,
            "GET",
            self.ICITE_API,
            params={"pmids": ",".join(pmids), "format": "json"},
            timeout=self.timeout,
            max_attempts=3,
        )
        if resp.status_code != 200:
            return []
        data = resp.json()
        return data.get("data", [])

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        query = arguments.get("query", "")
        limit = int(arguments.get("limit") or 10)
        offset = int(arguments.get("offset") or 0)

        if not query:
            return {"status": "error", "error": "query parameter is required"}

        try:
            # Fetch more from PubMed to account for offset
            fetch_count = min(limit + offset, 1000)
            pmids = self._search_pubmed(query, fetch_count)

            if not pmids:
                return {
                    "status": "success",
                    "data": [],
                    "message": f"No PubMed results found for query: {query}",
                }

            # Apply offset
            pmids = pmids[offset:]

            # Batch iCite in chunks of 100
            all_pubs = []
            for i in range(0, len(pmids), 100):
                chunk = pmids[i : i + 100]
                all_pubs.extend(self._fetch_icite(chunk))

            # Sort by citation_count descending
            all_pubs.sort(key=lambda p: p.get("citation_count", 0), reverse=True)

            # Trim to requested limit
            all_pubs = all_pubs[:limit]

            return {"data": all_pubs}

        except Exception as e:
            return {"status": "error", "error": f"iCite search error: {e}"}
