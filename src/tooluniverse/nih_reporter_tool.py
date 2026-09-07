# nih_reporter_tool.py
"""
NIH RePORTER tool for ToolUniverse.

RePORTER is NIH's public database of funded research: ~3 million grants
since 1985 with title, abstract, funding amount, institute, principal
investigator, and institution. ToolUniverse has no funding-landscape layer
today, only the science itself (papers, structures, sequences).

The API's text search parameter is `advanced_text_search` (a differently
named, differently structured sibling of the more obviously named
`text_search`, which is silently ignored and matches every record).

API: https://api.reporter.nih.gov/v2/projects/search
No authentication required.
"""

from typing import Any, Dict, List

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

REPORTER_URL = "https://api.reporter.nih.gov/v2/projects/search"

_SEARCH_FIELDS = "projecttitle,terms,abstracttext"

_INCLUDE_FIELDS = [
    "ProjectTitle",
    "ProjectNum",
    "ApplId",
    "FiscalYear",
    "AwardAmount",
    "Organization",
    "ContactPiName",
    "AgencyIcAdmin",
    "ProjectStartDate",
    "ProjectEndDate",
    "AbstractText",
]


def _summarize(project: Dict[str, Any]) -> Dict[str, Any]:
    """Condense one RePORTER project record."""
    org = project.get("organization") or {}
    agency = project.get("agency_ic_admin") or {}
    return {
        "project_num": project.get("project_num"),
        "appl_id": project.get("appl_id"),
        "title": project.get("project_title"),
        "principal_investigator": project.get("contact_pi_name"),
        "organization": org.get("org_name"),
        "funding_institute": agency.get("name"),
        "fiscal_year": project.get("fiscal_year"),
        "award_amount": project.get("award_amount"),
        "project_start_date": project.get("project_start_date"),
        "project_end_date": project.get("project_end_date"),
        "abstract": project.get("abstract_text"),
    }


@register_tool("NIHReporterTool")
class NIHReporterTool(BaseTool):
    """
    Tool for querying NIH RePORTER, the public database of NIH-funded
    research projects.

    Supports full-text search over titles, abstracts, and terms with
    optional fiscal-year and organization filters, and direct lookup of one
    project by its project number or application id.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 45)
        self.operation = tool_config.get("fields", {}).get(
            "operation", "search_projects"
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the RePORTER lookup."""
        try:
            if self.operation == "search_projects":
                return self._search_projects(arguments)
            if self.operation == "get_project":
                return self._get_project(arguments)
            return {
                "status": "error",
                "error": f"Unknown operation: {self.operation}",
            }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"RePORTER request timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to NIH RePORTER. Check network.",
            }
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code if e.response is not None else "unknown"
            return {"status": "error", "error": f"RePORTER returned HTTP {code}"}
        except ValueError:
            return {
                "status": "error",
                "error": "RePORTER returned a non-JSON response",
            }
        except Exception as e:
            return {"status": "error", "error": f"Error querying RePORTER: {str(e)}"}

    def _search_projects(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Full-text search over NIH-funded project titles/abstracts/terms."""
        query = (arguments.get("query") or "").strip()
        if not query:
            return {
                "status": "error",
                "error": "query is required, e.g. 'CRISPR gene editing'.",
            }

        limit = arguments.get("limit")
        if not isinstance(limit, int) or limit <= 0:
            limit = 25
        limit = min(limit, 100)

        criteria: Dict[str, Any] = {
            "advanced_text_search": {
                "operator": "and",
                "search_field": _SEARCH_FIELDS,
                "search_text": query,
            }
        }

        fiscal_year = arguments.get("fiscal_year")
        if isinstance(fiscal_year, int):
            criteria["fiscal_years"] = [fiscal_year]

        organization = (arguments.get("organization") or "").strip()
        if organization:
            criteria["org_names"] = [organization]

        response = requests.post(
            REPORTER_URL,
            json={
                "criteria": criteria,
                "include_fields": _INCLUDE_FIELDS,
                "limit": limit,
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        results = payload.get("results") or []

        if not results:
            return {
                "status": "error",
                "error": f"No NIH-funded projects matching '{query}'"
                + (f" in fiscal year {fiscal_year}" if fiscal_year else "")
                + (f" at '{organization}'" if organization else "")
                + ".",
            }

        rows = [_summarize(p) for p in results]

        return {
            "status": "success",
            "data": rows,
            "metadata": {
                "query": query,
                "fiscal_year": fiscal_year,
                "organization": organization or None,
                "total_matching": (payload.get("meta") or {}).get("total"),
                "returned": len(rows),
                "note": "project_num or appl_id can be used with get_project "
                "for the full record.",
                "source": "NIH RePORTER",
            },
        }

    def _get_project(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch one project by its project number or application id."""
        project_num = (arguments.get("project_num") or "").strip()
        appl_id = arguments.get("appl_id")

        if not project_num and not appl_id:
            return {
                "status": "error",
                "error": "Provide either project_num (e.g. '5R21EB036298-03') "
                "or appl_id (e.g. 11326711).",
            }

        criteria: Dict[str, Any] = {}
        if project_num:
            criteria["project_nums"] = [project_num]
        elif isinstance(appl_id, int):
            criteria["appl_ids"] = [appl_id]

        response = requests.post(
            REPORTER_URL,
            json={
                "criteria": criteria,
                "include_fields": _INCLUDE_FIELDS,
                "limit": 1,
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        results = payload.get("results") or []

        if not results:
            identifier = project_num or appl_id
            return {
                "status": "error",
                "error": f"No NIH RePORTER project found for '{identifier}'.",
            }

        return {
            "status": "success",
            "data": _summarize(results[0]),
            "metadata": {
                "project_num": project_num or None,
                "appl_id": appl_id,
                "source": "NIH RePORTER",
            },
        }
