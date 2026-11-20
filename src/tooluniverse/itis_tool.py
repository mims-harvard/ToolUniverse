# itis_tool.py
"""
ITIS (Integrated Taxonomic Information System) API tool for ToolUniverse.

ITIS provides authoritative taxonomic information on plants, animals,
fungi, and microbes of North America and the world. It is maintained by
a partnership of US, Canadian, and Mexican agencies.

API: https://www.itis.gov/ITISWebService/jsonservice/
No authentication required. Free public access.
"""

import requests
from typing import Dict, Any, List
from .base_tool import BaseTool
from .tool_registry import register_tool

ITIS_BASE_URL = "https://www.itis.gov/ITISWebService/jsonservice"

# Homo sapiens carries 29 synonyms, 7 jurisdictional origins and 8 references
# across three lists. Each is capped here and the count and the cut reported.
SYNONYMS_PER_RECORD = 50
REFERENCES_PER_RECORD = 25
JURISDICTIONS_PER_RECORD = 50


def _clean(value: Any) -> Any:
    """ITIS pads several string fields to a fixed width: 'Species        '."""
    return value.strip() if isinstance(value, str) else value


def _rows(node: Any, key: str) -> List[Dict[str, Any]]:
    """The rows inside one of ITIS's `...List` wrappers.

    Every list is wrapped in an object with the row array under its own key,
    and ITIS puts a literal null in the array when the list is empty
    (`acceptedNames: [null]` for a valid taxon).
    """
    if not isinstance(node, dict):
        return []
    rows = node.get(key)
    if isinstance(rows, dict):
        rows = [rows]
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def _referred(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """What a reference is a reference *for*: the taxa it covers."""
    return [
        {
            "name": _clean(row.get("name")),
            "tsn": row.get("referredTsn"),
            "language": row.get("refLanguage"),
        }
        for row in rows
        if isinstance(row, dict)
    ]


def _capped(rows: List[Dict[str, Any]], cap: int) -> Dict[str, Any]:
    """A capped list beside its full count and whether it was cut."""
    return {"rows": rows[:cap], "total": len(rows), "truncated": len(rows) > cap}


@register_tool("ITISTool")
class ITISTool(BaseTool):
    """
    Tool for querying the ITIS taxonomic database.

    ITIS provides standardized species names, classification hierarchies,
    common names, and authority references. Supports search by scientific
    name, common name, TSN (Taxonomic Serial Number), and hierarchy retrieval.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "search_scientific")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the ITIS API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"ITIS API request timed out after {self.timeout} seconds",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to ITIS API. Check network connectivity.",
            }
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "error": f"ITIS API HTTP error: {e.response.status_code}",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error querying ITIS: {str(e)}",
            }

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate ITIS endpoint."""
        if self.endpoint == "search_scientific":
            return self._search_scientific(arguments)
        elif self.endpoint == "search_common":
            return self._search_common(arguments)
        elif self.endpoint == "hierarchy":
            return self._get_hierarchy(arguments)
        elif self.endpoint == "full_record":
            return self._get_full_record(arguments)
        else:
            return {"status": "error", "error": f"Unknown endpoint: {self.endpoint}"}

    def _search_scientific(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search for taxa by scientific name."""
        name = arguments.get("scientific_name", "")
        if not name:
            return {"status": "error", "error": "scientific_name parameter is required"}

        url = f"{ITIS_BASE_URL}/searchByScientificName"
        params = {"srchKey": name}
        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()

        data = response.json()
        names = data.get("scientificNames", [])

        # Filter out null entries
        results = []
        for n in names:
            if n and n.get("tsn"):
                results.append(
                    {
                        "tsn": n.get("tsn"),
                        "combined_name": n.get("combinedName"),
                        "author": n.get("author"),
                        "kingdom": n.get("kingdom"),
                        # ITIS splits the name into its ranked parts, which is
                        # how a subspecies or a variety is told from a species.
                        "name_parts": [
                            _clean(n.get(f"unitName{i}"))
                            for i in (1, 2, 3, 4)
                            if n.get(f"unitName{i}")
                        ],
                        "name_indicators": [
                            _clean(n.get(f"unitInd{i}"))
                            for i in (1, 2, 3, 4)
                            if n.get(f"unitInd{i}")
                        ],
                    }
                )

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "source": "ITIS",
                "query": name,
                "total_results": len(results),
            },
        }

    def _search_common(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search for taxa by common name."""
        name = arguments.get("common_name", "")
        if not name:
            return {"status": "error", "error": "common_name parameter is required"}

        url = f"{ITIS_BASE_URL}/searchByCommonName"
        params = {"srchKey": name}
        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()

        data = response.json()
        names = data.get("commonNames", [])

        results = []
        for n in names:
            if n and n.get("tsn"):
                results.append(
                    {
                        "tsn": n.get("tsn"),
                        "common_name": n.get("commonName"),
                        "language": n.get("language"),
                    }
                )

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "source": "ITIS",
                "query": name,
                "total_results": len(results),
            },
        }

    def _get_hierarchy(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get full taxonomic hierarchy for a TSN."""
        tsn = arguments.get("tsn", "")
        if not tsn:
            return {"status": "error", "error": "tsn parameter is required"}

        url = f"{ITIS_BASE_URL}/getFullHierarchyFromTSN"
        params = {"tsn": tsn}
        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()

        data = response.json()
        hierarchy_list = data.get("hierarchyList", [])

        results = []
        for h in hierarchy_list:
            if h and h.get("tsn"):
                results.append(
                    {
                        "tsn": h.get("tsn"),
                        "taxon_name": h.get("taxonName"),
                        "rank_name": _clean(h.get("rankName")),
                        "parent_tsn": h.get("parentTsn"),
                        # The parent's name, so the chain reads without
                        # re-looking-up every parent_tsn.
                        "parent_name": _clean(h.get("parentName")) or None,
                        # The naming authority for the rank, e.g.
                        # "Linnaeus, 1758" -- which is the citation for the name.
                        "author": _clean(h.get("author")),
                    }
                )

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "source": "ITIS",
                "query_tsn": str(tsn),
                "hierarchy_depth": len(results),
                # The response names the taxon the hierarchy was requested
                # for -- as an empty string for some TSNs, reported as null.
                "taxon_name": _clean(data.get("sciName")) or None,
                "rank_name": _clean(data.get("rankName")) or None,
                "author": _clean(data.get("author")) or None,
            },
        }

    def _get_full_record(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get complete taxonomic record for a TSN."""
        tsn = arguments.get("tsn", "")
        if not tsn:
            return {"status": "error", "error": "tsn parameter is required"}

        url = f"{ITIS_BASE_URL}/getFullRecordFromTSN"
        params = {"tsn": tsn}
        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()

        data = response.json()

        # Extract key fields from the full record
        sci_name = data.get("scientificName", {})
        usage = data.get("usage", {})
        taxon_author = data.get("taxonAuthor", {})

        # Get common names
        common_names_data = data.get("commonNameList", {})
        common_names_list = common_names_data.get("commonNames", [])
        common_names = []
        if isinstance(common_names_list, list):
            for cn in common_names_list:
                if cn and cn.get("commonName"):
                    common_names.append(
                        {
                            "name": cn.get("commonName"),
                            "language": cn.get("language"),
                        }
                    )

        # Get parent TSN
        parent_tsn_data = data.get("parentTSN", {})

        # An invalid name is only half an answer without the name that replaced
        # it: TSN 944513 is reported "invalid", and the record says in the same
        # response that it is a "junior synonym" of Homo sapiens, TSN 180092.
        accepted = [
            {
                "tsn": row.get("acceptedTsn"),
                "scientific_name": _clean(row.get("acceptedName")),
                "author": _clean(row.get("author")),
            }
            for row in _rows(data.get("acceptedNameList"), "acceptedNames")
        ]
        synonyms = _capped(
            [
                {
                    "tsn": row.get("tsn"),
                    "scientific_name": _clean(row.get("sciName")),
                    "author": _clean(row.get("author")),
                }
                for row in _rows(data.get("synonymList"), "synonyms")
            ],
            SYNONYMS_PER_RECORD,
        )
        jurisdictions = _capped(
            [
                {
                    "jurisdiction": _clean(row.get("jurisdictionValue")),
                    "origin": _clean(row.get("origin")),
                    "update_date": row.get("updateDate"),
                }
                for row in _rows(
                    data.get("jurisdictionalOriginList"), "jurisdictionalOrigins"
                )
            ],
            JURISDICTIONS_PER_RECORD,
        )
        publications = _capped(
            [
                {
                    "title": _clean(row.get("title")),
                    "authors": _clean(row.get("referenceAuthor")),
                    "publication": _clean(row.get("pubName")),
                    "publisher": _clean(row.get("publisher")),
                    "place": _clean(row.get("pubPlace")),
                    "date": row.get("actualPubDate") or row.get("listedPubDate"),
                    "pages": _clean(row.get("pages")),
                    "isbn": _clean(row.get("isbn")) or None,
                    "issn": _clean(row.get("issn")) or None,
                    "comment": _clean(row.get("pubComment")) or None,
                    "reference_for": _referred(row.get("referenceFor") or []),
                }
                for row in _rows(data.get("publicationList"), "publications")
            ],
            REFERENCES_PER_RECORD,
        )
        experts = _capped(
            [
                {
                    "expert": _clean(row.get("expert")),
                    "comment": _clean(row.get("comment")) or None,
                    "update_date": row.get("updateDate"),
                    "reference_for": _referred(row.get("referenceFor") or []),
                }
                for row in _rows(data.get("expertList"), "experts")
            ],
            REFERENCES_PER_RECORD,
        )
        other_sources = _capped(
            [
                {
                    "source": _clean(row.get("source")),
                    "source_type": _clean(row.get("sourceType")),
                    "version": _clean(row.get("version")),
                    "acquisition_date": row.get("acquisitionDate"),
                    "comment": _clean(row.get("sourceComment")) or None,
                    "reference_for": _referred(row.get("referenceFor") or []),
                }
                for row in _rows(data.get("otherSourceList"), "otherSources")
            ],
            REFERENCES_PER_RECORD,
        )
        comments = _capped(
            [
                {
                    "comment": _clean(row.get("commentDetail")),
                    "commentator": _clean(row.get("commentator")),
                    "comment_id": row.get("commentId"),
                    "update_date": row.get("updateDate"),
                }
                for row in _rows(data.get("commentList"), "comments")
            ],
            REFERENCES_PER_RECORD,
        )
        core = data.get("coreMetadata") or {}
        tax_rank = data.get("taxRank") or {}

        result = {
            "tsn": str(tsn),
            "scientific_name": sci_name.get("combinedName"),
            "kingdom": sci_name.get("kingdom"),
            "author": taxon_author.get("authorship"),
            "usage_rating": usage.get("taxonUsageRating"),
            "common_names": common_names,
            "parent_tsn": parent_tsn_data.get("parentTsn"),
            "rank": data.get("taxRank", {}).get("rankName"),
            "parent_name": _clean((data.get("hierarchyUp") or {}).get("parentName")),
            "rank_id": tax_rank.get("rankId"),
            "accepted_names": accepted,
            "unaccept_reason": _clean(
                (data.get("unacceptReason") or {}).get("unacceptReason")
            )
            or None,
            # "TWG standards met" is the Taxonomic Work Group's own verdict on
            # the record, and it was dropped from a tool whose point is to be
            # the authoritative name.
            "credibility_rating": _clean(
                (data.get("credibilityRating") or {}).get("credRating")
                or core.get("credRating")
            ),
            "taxon_currency": _clean(
                (data.get("currencyRating") or {}).get("taxonCurrency")
                or core.get("taxonCurrency")
            )
            or None,
            "completeness": _clean(
                (data.get("completenessRating") or {}).get("completeness")
            )
            or None,
            "update_date": (data.get("dateData") or {}).get("updateDate"),
            "initial_timestamp": (data.get("dateData") or {}).get("initialTimeStamp"),
            "geographic_divisions": [
                _clean(row.get("geographicValue"))
                for row in _rows(data.get("geographicDivisionList"), "geoDivisions")
            ],
            "jurisdictional_origins": jurisdictions["rows"],
            "jurisdictional_origin_count": jurisdictions["total"],
            "jurisdictional_origins_truncated": jurisdictions["truncated"],
            "synonyms": synonyms["rows"],
            "synonym_count": synonyms["total"],
            "synonyms_truncated": synonyms["truncated"],
            "publications": publications["rows"],
            "publication_count": publications["total"],
            "publications_truncated": publications["truncated"],
            "experts": experts["rows"],
            "expert_count": experts["total"],
            "experts_truncated": experts["truncated"],
            "other_sources": other_sources["rows"],
            "other_source_count": other_sources["total"],
            "other_sources_truncated": other_sources["truncated"],
            "comments": comments["rows"],
            "comment_count": comments["total"],
            "comments_truncated": comments["truncated"],
        }

        return {
            "status": "success",
            "data": result,
            "metadata": {
                "source": "ITIS",
                "query_tsn": str(tsn),
                "synonyms_per_record": SYNONYMS_PER_RECORD,
                "references_per_record": REFERENCES_PER_RECORD,
            },
        }
