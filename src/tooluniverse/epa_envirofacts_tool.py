"""
EPA Envirofacts tools for ToolUniverse — US environmental facility data.

The U.S. EPA Envirofacts REST service exposes regulated-facility data, including
the Toxics Release Inventory (TRI) and the Facility Registry Service (FRS). These
tools query the two validated facility tables by state (and optional city).

API: https://data.epa.gov/efservice/{table}/{col}/{val}.../rows/{a}:{b}/JSON
     (public, no authentication, US Gov public domain)
"""

from typing import Any, Dict
from urllib.parse import quote

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

EFSERVICE = "https://data.epa.gov/efservice"


class _EnvirofactsBase(BaseTool):
    table = ""
    state_col = ""
    city_col = "city_name"

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("fields", {}).get("timeout", 30)

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        state = (arguments.get("state") or "").strip().upper()
        if not state:
            return {
                "status": "error",
                "error": "'state' (2-letter code, e.g. 'CA') is required",
            }
        city = (arguments.get("city") or "").strip()
        try:
            limit = max(1, min(int(arguments.get("limit") or 10), 100))
        except (TypeError, ValueError):
            limit = 10

        path = f"{EFSERVICE}/{self.table}/{self.state_col}/{quote(state)}"
        if city:
            path += f"/{self.city_col}/{quote(city.upper())}"
        path += f"/rows/0:{limit - 1}/JSON"

        try:
            resp = requests.get(
                path, headers={"Accept": "application/json"}, timeout=self.timeout
            )
            resp.raise_for_status()
            rows = resp.json()
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"EPA Envirofacts request timed out after {self.timeout}s",
            }
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"EPA Envirofacts request failed: {e}"}
        except ValueError:
            return {
                "status": "error",
                "error": "EPA Envirofacts returned a non-JSON response",
            }

        if not isinstance(rows, list):
            rows = []
        return {
            "status": "success",
            "data": [self._summarize(r) for r in rows if isinstance(r, dict)],
            "metadata": {
                "total_results": len(rows),
                "table": self.table,
                "query": {"state": state, "city": city or None},
                "source": "EPA Envirofacts",
            },
        }

    @staticmethod
    def _summarize(
        r: Dict[str, Any],
    ) -> Dict[str, Any]:  # pragma: no cover - overridden
        return r


@register_tool("EPATRIFacilitiesTool")
class EPATRIFacilitiesTool(_EnvirofactsBase):
    """Search EPA Toxics Release Inventory (TRI) facilities by state/city."""

    table = "tri_facility"
    state_col = "state_abbr"

    @staticmethod
    def _summarize(r: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "tri_facility_id": r.get("tri_facility_id"),
            "facility_name": r.get("facility_name"),
            "street_address": r.get("street_address"),
            "city": r.get("city_name"),
            "county": r.get("county_name"),
            "state": r.get("state_abbr"),
            "zip_code": r.get("zip_code"),
            "epa_region": r.get("region"),
            "closed": r.get("fac_closed_ind"),
        }


@register_tool("EPAFRSFacilitiesTool")
class EPAFRSFacilitiesTool(_EnvirofactsBase):
    """Search EPA Facility Registry Service (FRS) facility sites by state/city."""

    table = "frs_facility_site"
    state_col = "state_code"
    city_col = "city_name"

    @staticmethod
    def _summarize(r: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "facility_name": r.get("std_name") or r.get("std_base_name"),
            "address": r.get("std_full_address") or r.get("location_address"),
            "city": r.get("std_city_name") or r.get("city_name"),
            "state": r.get("state_name"),
            "registry_id": r.get("parent_registry_id"),
            "federal_facility": r.get("federal_facility_code"),
            "tribal_land": r.get("tribal_land_name"),
        }
