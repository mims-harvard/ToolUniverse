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


def _strip_html(value: Optional[str]) -> Optional[str]:
    """Remove simple HTML tags (e.g. <i>...</i>) USDA wraps scientific names in."""
    if not isinstance(value, str):
        return value
    import re

    return re.sub(r"<[^>]+>", "", value).strip() or None


def _resolve_plant_id(arguments: Dict[str, Any], timeout: int):
    """Resolve a plant to its numeric PLANTS Id.

    Accepts an explicit ``id`` (numeric PLANTS Id), or a ``symbol`` that is
    looked up via the PlantProfile endpoint. Returns ``(plant_id, symbol,
    error_dict)`` where ``error_dict`` is non-None only on failure. A symbol
    with no matching profile returns ``(None, symbol, None)`` so callers can
    emit an empty success.
    """
    raw_id = arguments.get("id") or arguments.get("plant_id")
    if raw_id not in (None, ""):
        try:
            return int(raw_id), None, None
        except (TypeError, ValueError):
            return (
                None,
                None,
                {
                    "status": "error",
                    "error": f"'id' must be a numeric USDA PLANTS Id (got {raw_id!r}).",
                },
            )

    symbol = (arguments.get("symbol") or "").strip().upper()
    if not symbol:
        return (
            None,
            None,
            {
                "status": "error",
                "error": "Provide a USDA PLANTS 'symbol' (e.g. 'TYLA') or a numeric 'id'.",
            },
        )

    try:
        profile = _fetch_profile(symbol, timeout)
    except requests.exceptions.Timeout:
        return (
            None,
            symbol,
            {
                "status": "error",
                "error": f"USDA PLANTS request timed out after {timeout}s",
            },
        )
    except requests.exceptions.RequestException as e:
        return (
            None,
            symbol,
            {"status": "error", "error": f"USDA PLANTS request failed: {e}"},
        )
    except ValueError:
        return (
            None,
            symbol,
            {"status": "error", "error": "USDA PLANTS returned a non-JSON response"},
        )

    if profile is None:
        return None, symbol, None
    return profile.get("Id"), symbol, None


def _fetch_plants_json(path: str, timeout: int):
    """GET a USDA PLANTS sub-endpoint and return ``(parsed_json, error_dict)``."""
    try:
        resp = requests.get(
            f"{USDA_PLANTS_BASE}/{path}",
            headers={"Accept": "application/json"},
            timeout=timeout,
        )
        resp.raise_for_status()
        return resp.json(), None
    except requests.exceptions.Timeout:
        return None, {
            "status": "error",
            "error": f"USDA PLANTS request timed out after {timeout}s",
        }
    except requests.exceptions.RequestException as e:
        return None, {"status": "error", "error": f"USDA PLANTS request failed: {e}"}
    except ValueError:
        return None, {
            "status": "error",
            "error": "USDA PLANTS returned a non-JSON response",
        }


class _USDAPlantsBase(BaseTool):
    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        fields = tool_config.get("fields", {})
        self.timeout = fields.get("timeout", 30)
        self.action = fields.get("action", "profile")


