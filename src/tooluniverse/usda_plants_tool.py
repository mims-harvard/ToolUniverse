"""
USDA PLANTS tools for ToolUniverse — US plant taxonomy & traits.

The USDA PLANTS Database provides authoritative taxonomy, growth habit, duration,
native status, and morphological/physiological characteristics for plants of the
U.S. and its territories. These tools fetch a plant profile and its characteristics.

API: https://plantsservices.sc.egov.usda.gov/api  (public, no authentication, JSON)
"""

from typing import Any, Dict, Optional

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

USDA_PLANTS_BASE = "https://plantsservices.sc.egov.usda.gov/api"


def _fetch_profile(symbol: str, timeout: int) -> Optional[Dict[str, Any]]:
    resp = requests.get(
        f"{USDA_PLANTS_BASE}/PlantProfile",
        params={"symbol": symbol},
        headers={"Accept": "application/json"},
        timeout=timeout,
    )
    resp.raise_for_status()
    data = resp.json()
    return data if isinstance(data, dict) and data.get("Id") else None


class _USDAPlantsBase(BaseTool):
    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("fields", {}).get("timeout", 30)


@register_tool("USDAPlantsProfileTool")
class USDAPlantsProfileTool(_USDAPlantsBase):
    """Get a USDA PLANTS profile (taxonomy, habit, duration, native status) by symbol."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        symbol = (arguments.get("symbol") or "").strip().upper()
        if not symbol:
            return {
                "status": "error",
                "error": "'symbol' is required (USDA PLANTS symbol, e.g. 'ABBA')",
            }

        try:
            profile = _fetch_profile(symbol, self.timeout)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"USDA PLANTS request timed out after {self.timeout}s",
            }
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"USDA PLANTS request failed: {e}"}
        except ValueError:
            return {
                "status": "error",
                "error": "USDA PLANTS returned a non-JSON response",
            }

        if profile is None:
            return {
                "status": "success",
                "data": {},
                "metadata": {
                    "query_symbol": symbol,
                    "note": f"No USDA PLANTS profile for '{symbol}'.",
                },
            }
        return {
            "status": "success",
            "data": {
                "id": profile.get("Id"),
                "symbol": profile.get("Symbol"),
                "scientific_name": profile.get("ScientificNameWithoutAuthor")
                or profile.get("ScientificName"),
                "common_name": profile.get("CommonName"),
                "group": profile.get("GroupName") or profile.get("Group"),
                "rank": profile.get("Rank"),
                "duration": profile.get("Durations") or profile.get("Duration"),
                "growth_habits": profile.get("GrowthHabits"),
                "native_statuses": profile.get("NativeStatuses"),
                "synonyms": profile.get("Synonyms", [])
                if profile.get("HasSynonyms")
                else [],
                "fips_distribution": profile.get("FipsCode"),
            },
            "metadata": {"query_symbol": symbol, "source": "USDA PLANTS"},
        }


@register_tool("USDAPlantsCharacteristicsTool")
class USDAPlantsCharacteristicsTool(_USDAPlantsBase):
    """Get USDA PLANTS morphology/physiology/growth characteristics for a plant by symbol."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        symbol = (arguments.get("symbol") or "").strip().upper()
        if not symbol:
            return {
                "status": "error",
                "error": "'symbol' is required (USDA PLANTS symbol, e.g. 'ABBA')",
            }

        try:
            profile = _fetch_profile(symbol, self.timeout)
            if profile is None:
                return {
                    "status": "success",
                    "data": [],
                    "metadata": {
                        "query_symbol": symbol,
                        "note": f"No USDA PLANTS profile for '{symbol}'.",
                    },
                }
            resp = requests.get(
                f"{USDA_PLANTS_BASE}/PlantCharacteristics/{profile['Id']}",
                headers={"Accept": "application/json"},
                timeout=self.timeout,
            )
            resp.raise_for_status()
            chars = resp.json()
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"USDA PLANTS request timed out after {self.timeout}s",
            }
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"USDA PLANTS request failed: {e}"}
        except ValueError:
            return {
                "status": "error",
                "error": "USDA PLANTS returned a non-JSON response",
            }

        if not isinstance(chars, list):
            chars = []
        results = [
            {
                "name": c.get("PlantCharacteristicName"),
                "value": c.get("PlantCharacteristicValue"),
                "category": c.get("PlantCharacteristicCategory"),
            }
            for c in chars
            if isinstance(c, dict)
        ]
        return {
            "status": "success",
            "data": results,
            "metadata": {
                "total_results": len(results),
                "query_symbol": symbol,
                "plant_id": profile["Id"],
                "source": "USDA PLANTS",
            },
        }
