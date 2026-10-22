# unichem_tool.py
"""
UniChem REST API tool for ToolUniverse.

UniChem is EBI's unified chemical structure cross-referencing service.
It maps compound identifiers across 40+ chemical databases including
ChEMBL, DrugBank, PDBe, PubChem, KEGG, ChEBI, and HMDB. Given a
chemical structure (InChIKey) or database ID, UniChem returns all
known cross-references instantly.

API: https://www.ebi.ac.uk/unichem/api/v1/
No authentication required. Free for all use.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

UNICHEM_BASE_URL = "https://www.ebi.ac.uk/unichem/api/v1"


@register_tool("UniChemTool")
class UniChemTool(BaseTool):
    """
    Tool for querying UniChem compound cross-referencing service.

    Maps chemical identifiers across 40+ databases using InChIKey,
    source compound IDs, or UCIs (UniChem Compound Identifiers).

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        self.endpoint_type = tool_config.get("fields", {}).get(
            "endpoint_type", "search_compound"
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the UniChem API call."""
        try:
            return self._dispatch(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"UniChem API request timed out after {self.timeout} seconds",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to UniChem API. Check network connectivity.",
            }
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "error": f"UniChem API HTTP error: {e.response.status_code}",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error querying UniChem: {str(e)}",
            }

    def _dispatch(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint based on config."""
        if self.endpoint_type == "search_compound":
            return self._search_compound(arguments)
        elif self.endpoint_type == "list_sources":
            return self._list_sources(arguments)
        elif self.endpoint_type == "connectivity_search":
            return self._connectivity_search(arguments)
        else:
            return {
                "status": "error",
                "error": f"Unknown endpoint_type: {self.endpoint_type}",
            }

    @staticmethod
    def _search_arguments(arguments):
        compound = arguments.get("compound", "")
        search_type = arguments.get("type", "inchikey")
        source_id = arguments.get("sourceID")
        if not isinstance(compound, str) or not compound.strip():
            return {"status": "error", "error": "compound must be a non-empty string"}
        if search_type not in {"inchi", "inchikey", "sourceID", "uci"}:
            return {
                "status": "error",
                "error": "type must be one of inchi, inchikey, sourceID, or uci",
            }
        if search_type == "sourceID":
            if (
                isinstance(source_id, bool)
                or not isinstance(source_id, int)
                or source_id < 1
            ):
                return {
                    "status": "error",
                    "error": "sourceID must be a positive integer when type is sourceID",
                }
        elif source_id is not None:
            return {
                "status": "error",
                "error": "sourceID is only valid when type is sourceID",
            }
        return compound.strip(), search_type, source_id

    @staticmethod
    def _nonnegative_count(value, field):
        if isinstance(value, str) and value.isdigit():
            value = int(value)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            return {
                "status": "error",
                "error": f"UniChem {field} was not a valid count",
            }
        return value

    @staticmethod
    def _source_record(source):
        return {
            "source_id": source.get("id"),
            "source_name": source.get("shortName", ""),
            "source_long_name": source.get("longName", ""),
            "compound_id": source.get("compoundId", ""),
            "url": source.get("url"),
        }

    def _search_compound(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search UniChem for a compound by InChIKey, sourceID, or UCI."""
        controls = self._search_arguments(arguments)
        if isinstance(controls, dict):
            return controls
        compound, search_type, source_id = controls

        payload = {
            "compound": compound,
            "type": search_type,
        }
        if source_id is not None:
            payload["sourceID"] = source_id

        url = f"{UNICHEM_BASE_URL}/compounds"
        response = requests.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        raw = response.json()
        if not isinstance(raw, dict):
            return {"status": "error", "error": "UniChem response was not an object"}
        # UniChem answers a query that matches nothing with response
        # 'Not found' and an empty list: an empty result, not a failure.
        if raw.get("response") == "Not found" and not raw.get("compounds"):
            return {
                "status": "success",
                "data": {
                    "query": compound,
                    "query_type": search_type,
                    "total_compounds": 0,
                    "returned_compounds": 0,
                    "result_set_complete": True,
                    "compounds": [],
                    "inchi": None,
                    "inchikey": None,
                    "formula": None,
                    "uci": None,
                    "source_count": 0,
                    "sources": [],
                },
                "metadata": {
                    "source": "UniChem",
                    "query": compound,
                    "endpoint": "compounds",
                },
            }
        if raw.get("response") != "Success":
            return {
                "status": "error",
                "error": f"UniChem application response was {raw.get('response')!r}",
                "not_found": raw.get("notFound"),
            }
        total = self._nonnegative_count(raw.get("totalCompounds"), "totalCompounds")
        if isinstance(total, dict):
            return total

        compounds = raw.get("compounds", [])
        if not isinstance(compounds, list) or len(compounds) != total:
            return {
                "status": "error",
                "error": "UniChem compounds length conflicts with totalCompounds",
                "reported_total": total,
                "returned_compounds": len(compounds)
                if isinstance(compounds, list)
                else None,
            }
        parsed_compounds = []
        for entry in compounds:
            if not isinstance(entry, dict) or not isinstance(entry.get("inchi"), dict):
                return {
                    "status": "error",
                    "error": "UniChem returned a malformed compound",
                }
            sources_raw = entry.get("sources")
            if not isinstance(sources_raw, list) or any(
                not isinstance(source, dict) for source in sources_raw
            ):
                return {
                    "status": "error",
                    "error": "UniChem returned malformed sources",
                }
            sources = [self._source_record(source) for source in sources_raw]
            unique_source_ids = {source["source_id"] for source in sources}
            inchi_data = entry["inchi"]
            parsed_compounds.append(
                {
                    "inchi": inchi_data.get("inchi"),
                    # The /compounds response carries the standard InChIKey
                    # at the top level (same field ``_connectivity_search``
                    # reads).
                    "inchikey": entry.get("standardInchiKey"),
                    "formula": inchi_data.get("formula"),
                    "uci": entry.get("uci"),
                    "source_record_count": len(sources),
                    "unique_source_count": len(unique_source_ids),
                    "duplicate_source_records": len(sources) - len(unique_source_ids),
                    "sources": sources,
                }
            )

        result = {
            "query": compound,
            "query_type": search_type,
            "total_compounds": total,
            "returned_compounds": len(parsed_compounds),
            "result_set_complete": True,
            "compounds": parsed_compounds,
            "not_found": raw.get("notFound"),
        }
        if len(parsed_compounds) == 1:
            result.update(parsed_compounds[0])
            # Fall back to echoing the query only when the API omits the
            # InChIKey, so callers that searched by InChIKey never lose it.
            if not result["inchikey"]:
                result["inchikey"] = compound if search_type == "inchikey" else None
            result["source_count"] = parsed_compounds[0]["source_record_count"]

        return {
            "status": "success",
            "data": result,
            "metadata": {
                "source": "UniChem",
                "query": compound,
                "endpoint": "compounds",
            },
        }

    def _connectivity_search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Connectivity (cross-source) search.

        Finds all compounds across the 40+ UniChem source databases that
        share the same connectivity layer as the query (i.e. salts,
        stereoisomers, tautomers, charge/protonation/isotope variants).
        Each returned source entry carries a per-match ``comparison`` object
        describing how that match differs from the query (charge, stereo
        double bond, isotope, protonation, heavy atoms, etc.).
        """
        controls = self._search_arguments(arguments)
        if isinstance(controls, dict):
            return controls
        compound, search_type, source_id = controls

        payload = {"compound": compound, "type": search_type}
        if source_id is not None:
            payload["sourceID"] = source_id

        url = f"{UNICHEM_BASE_URL}/connectivity"
        response = requests.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        raw = response.json()
        if not isinstance(raw, dict) or raw.get("response") != "Success":
            return {
                "status": "error",
                "error": "UniChem connectivity response was not a successful object",
            }
        total_compounds = self._nonnegative_count(
            raw.get("totalCompounds"), "totalCompounds"
        )
        total_sources = self._nonnegative_count(raw.get("totalSources"), "totalSources")
        if isinstance(total_compounds, dict):
            return total_compounds
        if isinstance(total_sources, dict):
            return total_sources
        sources_raw = raw.get("sources")
        if not isinstance(sources_raw, list) or len(sources_raw) != total_sources:
            return {
                "status": "error",
                "error": "UniChem connectivity sources length conflicts with totalSources",
            }

        searched = raw.get("searchedCompound", {})
        searched_info = {
            "inchi": searched.get("inchi") if isinstance(searched, dict) else None,
            "inchikey": (
                searched.get("standardInchiKey") if isinstance(searched, dict) else None
            ),
            "uci": searched.get("uci") if isinstance(searched, dict) else None,
        }

        matches = []
        for s in sources_raw:
            matches.append(
                {
                    "source_id": s.get("id"),
                    "source_name": s.get("shortName", ""),
                    "source_long_name": s.get("longName", ""),
                    "compound_id": s.get("compoundId", ""),
                    "type_of_search": s.get("typeOfSearch"),
                    "url": s.get("url", None),
                    "comparison": s.get("comparison", {}),
                }
            )

        result = {
            "response": raw.get("response"),
            "searched_compound": searched_info,
            "total_compounds": total_compounds,
            "total_sources": total_sources,
            "match_count": len(matches),
            "matches": matches,
        }

        return {
            "status": "success",
            "data": result,
            "metadata": {
                "source": "UniChem",
                "query": compound,
                "endpoint": "connectivity",
            },
        }

    def _list_sources(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List all chemical database sources in UniChem."""
        url = f"{UNICHEM_BASE_URL}/sources/"
        response = requests.get(
            url,
            headers={"Content-Type": "application/json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        raw = response.json()
        if not isinstance(raw, dict):
            return {
                "status": "error",
                "error": "UniChem sources response was not an object",
            }
        total = self._nonnegative_count(raw.get("totalSources"), "totalSources")
        if isinstance(total, dict):
            return total

        sources_raw = raw.get("sources", [])
        if not isinstance(sources_raw, list) or len(sources_raw) != total:
            return {
                "status": "error",
                "error": "UniChem sources length conflicts with totalSources",
            }
        sources = []
        for s in sources_raw:
            sources.append(
                {
                    "source_id": s.get("sourceID", 0),
                    "name": s.get("name", ""),
                    "long_name": s.get("nameLong", s.get("nameLabel", "")),
                    "description": s.get("description", None),
                    "compound_count": s.get("UCICount", None),
                    "last_updated": s.get("lastUpdated", None),
                }
            )

        result = {
            "source_count": len(sources),
            "sources": sources,
            "reported_total_sources": total,
            "result_set_complete": True,
        }

        return {
            "status": "success",
            "data": result,
            "metadata": {
                "source": "UniChem",
                "query": "all_sources",
                "endpoint": "sources",
            },
        }
