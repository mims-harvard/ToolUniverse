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


def _plant_identity(profile, symbol):
    """Which plant the symbol resolved to, for the tools that only need its id.

    Each of these tools pays for a PlantProfile to turn a symbol into a
    numeric id and then threw the profile away, so a wetland or invasive
    answer named neither the species nor the fact that USDA had substituted
    one: `symbol=AGRE2` resolves to ELRE4, Elymus repens.
    """
    if not isinstance(profile, dict):
        return None
    returned = profile.get("Symbol")
    identity = {
        "symbol": returned,
        "scientific_name": _strip_html(
            profile.get("ScientificNameWithoutAuthor") or profile.get("ScientificName")
        ),
        "common_name": profile.get("CommonName"),
        "rank": profile.get("Rank"),
        "accepted_symbol": profile.get("AcceptedSymbol"),
        "queried_symbol": symbol,
        # Native, introduced or both, per region. The counterpart question to
        # an invasive or noxious listing, and on the same record.
        "native_statuses": profile.get("NativeStatuses"),
        # The classification, as the ranked chain the profile already holds.
        # Kept here as names and ranks rather than the full ancestor records,
        # which USDA_plants_get_profile returns in full: enough to tell two
        # plants of the same common name apart, without repeating a
        # nine-row taxonomy on every wetland or wildlife row.
        "lineage": [
            {
                "rank": a.get("Rank"),
                "rank_id": a.get("RankId"),
                "name": _strip_html(a.get("ScientificName")),
                "common_name": a.get("CommonName"),
                "symbol": a.get("Symbol"),
            }
            for a in (profile.get("Ancestors") or [])
            if isinstance(a, dict)
        ],
        # Where it occurs, as the states USDA has distribution data for. The
        # bounding boxes behind them are on USDA_plants_get_profile.
        "distribution_states": [
            m.get("StateAbbr")
            for m in (profile.get("MapCoordinates") or [])
            if isinstance(m, dict) and m.get("StateAbbr")
        ],
    }
    if symbol and returned and returned != symbol:
        identity["synonym_note"] = (
            f"'{symbol}' is a synonym; USDA PLANTS answered for the accepted "
            f"taxon '{returned}'."
        )
    return identity


