# nci_thesaurus_tool.py
"""
NCI Thesaurus (NCIt) API tool for ToolUniverse.

The NCI Thesaurus is the National Cancer Institute's reference terminology
covering cancer-related diseases, drugs, genes, anatomy, and biological
processes. It is the de-facto standard vocabulary for cancer research.

API: https://api-evsrest.nci.nih.gov/api/v1/
No authentication required. Free public access.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

NCI_BASE_URL = "https://api-evsrest.nci.nih.gov/api/v1"


@register_tool("NCIThesaurusTool")
class NCIThesaurusTool(BaseTool):
    """
    Tool for querying the NCI Thesaurus (NCIt).

    NCIt provides a rich set of cancer-related terms with definitions,
    synonyms, semantic types, and cross-references to ICD, SNOMED-CT,
    MedDRA, and CDISC. Covers ~190,000 concepts organized in a polyhierarchy.

    Supports: concept search, concept details, hierarchy navigation.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "search")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the NCI Thesaurus API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"NCI Thesaurus API timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to NCI Thesaurus API",
            }
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "error": f"NCI Thesaurus API HTTP error: {e.response.status_code}",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error querying NCI Thesaurus: {str(e)}",
            }

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate NCI endpoint."""
        if self.endpoint == "search":
            return self._search(arguments)
        elif self.endpoint == "get_concept":
            return self._get_concept(arguments)
        elif self.endpoint == "get_children":
            return self._get_children(arguments)
        elif self.endpoint == "get_parents":
            return self._get_parents(arguments)
        elif self.endpoint == "get_maps":
            return self._get_maps(arguments)
        else:
            return {"status": "error", "error": f"Unknown endpoint: {self.endpoint}"}

    def _search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search NCI Thesaurus by term."""
        term = arguments.get("term", "")
        if not isinstance(term, str) or not term.strip():
            return {"status": "error", "error": "term parameter is required"}

        page_size = arguments.get("page_size", 10)
        offset = arguments.get("offset", 0)
        match_type = arguments.get("match_type", "match")
        if (
            isinstance(page_size, bool)
            or not isinstance(page_size, int)
            or not 1 <= page_size <= 100
        ):
            return {
                "status": "error",
                "error": "page_size must be an integer between 1 and 100",
                "parameter": "page_size",
            }
        if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
            return {
                "status": "error",
                "error": "offset must be a non-negative integer",
                "parameter": "offset",
            }
        allowed_match_types = {
            "contains",
            "match",
            "startsWith",
            "phrase",
            "AND",
            "OR",
            "fuzzy",
        }
        if match_type not in allowed_match_types:
            return {
                "status": "error",
                "error": (
                    "match_type must be one of: contains, match, startsWith, "
                    "phrase, AND, OR, fuzzy"
                ),
                "parameter": "match_type",
            }

        url = f"{NCI_BASE_URL}/concept/ncit/search"
        params = {
            "term": term.strip(),
            "type": match_type,
            "include": "minimal",
            "fromRecord": offset,
            "pageSize": page_size,
        }
        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()

        data = response.json()
        concepts = data.get("concepts", [])

        results = []
        for c in concepts:
            results.append(
                {
                    "code": c.get("code", ""),
                    "name": c.get("name", ""),
                    "terminology": c.get("terminology"),
                    "leaf": c.get("leaf"),
                }
            )

        total = data.get("total", len(results))
        try:
            total = int(total)
        except (TypeError, ValueError):
            total = len(results)
        returned_count = len(results)
        has_more = offset + returned_count < total

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "source": "NCI Thesaurus (NCIt)",
                "total_results": total,
                "returned_count": returned_count,
                "query": term.strip(),
                "match_type": match_type,
                "offset": offset,
                "page_size": page_size,
                "has_more": has_more,
                "next_offset": (
                    offset + returned_count if returned_count and has_more else None
                ),
                "truncated": has_more,
                "result_set_complete": not has_more,
            },
        }

    def _get_concept(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed concept information by code."""
        code = arguments.get("code", "")
        if not code:
            return {"status": "error", "error": "code parameter is required"}

        url = f"{NCI_BASE_URL}/concept/ncit/{code}"
        params = {"include": "summary"}
        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()

        data = response.json()

        # Extract definition
        definitions = data.get("definitions", [])
        # Four definitions for C3224, from NCI-GLOSS, CDISC, NICHD and NCI,
        # and `definitions[0]` is the patient-facing glossary one. NCI is the
        # thesaurus's own source, so it is preferred and the source is
        # reported; all four are returned beside it, because which body
        # wrote a definition is part of what the definition is.
        definition_rows = [
            {
                "definition": row.get("definition"),
                "source": row.get("source"),
                "type": row.get("type"),
                "code": row.get("code"),
            }
            for row in definitions
            if isinstance(row, dict) and row.get("definition")
        ]
        preferred_definition = next(
            (row for row in definition_rows if (row.get("source") or "") == "NCI"),
            definition_rows[0] if definition_rows else None,
        )
        definition = (
            preferred_definition.get("definition") if preferred_definition else None
        )
        definition_source = (
            preferred_definition.get("source") if preferred_definition else None
        )

        # Extract synonyms
        synonyms_raw = data.get("synonyms", [])
        synonyms = []
        for s in synonyms_raw:
            # `termType` is the term's role WITHIN its source terminology and
            # NCIt's `type` is the annotation property the synonym came from.
            # They are not interchangeable: C3224 has ten rows with
            # termType "PT" -- each the preferred term of a different source
            # -- and exactly one with type "Preferred_Name", which is NCIt's
            # own. That one and the Display_Name row carry no termType at
            # all, so the old row reported them as {"type": null,
            # "source": null} and nothing marked the concept's actual name.
            synonyms.append(
                {
                    "name": s.get("name", ""),
                    "type": s.get("termType"),
                    "source": s.get("source"),
                    "annotation_property": s.get("type"),
                    "annotation_property_code": s.get("typeCode"),
                    "is_preferred_name": s.get("type") == "Preferred_Name",
                    "is_display_name": s.get("type") == "Display_Name",
                }
            )

        # Extract properties
        properties_raw = data.get("properties", [])
        properties = []
        for p in properties_raw:
            properties.append(
                {
                    "type": p.get("type", ""),
                    "value": p.get("value", ""),
                    # The P-code NCIt and its downstream datasets key on; the
                    # readable type beside it is the label, not the id.
                    "code": p.get("code"),
                }
            )

        return {
            "status": "success",
            "data": {
                "code": data.get("code", ""),
                "name": data.get("name", ""),
                "definition": definition,
                "definition_source": definition_source,
                "definitions": definition_rows,
                "definition_count": len(definition_rows),
                "synonyms": synonyms,
                "properties": properties,
            },
            "metadata": {
                "source": "NCI Thesaurus (NCIt)",
                "terminology": "ncit",
            },
        }

    def _get_children(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get child concepts for a given code."""
        code = arguments.get("code", "")
        if not code:
            return {"status": "error", "error": "code parameter is required"}

        url = f"{NCI_BASE_URL}/concept/ncit/{code}/children"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()

        data = response.json()

        results = []
        for c in data:
            results.append(
                {
                    "code": c.get("code", ""),
                    "name": c.get("name", ""),
                    "leaf": c.get("leaf"),
                }
            )

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "source": "NCI Thesaurus (NCIt)",
                "parent_code": code,
                "total_children": len(results),
            },
        }

    def _get_parents(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get direct parent concepts (upward hierarchy) for a given code."""
        code = arguments.get("code", "")
        if not code:
            return {"status": "error", "error": "code parameter is required"}

        url = f"{NCI_BASE_URL}/concept/ncit/{code}/parents"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()

        data = response.json()

        results = []
        for c in data:
            results.append(
                {
                    "code": c.get("code", ""),
                    "name": c.get("name", ""),
                    "leaf": c.get("leaf"),
                }
            )

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "source": "NCI Thesaurus (NCIt)",
                "child_code": code,
                "total_parents": len(results),
            },
        }

    def _get_maps(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get cross-vocabulary maps (MedDRA, SNOMED, GDC, ICD) for a concept."""
        code = arguments.get("code", "")
        if not code:
            return {"status": "error", "error": "code parameter is required"}

        url = f"{NCI_BASE_URL}/concept/ncit/{code}"
        params = {"include": "maps"}
        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()

        data = response.json()
        maps_raw = data.get("maps", []) or []

        maps = []
        terminologies = set()
        for m in maps_raw:
            target_terminology = m.get("targetTerminology")
            if target_terminology:
                terminologies.add(target_terminology)
            maps.append(
                {
                    "type": m.get("type"),
                    "target_name": m.get("targetName"),
                    "target_code": m.get("targetCode"),
                    "target_term_type": m.get("targetTermType"),
                    "target_terminology": target_terminology,
                    "target_terminology_version": m.get("targetTerminologyVersion"),
                }
            )

        return {
            "status": "success",
            "data": {
                "code": data.get("code", code),
                "name": data.get("name", ""),
                "maps": maps,
            },
            "metadata": {
                "source": "NCI Thesaurus (NCIt)",
                "total_maps": len(maps),
                "target_terminologies": sorted(terminologies),
            },
        }
