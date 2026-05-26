"""
Data.gov search tool for ToolUniverse.

Searches the US federal open data catalog (catalog.data.gov) for datasets
from EPA, CDC, Census, NIH, USDA, NOAA, and 100+ other federal agencies.

The legacy CKAN /api/3/action/package_search endpoint was retired in 2025;
the catalog now serves a Solr-backed JSON search at /search?_format=json
with different param names (`_q` instead of `q`, `organization` slug
instead of CKAN `fq` filter). This tool talks to the new endpoint and
normalises the response into the same {datasets:[{title, description,
organization, ...}], total_count, returned} shape the previous CKAN
version emitted, so callers don't see a behavioural change.
"""

import requests
from .base_tool import BaseTool
from .tool_registry import register_tool

DATAGOV_SEARCH = "https://catalog.data.gov/search"
_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36 ToolUniverse/DataGov"
    ),
    "Accept": "application/json,*/*;q=0.8",
}


@register_tool("DataGovTool")
class DataGovTool(BaseTool):
    """Search US federal open data catalog (Data.gov) for datasets."""

    def run(self, arguments=None):
        arguments = arguments or {}
        query = (arguments.get("query") or "").strip()
        organization = arguments.get("organization")
        rows = max(1, min(int(arguments.get("rows", 10)), 100))

        if not query:
            return {
                "status": "error",
                "error": {
                    "message": "Missing required parameter: query",
                    "details": "Provide a search query string.",
                },
            }

        params = {"_q": query, "_format": "json", "rows": rows}
        if organization:
            # The new endpoint takes the organization *slug* (e.g. 'epa-gov')
            # as a separate query param, not as a CKAN fq filter.
            params["organization"] = organization

        try:
            resp = requests.get(
                DATAGOV_SEARCH, params=params, headers=_BROWSER_HEADERS, timeout=30
            )
            resp.raise_for_status()
            body = resp.json()
        except requests.RequestException as exc:
            return {
                "status": "error",
                "error": {
                    "message": "Data.gov API request failed",
                    "details": str(exc),
                },
            }
        except ValueError as exc:
            return {
                "status": "error",
                "error": {
                    "message": "Data.gov API returned non-JSON response",
                    "details": str(exc),
                },
            }

        results = body.get("results") or []
        datasets = []
        for pkg in results:
            org = pkg.get("organization") or {}
            # The Solr response stores 'distribution_titles' (a flat list of
            # resource titles) — the old CKAN response had a full 'resources'
            # array. Reconstruct a thin resources list from what's available.
            dcat = pkg.get("dcat") or {}
            resources = []
            for dist in (dcat.get("distribution") or [])[:10]:
                if not isinstance(dist, dict):
                    continue
                resources.append(
                    {
                        "name": dist.get("title"),
                        "url": dist.get("accessURL") or dist.get("downloadURL"),
                        "format": dist.get("format") or dist.get("mediaType"),
                        "description": dist.get("description"),
                    }
                )

            datasets.append(
                {
                    "title": pkg.get("title", ""),
                    "description": (pkg.get("description") or "")[:500] or None,
                    "organization": org.get("slug") or org.get("name"),
                    "organization_title": org.get("name"),
                    "metadata_modified": pkg.get("last_harvested_date"),
                    "tags": pkg.get("keyword") or [],
                    "resources": resources,
                    "url": (
                        f"https://catalog.data.gov/dataset/{pkg['slug']}"
                        if pkg.get("slug")
                        else None
                    ),
                }
            )

        return {
            "status": "success",
            "data": {
                "query": query,
                "organization": organization,
                "total_count": len(results),
                "returned": len(datasets),
                "datasets": datasets,
            },
            "metadata": {
                "source": "Data.gov (Solr search)",
                "api": DATAGOV_SEARCH,
            },
        }