@register_tool("USDAPlantsProfileTool")
class USDAPlantsProfileTool(_USDAPlantsBase):
    """Get a USDA PLANTS profile by symbol, or resolve a plant name to PLANTS symbols.

    The ``search`` action (``fields.action = "search"``) takes a ``searchText`` of a
    scientific/common name or genus and returns matching plants with their Symbol,
    ScientificName, CommonName and Rank — the missing name->symbol resolution step.
    The default ``profile`` action takes a ``symbol`` and returns the full profile.
    """

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if self.action == "search":
            return self._search(arguments)
        if self.action == "wetland":
            return self._wetland(arguments)
        if self.action == "invasive":
            return self._invasive(arguments)
        if self.action == "wildlife":
            return self._wildlife(arguments)
        return self._profile(arguments)

    def _wetland(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        plant_id, symbol, err = _resolve_plant_id(arguments, self.timeout)
        if err is not None:
            return err
        if plant_id is None:
            return {
                "status": "success",
                "data": [],
                "metadata": {
                    "query_symbol": symbol,
                    "note": f"No USDA PLANTS profile for '{symbol}'.",
                },
            }

        raw, err = _fetch_plants_json(f"PlantWetland/{plant_id}", self.timeout)
        if err is not None:
            return err
        if not isinstance(raw, list):
            raw = []

        results = []
        for entry in raw:
            if not isinstance(entry, dict):
                continue
            designations = [
                {
                    "region": d.get("Region"),
                    "sub_region": d.get("SubRegion"),
                    "wetland_code": d.get("WetlandCode"),
                }
                for d in (entry.get("WetlandDesignations") or [])
                if isinstance(d, dict)
            ]
            results.append(
                {
                    "id": entry.get("Id"),
                    "scientific_name": _strip_html(entry.get("ScientificName")),
                    "wetland_designations": designations,
                }
            )

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "total_results": len(results),
                "query_symbol": symbol,
                "plant_id": plant_id,
                "source": "USDA PLANTS",
                "note": "WetlandCode values: OBL=obligate wetland, FACW=facultative wetland, FAC=facultative, FACU=facultative upland, UPL=upland (per USACE region).",
            },
        }

    def _invasive(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        plant_id, symbol, err = _resolve_plant_id(arguments, self.timeout)
        if err is not None:
            return err
        if plant_id is None:
            return {
                "status": "success",
                "data": {"invasive": [], "noxious": []},
                "metadata": {
                    "query_symbol": symbol,
                    "note": f"No USDA PLANTS profile for '{symbol}'.",
                },
            }

        invasive_raw, err = _fetch_plants_json(
            f"PlantInvasiveStatus/{plant_id}", self.timeout
        )
        if err is not None:
            return err
        noxious_raw, err = _fetch_plants_json(
            f"PlantNoxiousStatus/{plant_id}", self.timeout
        )
        if err is not None:
            return err

        def _normalize(rows):
            out = []
            for r in rows if isinstance(rows, list) else []:
                if not isinstance(r, dict):
                    continue
                out.append(
                    {
                        "locality_name": r.get("LocalityName"),
                        "common_names": r.get("CommonNames") or [],
                        "statuses": r.get("InvasiveStatuses")
                        or r.get("NoxiousStatuses")
                        or [],
                    }
                )
            return out

        invasive = _normalize(invasive_raw)
        noxious = _normalize(noxious_raw)

        return {
            "status": "success",
            "data": {"invasive": invasive, "noxious": noxious},
            "metadata": {
                "invasive_count": len(invasive),
                "noxious_count": len(noxious),
                "query_symbol": symbol,
                "plant_id": plant_id,
                "source": "USDA PLANTS",
                "note": "State-by-state invasive listings and federal/state noxious-weed legal statuses.",
            },
        }

    def _wildlife(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        plant_id, symbol, err = _resolve_plant_id(arguments, self.timeout)
        if err is not None:
            return err
        if plant_id is None:
            return {
                "status": "success",
                "data": {},
                "metadata": {
                    "query_symbol": symbol,
                    "note": f"No USDA PLANTS profile for '{symbol}'.",
                },
            }

        raw, err = _fetch_plants_json(f"PlantWildlife/{plant_id}", self.timeout)
        if err is not None:
            return err
        if not isinstance(raw, dict):
            raw = {}

        def _ratings(rows):
            out = []
            for r in rows if isinstance(rows, list) else []:
                if not isinstance(r, dict):
                    continue
                out.append(
                    {
                        "source": r.get("Source"),
                        "large_mammals": r.get("LargeMammals") or None,
                        "small_mammals": r.get("SmallMammals") or None,
                        "water_birds": r.get("WaterBirds") or None,
                        "terrestrial_birds": r.get("TerrestrialBirds") or None,
                    }
                )
            return out

        sources = [
            {
                "author": s.get("AuthorName"),
                "title": s.get("Title"),
                "publisher": s.get("PublisherName"),
                "year": s.get("PublicationYear"),
            }
            for s in (raw.get("Sources") or [])
            if isinstance(s, dict)
        ]

        food = _ratings(raw.get("Food"))
        cover = _ratings(raw.get("Cover"))

        return {
            "status": "success",
            "data": {"food": food, "cover": cover, "sources": sources},
            "metadata": {
                "food_count": len(food),
                "cover_count": len(cover),
                "query_symbol": symbol,
                "plant_id": plant_id,
                "source": "USDA PLANTS",
                "note": "Wildlife food and cover value ratings (e.g. Minor/Low/Moderate/High) by source for mammal and bird groups.",
            },
        }

    def _search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        search_text = (
            arguments.get("searchText") or arguments.get("search_text") or ""
        ).strip()
        if not search_text:
            return {
                "status": "error",
                "error": "'searchText' is required (a plant scientific/common name or genus, e.g. 'white oak').",
            }
        try:
            limit = int(arguments.get("limit", 25))
        except (TypeError, ValueError):
            limit = 25
        limit = max(1, min(limit, 200))

        try:
            resp = requests.get(
                f"{USDA_PLANTS_BASE}/PlantSearch",
                params={"searchText": search_text},
                headers={"Accept": "application/json"},
                timeout=self.timeout,
            )
            resp.raise_for_status()
            results = resp.json()
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

        if not isinstance(results, list):
            results = []
        matches = []
        for item in results:
            if not isinstance(item, dict):
                continue
            plant = item.get("Plant")
            if not isinstance(plant, dict):
                continue
            matches.append(
                {
                    "symbol": plant.get("Symbol"),
                    "scientific_name": _strip_html(plant.get("ScientificName")),
                    "common_name": plant.get("CommonName") or item.get("Text"),
                    "rank": plant.get("Rank"),
                    "id": plant.get("Id"),
                }
            )

        total = len(matches)
        matches = matches[:limit]
        return {
            "status": "success",
            "data": matches,
            "metadata": {
                "total_results": total,
                "returned_results": len(matches),
                "query": search_text,
                "source": "USDA PLANTS",
                "note": "Use the 'symbol' field with USDA_plants_get_profile / USDA_plants_get_characteristics."
                if matches
                else f"No USDA PLANTS matches for '{search_text}'.",
            },
        }

    def _profile(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
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
