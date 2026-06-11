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


# Maps friendly argument names to CTIS searchCriteria keys. List-valued
# CTIS filters take arrays of string codes; the rest take scalars.
_CTIS_LIST_FILTERS = {
    "status": "status",
    "trial_phase_code": "trialPhaseCode",
    "age_group_code": "ageGroupCode",
    "gender_code": "genderCode",
    "therapeutic_area": "therapeuticArea",
    "msc": "msc",
    "country": "msc",
    "trial_region_code": "trialRegionCode",
    "sponsor_type_code": "sponsorTypeCode",
}
_CTIS_SCALAR_FILTERS = {
    "medical_condition": "medicalCondition",
    "sponsor": "sponsor",
    "has_study_results": "hasStudyResults",
    "sort_by": "sortBy",
}


def _pagination(arguments: Dict[str, Any]) -> Dict[str, int]:
    """Build a CTIS pagination block from limit/page arguments (1<=size<=100)."""
    try:
        size = int(arguments.get("limit") or 10)
    except (TypeError, ValueError):
        size = 10
    try:
        page = int(arguments.get("page") or 1)
    except (TypeError, ValueError):
        page = 1
    return {"page": max(1, page), "size": max(1, min(size, 100))}


def _coerce_list(value: Any) -> list:
    """Normalize a filter value to a list (CTIS list filters expect arrays)."""
    if value is None:
        return []
    if isinstance(value, list):
        return [v for v in value if v not in (None, "")]
    return [value]


def _build_search_criteria(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Assemble a CTIS searchCriteria dict from filtered-search arguments."""
    criteria: Dict[str, Any] = {}
    contain_all = (arguments.get("query") or arguments.get("contain_all") or "").strip()
    if contain_all:
        criteria["containAll"] = contain_all

    for arg_name, api_key in _CTIS_SCALAR_FILTERS.items():
        val = arguments.get(arg_name)
        if val is None:
            continue
        if isinstance(val, str) and not val.strip():
            continue
        criteria[api_key] = val

    for arg_name, api_key in _CTIS_LIST_FILTERS.items():
        items = _coerce_list(arguments.get(arg_name))
        if not items:
            continue
        # status codes are integers in the CTIS API; other filters are strings.
        if api_key == "status":
            coerced = []
            for it in items:
                try:
                    coerced.append(int(it))
                except (TypeError, ValueError):
                    coerced.append(it)
            criteria.setdefault(api_key, [])
            criteria[api_key].extend(coerced)
        else:
            criteria.setdefault(api_key, [])
            criteria[api_key].extend(str(it) for it in items)
    return criteria


@register_tool("CTISSearchTrialsTool")
class CTISSearchTrialsTool(BaseTool):
    """Search EU CTIS clinical trials by free text or structured filters.

    Behavior is selected by the tool's configured ``name``: the
    ``CTIS_search_trials_filtered`` entry assembles a structured
    ``searchCriteria`` body from filter arguments (status, medical condition,
    phase, age group, gender, has-results, sponsor, country/MSC, etc.), while
    every other entry performs the original ``containAll`` free-text search.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("fields", {}).get("timeout", 30)
        self._tool_name = (tool_config.get("name") or "").strip()

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if self._tool_name == "CTIS_search_trials_filtered":
            return self._run_filtered(arguments)
        return self._run_freetext(arguments)

    def _run_filtered(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        criteria = _build_search_criteria(arguments)
        if not criteria:
            return {
                "status": "error",
                "error": (
                    "At least one search filter is required (e.g. "
                    "medical_condition, query/contain_all, status, "
                    "trial_phase_code, age_group_code, sponsor)."
                ),
            }
        return self._search(arguments, criteria, {"search_criteria": criteria})

    def _run_freetext(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        query = (arguments.get("query") or "").strip()
        if not query:
            return {
                "status": "error",
                "error": "'query' is required (e.g. 'breast cancer')",
            }
        return self._search(arguments, {"containAll": query}, {"query": query})

    def _search(
        self,
        arguments: Dict[str, Any],
        criteria: Dict[str, Any],
        extra_meta: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Run a CTIS search with the given criteria and format the results."""
        body = {
            "pagination": _pagination(arguments),
            "searchCriteria": criteria,
        }
        result = self._post_search(body)
        if isinstance(result, dict) and result.get("status") == "error":
            return result
        return self._format_results(result, extra_meta)

    def _post_search(self, body: Dict[str, Any]) -> Any:
        """POST to the CTIS search endpoint. Returns parsed JSON or an error dict."""
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
        return payload

    @staticmethod
    def _format_results(payload: Any, extra_meta: Dict[str, Any]) -> Dict[str, Any]:
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
                "age_group": it.get("ageGroup"),
                "gender": it.get("gender"),
                "trial_region": it.get("trialRegion"),
                "total_enrolled": it.get("totalNumberEnrolled"),
                "results_first_received": it.get("resultsFirstReceived"),
                "start_date_eu": it.get("startDateEU"),
                "last_updated": it.get("lastUpdated"),
            }
            for it in items
            if isinstance(it, dict)
        ]
        metadata = {
            "total_records": pag.get("totalRecords"),
            "page": pag.get("currentPage"),
            "total_pages": pag.get("totalPages"),
            "returned": len(trials),
            "source": "EU CTIS",
        }
        metadata.update(extra_meta)
        return {"status": "success", "data": trials, "metadata": metadata}


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
