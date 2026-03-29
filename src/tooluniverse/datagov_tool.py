"""
Data.gov (CKAN) API tool for ToolUniverse.

Searches the US federal open data catalog (catalog.data.gov) for datasets
from EPA, CDC, Census, NIH, USDA, NOAA, and 100+ other federal agencies.

API Documentation: https://catalog.data.gov/api/3
"""

import requests
from .base_tool import BaseTool
from .tool_registry import register_tool

DATAGOV_BASE = "https://catalog.data.gov/api/3/action/package_search"


@register_tool("DataGovTool")
class DataGovTool(BaseTool):
    """Search US federal open data catalog (Data.gov) for datasets."""

    def run(self, arguments=None):
        arguments = arguments or {}
        query = arguments.get("query", "").strip()
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

        params = {"q": query, "rows": rows}
        if organization:
            params["fq"] = f"organization:{organization}"

        try:
            resp = requests.get(DATAGOV_BASE, params=params, timeout=30)
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

        if not body.get("success"):
            return {
                "status": "error",
                "error": {
                    "message": "Data.gov API returned an error",
                    "details": str(body.get("error", "Unknown error")),
                },
            }

        result = body.get("result", {})
        datasets = []
        for pkg in result.get("results", []):
            org = pkg.get("organization") or {}
            resources = []
            for res in (pkg.get("resources") or [])[:10]:
                resources.append(
                    {
                        "name": res.get("name"),
                        "url": res.get("url"),
                        "format": res.get("format") or None,
                        "description": res.get("description") or None,
                    }
                )
            datasets.append(
                {
                    "title": pkg.get("title", ""),
                    "description": (pkg.get("notes") or "")[:500] or None,
                    "organization": org.get("name"),
                    "organization_title": org.get("title"),
                    "metadata_modified": pkg.get("metadata_modified"),
                    "tags": [t.get("name", "") for t in (pkg.get("tags") or [])],
                    "resources": resources,
                    "url": pkg.get("url") or None,
                }
            )

        return {
            "status": "success",
            "data": {
                "query": query,
                "organization": organization,
                "total_count": result.get("count", 0),
                "returned": len(datasets),
                "datasets": datasets,
            },
            "metadata": {
                "source": "Data.gov (CKAN)",
                "api": DATAGOV_BASE,
            },
        }
