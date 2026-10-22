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

    def _search_pubmed(self, query: str, limit: int, offset: int) -> tuple[list, int | None]:
        """Return one PubMed page and the exact global match count."""
        self._enforce_rate_limit()
        params = {
            "db": "pubmed",
            "term": query,
            "retmode": "json",
            "retmax": limit,
            "retstart": offset,
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
        # Fix-R75A-1: a genuine zero-hit PubMed query returns HTTP 200 with
        # an empty idlist (confirmed live) -- a non-200 here always means
        # the request itself failed (rate limit, outage, etc.), never
        # "no results." The old `if status_code != 200: return []` made
        # both cases produce the identical empty list, so run()'s "No
        # PubMed results found for query: {query}" success message
        # silently misreported real request failures as empty searches.
        # Raise instead, so run()'s existing except-Exception surfaces it
        # as an actual error.
        resp.raise_for_status()
        data = resp.json()
        result = data.get("esearchresult", {})
        ids = result.get("idlist", [])
        # A real eSearch response honors retmax.  Retain compatibility with
        # simple test/fallback responders that return the unpaged ID list.
        if len(ids) > limit:
            ids = ids[offset : offset + limit] if offset else ids[:limit]
        try:
            total = int(result["count"])
        except (KeyError, TypeError, ValueError):
            total = None
        return ids, total

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
        # Fix-R75A-1: same reasoning as _search_pubmed -- a failed batch
        # fetch previously vanished silently (extend() of an empty list),
        # under-representing citation data for that PMID chunk with no
        # error at all. Raise so the caller's except-Exception catches it.
        resp.raise_for_status()
        data = resp.json()
        return data.get("data", [])

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        query = arguments.get("query", "")
        raw_limit = arguments.get("limit", 10)
        raw_offset = arguments.get("offset", 0)

        if not query:
            return {"status": "error", "error": "query parameter is required"}
        if isinstance(raw_limit, bool) or not isinstance(raw_limit, int):
            return {"status": "error", "error": "limit must be a positive integer"}
        if isinstance(raw_offset, bool) or not isinstance(raw_offset, int):
            return {
                "status": "error",
                "error": "offset must be a non-negative integer",
            }
        limit = raw_limit
        offset = raw_offset
        if limit < 1 or limit > 1000:
            return {"status": "error", "error": "limit must be between 1 and 1000"}
        if offset < 0:
            return {
                "status": "error",
                "error": "offset must be a non-negative integer",
            }

        try:
            pmids, total_results = self._search_pubmed(query, limit, offset)

            if not pmids:
                stalled = total_results is not None and offset < total_results
                return {
                    "status": "success",
                    "data": [],
                    "message": (
                        "PubMed reported additional matches but returned an empty page at this offset."
                        if stalled
                        else f"No PubMed results found for query: {query}"
                    ),
                    "metadata": {
                        "query": query,
                        "returned": 0,
                        "total_results": total_results,
                        "offset": offset,
                        "limit": limit,
                        "has_more": False,
                        "next_offset": None,
                        "pagination_stalled": stalled,
                        "warning": (
                            "Do not retry the same offset automatically; PubMed's count and page payload are inconsistent."
                            if stalled
                            else None
                        ),
                        "enrichment_complete": True,
                        "sort_scope": "current PubMed relevance page",
                    },
                }

            # Batch iCite in chunks of 100
            all_pubs = []
            for i in range(0, len(pmids), 100):
                chunk = pmids[i : i + 100]
                all_pubs.extend(self._fetch_icite(chunk))

            # Sort by citation_count descending
            all_pubs.sort(key=lambda p: p.get("citation_count", 0), reverse=True)

            # Trim to requested limit
            all_pubs = all_pubs[:limit]
            returned_pmids = {str(pub.get("pmid")) for pub in all_pubs}
            missing_pmids = [pmid for pmid in pmids if str(pmid) not in returned_pmids]
            if total_results is not None:
                has_more = offset + len(pmids) < total_results
            else:
                has_more = len(pmids) == limit

            return {
                "status": "success",
                "data": all_pubs,
                "metadata": {
                    "query": query,
                    "returned": len(all_pubs),
                    "pubmed_records_requested": len(pmids),
                    "total_results": total_results,
                    "offset": offset,
                    "limit": limit,
                    "has_more": has_more,
                    "next_offset": offset + len(pmids) if has_more else None,
                    "pagination_stalled": False,
                    "truncated": offset > 0 or has_more,
                    "result_set_complete": bool(
                        total_results is not None
                        and offset == 0
                        and len(pmids) == total_results
                        and not missing_pmids
                    ),
                    "enrichment_complete": not missing_pmids,
                    "missing_icite_pmids": missing_pmids,
                    "sort_scope": "current PubMed relevance page",
                },
            }

        except Exception as e:
            return {"status": "error", "error": f"iCite search error: {e}"}
