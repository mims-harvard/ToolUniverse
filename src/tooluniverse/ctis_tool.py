"""
EU CTIS tools for ToolUniverse — Clinical Trials Information System.

CTIS is the EU clinical-trials register under the Clinical Trials Regulation
(applies since 2022), the EU counterpart to ClinicalTrials.gov. These tools
search and retrieve authorized trials.

API: https://euclinicaltrials.eu/ctis-public-api  (public, no authentication, JSON)
  - POST /search           (body: pagination + searchCriteria)
  - GET  /retrieve/{ctNumber}
"""

from typing import Any, Dict

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

CTIS_BASE = "https://euclinicaltrials.eu/ctis-public-api"
# CTIS rejects non-browser user agents on some paths.
_HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (compatible; ToolUniverse/1.0)",
}


@register_tool("CTISSearchTrialsTool")
class CTISSearchTrialsTool(BaseTool):
    """Search EU CTIS clinical trials by free text."""

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("fields", {}).get("timeout", 30)

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        query = (arguments.get("query") or "").strip()
        if not query:
            return {
                "status": "error",
                "error": "'query' is required (e.g. 'breast cancer')",
            }
        try:
            size = int(arguments.get("limit") or 10)
        except (TypeError, ValueError):
            size = 10
        size = max(1, min(size, 100))
        try:
            page = int(arguments.get("page") or 1)
        except (TypeError, ValueError):
            page = 1

        body = {
            "pagination": {"page": max(1, page), "size": size},
            "searchCriteria": {"containAll": query},
        }
        try:
            resp = requests.post(
                f"{CTIS_BASE}/search", json=body, headers=_HEADERS, timeout=self.timeout
            )
            resp.raise_for_status()
            payload = resp.json()
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"CTIS request timed out after {self.timeout}s",
            }
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"CTIS request failed: {e}"}
        except ValueError:
            return {"status": "error", "error": "CTIS returned a non-JSON response"}

        items = payload.get("data", []) if isinstance(payload, dict) else []
        pag = payload.get("pagination", {}) if isinstance(payload, dict) else {}
        trials = [
            {
                "ct_number": it.get("ctNumber"),
                "title": it.get("ctTitle") or it.get("shortTitle"),
                "status": it.get("ctStatus"),
                "conditions": it.get("conditions"),
                "therapeutic_areas": it.get("therapeuticAreas"),
                "phase": it.get("trialPhase"),
                "sponsor": it.get("sponsor"),
                "sponsor_type": it.get("sponsorType"),
                "countries": it.get("trialCountries"),
                "total_enrolled": it.get("totalNumberEnrolled"),
                "start_date_eu": it.get("startDateEU"),
                "last_updated": it.get("lastUpdated"),
            }
            for it in items
            if isinstance(it, dict)
        ]
        return {
            "status": "success",
            "data": trials,
            "metadata": {
                "total_records": pag.get("totalRecords"),
                "page": pag.get("currentPage"),
                "total_pages": pag.get("totalPages"),
                "returned": len(trials),
                "query": query,
                "source": "EU CTIS",
            },
        }


@register_tool("CTISGetTrialTool")
class CTISGetTrialTool(BaseTool):
    """Retrieve a single EU CTIS trial by CT number."""

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("fields", {}).get("timeout", 30)

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        ct_number = (arguments.get("ct_number") or "").strip()
        if not ct_number:
            return {
                "status": "error",
                "error": "'ct_number' is required (e.g. '2022-503001-38-01')",
            }

        try:
            resp = requests.get(
                f"{CTIS_BASE}/retrieve/{ct_number}",
                headers=_HEADERS,
                timeout=self.timeout,
            )
            if resp.status_code == 404:
                return {
                    "status": "success",
                    "data": {},
                    "metadata": {
                        "query_ct_number": ct_number,
                        "note": f"No CTIS trial found for '{ct_number}'.",
                    },
                }
            resp.raise_for_status()
            rec = resp.json()
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"CTIS request timed out after {self.timeout}s",
            }
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"CTIS request failed: {e}"}
        except ValueError:
            return {"status": "error", "error": "CTIS returned a non-JSON response"}

        if not isinstance(rec, dict) or not rec:
            return {
                "status": "success",
                "data": {},
                "metadata": {"query_ct_number": ct_number},
            }
        return {
            "status": "success",
            "data": {
                "ct_number": rec.get("ctNumber"),
                "status_code": rec.get("ctPublicStatusCode"),
                "start_date_eu": rec.get("startDateEU"),
                "decision_date": rec.get("decisionDate"),
                "publish_date": rec.get("publishDate"),
                "trial_region": rec.get("trialRegion"),
                "authorized_application": rec.get("authorizedApplication"),
                "events": rec.get("events"),
                "results": rec.get("results"),
            },
            "metadata": {"query_ct_number": ct_number, "source": "EU CTIS"},
        }
