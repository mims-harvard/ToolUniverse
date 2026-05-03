"""
ORCID Researcher Identity Tool

Provides access to the ORCID Public API v3.0 for querying researcher profiles,
publications, affiliations, and employment information.

API: https://pub.orcid.org/v3.0/
No authentication required for public data. Respects 24 req/s rate limit.
"""

import requests
from typing import Dict, Any, Optional
from .base_tool import BaseTool
from .tool_registry import register_tool

ORCID_BASE_URL = "https://pub.orcid.org/v3.0"
ORCID_HEADERS = {
    "Accept": "application/json",
    "User-Agent": "ToolUniverse/1.0 (research tool)",
}


@register_tool("ORCIDTool")
class ORCIDTool(BaseTool):
    """
    Tool for querying the ORCID Public API.

    Provides access to:
    - Researcher profiles and biographical data
    - Publication works
    - Search across all ORCID records
    - Employment and affiliation history
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.parameter = tool_config.get("parameter", {})
        self.required = self.parameter.get("required", [])

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        operation = arguments.get("operation")
        if not operation:
            return {"status": "error", "error": "Missing required parameter: operation"}

        operation_handlers = {
            "get_profile": self._get_profile,
            "get_works": self._get_works,
            "search_researchers": self._search_researchers,
            "get_employments": self._get_employments,
        }

        handler = operation_handlers.get(operation)
        if not handler:
            return {
                "status": "error",
                "error": f"Unknown operation: {operation}",
                "available_operations": list(operation_handlers.keys()),
            }

        try:
            return handler(arguments)
        except requests.exceptions.Timeout:
            return {"status": "error", "error": "ORCID API request timed out"}
        except requests.exceptions.ConnectionError:
            return {"status": "error", "error": "Failed to connect to ORCID API"}
        except Exception as e:
            return {"status": "error", "error": f"Operation failed: {str(e)}"}

    def _make_request(self, path: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        url = f"{ORCID_BASE_URL}/{path}"
        response = requests.get(
            url, headers=ORCID_HEADERS, params=params or {}, timeout=30
        )
        if response.status_code == 200:
            return {"ok": True, "data": response.json()}
        elif response.status_code == 404:
            return {"ok": False, "error": "ORCID record not found", "detail": path}
        else:
            return {
                "ok": False,
                "error": f"API request failed with status {response.status_code}",
                "detail": response.text[:500],
            }

    def _get_profile(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        orcid = arguments.get("orcid")
        if not orcid:
            return {"status": "error", "error": "orcid is required"}

        result = self._make_request(f"{orcid}/record")
        if not result["ok"]:
            return {
                "status": "error",
                "error": result["error"],
                "detail": result.get("detail", ""),
            }

        data = result["data"]
        person = data.get("person", {})
        activities = data.get("activities-summary", {})

        return {
            "status": "success",
            "data": {
                "orcid": orcid,
                "name": person.get("name", {}),
                "biography": person.get("biography", {}),
                "emails": person.get("emails", {}),
                "keywords": person.get("keywords", {}),
                "urls": person.get("researcher-urls", {}),
                "works_count": len(activities.get("works", {}).get("group", [])),
                "employments_count": len(
                    activities.get("employments", {}).get("affiliation-group", [])
                ),
            },
        }

    def _get_works(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        orcid = arguments.get("orcid")
        if not orcid:
            return {"status": "error", "error": "orcid is required"}

        result = self._make_request(f"{orcid}/works")
        if not result["ok"]:
            return {
                "status": "error",
                "error": result["error"],
                "detail": result.get("detail", ""),
            }

        data = result["data"]
        groups = data.get("group", [])

        works = []
        for group in groups:
            summaries = group.get("work-summary", [])
            if summaries:
                s = summaries[0]
                works.append(
                    {
                        "put_code": s.get("put-code"),
                        "title": s.get("title", {}).get("title", {}).get("value"),
                        "type": s.get("type"),
                        "publication_date": s.get("publication-date"),
                        "journal_title": s.get("journal-title", {}).get("value")
                        if s.get("journal-title")
                        else None,
                        "external_ids": s.get("external-ids", {}).get(
                            "external-id", []
                        ),
                    }
                )

        return {
            "status": "success",
            "data": works,
            "num_works": len(works),
        }

    def _search_researchers(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        query = arguments.get("query")
        if not query:
            return {"status": "error", "error": "query is required"}

        start = arguments.get("start", 0)
        rows = arguments.get("rows", 10)

        params = {"q": query, "start": start, "rows": rows}
        result = self._make_request("search", params)
        if not result["ok"]:
            return {
                "status": "error",
                "error": result["error"],
                "detail": result.get("detail", ""),
            }

        data = result["data"]
        results = data.get("result", [])

        researchers = []
        for r in results:
            orcid_id = r.get("orcid-identifier", {})
            researchers.append(
                {
                    "orcid": orcid_id.get("path"),
                    "uri": orcid_id.get("uri"),
                }
            )

        return {
            "status": "success",
            "data": researchers,
            "num_results": len(researchers),
            "total_found": data.get("num-found", 0),
        }

    def _get_employments(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        orcid = arguments.get("orcid")
        if not orcid:
            return {"status": "error", "error": "orcid is required"}

        result = self._make_request(f"{orcid}/employments")
        if not result["ok"]:
            return {
                "status": "error",
                "error": result["error"],
                "detail": result.get("detail", ""),
            }

        data = result["data"]
        groups = data.get("affiliation-group", [])

        employments = []
        for group in groups:
            summaries = group.get("summaries", [])
            for s in summaries:
                emp = s.get("employment-summary", {})
                employments.append(
                    {
                        "organization": emp.get("organization", {}).get("name"),
                        "department": emp.get("department-name"),
                        "role": emp.get("role-title"),
                        "start_date": emp.get("start-date"),
                        "end_date": emp.get("end-date"),
                        "country": emp.get("organization", {})
                        .get("address", {})
                        .get("country"),
                    }
                )

        return {
            "status": "success",
            "data": employments,
            "num_employments": len(employments),
        }
