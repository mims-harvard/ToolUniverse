# dhs_program_tool.py
"""
DHS Program (Demographic and Health Surveys) tool for ToolUniverse.

The DHS Program has run nationally representative household health surveys
across ~90 low- and middle-income countries since 1984: fertility,
maternal and child mortality, nutrition, immunization, and HIV indicators,
each broken down by subnational region, wealth quintile, education, and
urban/rural residence. ToolUniverse's existing WHO GHO tools cover
country-level aggregates; DHS is the underlying subnational survey data
that GHO's own figures are often built from, and corrects a known
LMIC skew in what ToolUniverse otherwise covers.

The indicator catalog's own `search` parameter is silently ignored: a
query and no query at all return the identical RecordCount (4,655),
confirmed by direct comparison. The full catalog fetches in under a
second, so this tool caches it once per process and filters client-side
instead, the same workaround used for MediaDive and M-CSA.

API: https://api.dhsprogram.com/rest/dhs
No authentication required for standard indicator queries.
"""

import threading
from typing import Any, Dict, List, Optional

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

DHS_BASE_URL = "https://api.dhsprogram.com/rest/dhs"
_INDICATOR_CATALOG_PAGE_SIZE = 5000


class _IndicatorCatalogue:
    """Lazily fetches and caches the full DHS indicator catalog."""

    def __init__(self):
        self._rows: Optional[List[Dict[str, Any]]] = None
        self._lock = threading.Lock()

    def rows(self, timeout: int) -> List[Dict[str, Any]]:
        if self._rows is None:
            with self._lock:
                if self._rows is None:
                    response = requests.get(
                        f"{DHS_BASE_URL}/indicators",
                        params={"perPage": _INDICATOR_CATALOG_PAGE_SIZE},
                        timeout=timeout,
                    )
                    response.raise_for_status()
                    self._rows = response.json().get("Data") or []
        return self._rows


@register_tool("DHSProgramTool")
class DHSProgramTool(BaseTool):
    """
    Tool for querying the DHS Program's household health survey data.

    Supports searching the indicator catalog by keyword, and querying
    survey results by country, indicator, and year range.

    No authentication required.
    """

    _indicators = _IndicatorCatalogue()

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 45)
        self.operation = tool_config.get("fields", {}).get(
            "operation", "search_indicators"
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the DHS Program lookup."""
        try:
            if self.operation == "search_indicators":
                return self._search_indicators(arguments)
            if self.operation == "get_data":
                return self._get_data(arguments)
            return {
                "status": "error",
                "error": f"Unknown operation: {self.operation}",
            }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"DHS Program request timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to the DHS Program API. Check network.",
            }
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code if e.response is not None else "unknown"
            return {
                "status": "error",
                "error": f"DHS Program API returned HTTP {code}",
            }
        except ValueError:
            return {
                "status": "error",
                "error": "DHS Program API returned a non-JSON response",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Error querying DHS Program API: {str(e)}",
            }

    def _search_indicators(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search the DHS indicator catalog by keyword."""
        query = (arguments.get("query") or "").strip()
        if not query:
            return {
                "status": "error",
                "error": "query is required, e.g. 'total fertility rate' or "
                "'child immunization'.",
            }

        limit = arguments.get("limit")
        if not isinstance(limit, int) or limit <= 0:
            limit = 25
        limit = min(limit, 100)

        wanted = query.lower()
        catalog = self._indicators.rows(self.timeout)
        matches = [
            i
            for i in catalog
            if wanted in (i.get("Label") or "").lower()
            or wanted in (i.get("Definition") or "").lower()
        ]

        if not matches:
            return {
                "status": "error",
                "error": f"No DHS indicators matching '{query}' in the "
                f"{len(catalog)}-indicator catalog.",
            }

        rows = [
            {
                "indicator_id": i.get("IndicatorId"),
                "label": i.get("Label"),
                "definition": i.get("Definition"),
                "category": i.get("Level1"),
                "subcategory": i.get("Level2"),
                "measurement_type": i.get("MeasurementType"),
                "denominator": i.get("Denominator"),
            }
            for i in matches[:limit]
        ]

        return {
            "status": "success",
            "data": rows,
            "metadata": {
                "query": query,
                "matches_found": len(matches),
                "returned": len(rows),
                "note": "indicator_id is what get_data expects.",
                "source": "The DHS Program",
            },
        }

    def _get_data(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Query survey results for an indicator, optionally by country/year."""
        indicator_id = (arguments.get("indicator_id") or "").strip()
        if not indicator_id:
            return {
                "status": "error",
                "error": "indicator_id is required, e.g. 'FE_FRTR_W_TFR' "
                "(total fertility rate). Use search_indicators to find one.",
            }

        limit = arguments.get("limit")
        if not isinstance(limit, int) or limit <= 0:
            limit = 25
        limit = min(limit, 100)

        params: Dict[str, Any] = {"indicatorIds": indicator_id, "perpage": limit}
        country_code = (arguments.get("country_code") or "").strip()
        if country_code:
            params["countryIds"] = country_code.upper()

        year_start = arguments.get("survey_year_start")
        if isinstance(year_start, int):
            params["surveyYearStart"] = year_start
        year_end = arguments.get("survey_year_end")
        if isinstance(year_end, int):
            params["surveyYearEnd"] = year_end

        response = requests.get(
            f"{DHS_BASE_URL}/data", params=params, timeout=self.timeout
        )
        response.raise_for_status()
        payload = response.json()
        results = payload.get("Data") or []

        if not results:
            return {
                "status": "error",
                "error": f"No DHS data for indicator '{indicator_id}'"
                + (f" in country '{country_code}'" if country_code else "")
                + ".",
            }

        rows = [
            {
                "country": r.get("CountryName"),
                "survey_id": r.get("SurveyId"),
                "survey_year": r.get("SurveyYearLabel"),
                "indicator": r.get("Indicator"),
                "value": r.get("Value"),
                "characteristic": r.get("CharacteristicLabel"),
                "denominator_weighted": r.get("DenominatorWeighted") or None,
            }
            for r in results
        ]

        return {
            "status": "success",
            "data": rows,
            "metadata": {
                "indicator_id": indicator_id,
                "country_code": country_code or None,
                "total_matching": payload.get("RecordCount"),
                "returned": len(rows),
                "note": "characteristic breaks results down by subgroup "
                "(e.g. wealth quintile, region, education); 'Total' is the "
                "national aggregate.",
                "source": "The DHS Program",
            },
        }