def _resolve_plant_id(arguments: Dict[str, Any], timeout: int):
    """Resolve a plant to its numeric PLANTS Id.

    Accepts an explicit ``id`` (numeric PLANTS Id), or a ``symbol`` that is
    looked up via the PlantProfile endpoint. Returns ``(plant_id, symbol,
    error_dict, profile)`` where ``error_dict`` is non-None only on failure. A
    symbol with no matching profile returns ``(None, symbol, None, None)`` so
    callers can emit an empty success.

    The profile is handed back rather than dropped: resolving a symbol costs a
    full PlantProfile request, and every caller then answered without saying
    which plant it had resolved to -- which matters because USDA redirects a
    synonym symbol to the accepted taxon in silence.
    """
    raw_id = arguments.get("id") or arguments.get("plant_id")
    if raw_id not in (None, ""):
        try:
            return int(raw_id), None, None, None
        except (TypeError, ValueError):
            return (
                None,
                None,
                {
                    "status": "error",
                    "error": f"'id' must be a numeric USDA PLANTS Id (got {raw_id!r}).",
                },
                None,
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
            None,
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
            None,
        )
    except requests.exceptions.RequestException as e:
        return (
            None,
            symbol,
            {"status": "error", "error": f"USDA PLANTS request failed: {e}"},
            None,
        )
    except ValueError:
        return (
            None,
            symbol,
            {"status": "error", "error": "USDA PLANTS returned a non-JSON response"},
            None,
        )

    if profile is None:
        return None, symbol, None, None
    return profile.get("Id"), symbol, None, profile


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
        plant_id, symbol, err, profile = _resolve_plant_id(arguments, self.timeout)
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
                "plant": _plant_identity(profile, symbol),
                "source": "USDA PLANTS",
                "note": "WetlandCode values: OBL=obligate wetland, FACW=facultative wetland, FAC=facultative, FACU=facultative upland, UPL=upland (per USACE region).",
            },
        }

    def _invasive(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        plant_id, symbol, err, profile = _resolve_plant_id(arguments, self.timeout)
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
                "plant": _plant_identity(profile, symbol),
                "source": "USDA PLANTS",
                "note": "State-by-state invasive listings and federal/state noxious-weed legal statuses.",
            },
        }

    def _wildlife(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        plant_id, symbol, err, profile = _resolve_plant_id(arguments, self.timeout)
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
                "plant": _plant_identity(profile, symbol),
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
        limit = arguments.get("limit", 25)
        if (
            isinstance(limit, bool)
            or not isinstance(limit, int)
            or not 1 <= limit <= 200
        ):
            return {
                "status": "error",
                "error": "limit must be an integer from 1 to 200",
            }
        offset = arguments.get("offset", 0)
        if isinstance(offset, bool) or not isinstance(offset, int):
            return {"status": "error", "error": "offset must be a non-negative integer"}
        if offset < 0:
            return {"status": "error", "error": "offset must be a non-negative integer"}

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

        if not isinstance(results, list) or any(
            not isinstance(item, dict) for item in results
        ):
            return {
                "status": "error",
                "error": "USDA PLANTS returned malformed search results",
            }
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
                    # Fix-R4E-4: when CommonName is empty, USDA's own
                    # fallback autocomplete text re-renders the scientific
                    # name wrapped in <i> tags — strip it the same way
                    # scientific_name already is, instead of leaking raw
                    # HTML markup into a field callers expect to be plain
                    # text.
                    "common_name": plant.get("CommonName")
                    or _strip_html(item.get("Text")),
                    "rank": plant.get("Rank"),
                    "rank_id": plant.get("RankId"),
                    "id": plant.get("Id"),
                    # Whether the hit is itself an accepted name. A search for
                    # a genus returns synonyms beside accepted taxa and the
                    # row did not distinguish them, so the caller picked a
                    # symbol that would be silently redirected on the next
                    # call.
                    "accepted_symbol": plant.get("AcceptedSymbol"),
                    "synonym_symbol": plant.get("SynonymSymbol"),
                    "group": plant.get("GroupName") or plant.get("Group"),
                    "duration": plant.get("Durations") or plant.get("Duration"),
                    "growth_habits": plant.get("GrowthHabits"),
                    "native_statuses": plant.get("NativeStatuses"),
                }
            )

        total = len(matches)
        matches = matches[offset : offset + limit]
        has_more = offset + len(matches) < total
        return {
            "status": "success",
            "data": matches,
            "metadata": {
                "total_results": total,
                "returned_results": len(matches),
                "offset": offset,
                "limit": limit,
                "has_more": has_more,
                "next_offset": offset + len(matches) if has_more else None,
                "result_set_complete": offset == 0 and len(matches) == total,
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
        # USDA redirects a synonym symbol to the accepted taxon without
        # saying so: `symbol=AGRE2` answers the profile of ELRE4 (Elymus
        # repens). The returned symbol and the queried one were in two
        # different parts of the response -- data and metadata -- and nothing
        # stated the substitution.
        returned_symbol = profile.get("Symbol")
        note = None
        if returned_symbol and returned_symbol != symbol:
            note = (
                f"'{symbol}' is a synonym; USDA PLANTS answered with the "
                f"accepted taxon '{returned_symbol}'"
                + (
                    f" ({_strip_html(profile.get('ScientificName'))})."
                    if profile.get("ScientificName")
                    else "."
                )
            )
        metadata = {"query_symbol": symbol, "source": "USDA PLANTS"}
        if note:
            metadata["note"] = note
        return {
            "status": "success",
            "data": {
                "id": profile.get("Id"),
                "symbol": returned_symbol,
                "scientific_name": _strip_html(
                    profile.get("ScientificNameWithoutAuthor")
                    or profile.get("ScientificName")
                ),
                "common_name": profile.get("CommonName"),
                "group": profile.get("GroupName") or profile.get("Group"),
                "rank": profile.get("Rank"),
                "rank_id": profile.get("RankId"),
                "duration": profile.get("Durations") or profile.get("Duration"),
                "growth_habits": profile.get("GrowthHabits"),
                "native_statuses": profile.get("NativeStatuses"),
                "synonyms": profile.get("Synonyms", [])
                if profile.get("HasSynonyms")
                else [],
                "fips_distribution": profile.get("FipsCode"),
                "queried_symbol": symbol,
                "synonym_note": note,
                # Where the symbol resolves, when USDA names an accepted
                # taxon separately from the record it answered with.
                "accepted_symbol": profile.get("AcceptedSymbol"),
                "accepted_id": profile.get("AcceptedId"),
                "accepted_scientific_name": _strip_html(
                    profile.get("AcceptedScientificName")
                ),
                "accepted_common_name": profile.get("AcceptedCommonName"),
                "synonym_symbol": profile.get("SynonymSymbol"),
                # The classification. Nine ancestors for balsam fir, Kingdom
                # down to Genus, each with its own symbol and rank -- the part
                # of a plant profile that says what the plant IS, and the
                # profile already had it.
                "ancestors": [
                    {
                        "id": a.get("Id"),
                        "symbol": a.get("Symbol"),
                        "scientific_name": _strip_html(a.get("ScientificName")),
                        "common_name": a.get("CommonName"),
                        "rank": a.get("Rank"),
                        "rank_id": a.get("RankId"),
                    }
                    for a in (profile.get("Ancestors") or [])
                    if isinstance(a, dict)
                ],
                # The distribution. `fips_distribution` is null on most
                # records; the map coordinates are the per-state bounding
                # boxes USDA actually publishes.
                "map_coordinates": profile.get("MapCoordinates") or [],
                "distribution_results": profile.get("PlantsDistributionResults"),
                "other_common_names": profile.get("OtherCommonNames") or [],
                "subordinate_taxa": profile.get("SubordinateTaxa"),
                # Status sets with no tool of their own: the invasive and
                # noxious ones have USDA_plants_get_invasive_status, and these
                # two were reachable nowhere.
                "legal_statuses": profile.get("LegalStatuses"),
                "protected_statuses": profile.get("ProtectedStatuses"),
                "notes": profile.get("PlantNotes"),
                "fact_sheet_urls": profile.get("FactSheetUrls") or [],
                "plant_guide_urls": profile.get("PlantGuideUrls") or [],
                "related_links": profile.get("RelatedLinks") or [],
                # Which of the sibling tools will have something for this
                # plant. USDA states it per record and a caller otherwise
                # finds out by trying.
                "available_data": {
                    key[3:].lower(): value
                    for key, value in profile.items()
                    if key.startswith("Has") and isinstance(value, bool)
                },
            },
            "metadata": metadata,
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
                "plant": _plant_identity(profile, symbol),
                "source": "USDA PLANTS",
            },
        }
