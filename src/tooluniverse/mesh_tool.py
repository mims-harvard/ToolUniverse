# mesh_tool.py
"""
MeSH (Medical Subject Headings) API tool for ToolUniverse.

MeSH is the NLM's controlled vocabulary thesaurus used for indexing articles
in PubMed. It provides a hierarchically organized terminology for biomedical
concepts including diseases, drugs, anatomy, organisms, and procedures.
MeSH descriptors are organized into 16 top-level categories with tree
structures for browsing related terms.

API: https://id.nlm.nih.gov/mesh/
No authentication required. Free public access.
"""

from typing import Dict, Any

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

MESH_LOOKUP_URL = "https://id.nlm.nih.gov/mesh/lookup"
MESH_BASE_URL = "https://id.nlm.nih.gov/mesh"


@register_tool("MeSHTool")
class MeSHTool(BaseTool):
    """
    Tool for querying NLM's MeSH (Medical Subject Headings) vocabulary.

    MeSH is the authoritative vocabulary for biomedical indexing, used by
    PubMed to categorize literature. Supports descriptor lookup, term
    search, and hierarchical tree browsing.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "search_descriptors")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the MeSH API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"MeSH API request timed out after {self.timeout} seconds",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to MeSH API. Check network connectivity.",
            }
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "error": f"MeSH API HTTP error: {e.response.status_code}",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error querying MeSH: {str(e)}",
            }

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate MeSH endpoint."""
        if not isinstance(arguments, dict):
            return {"status": "error", "error": "arguments must be an object"}
        allowed_arguments = {
            "search_descriptors": {"query", "match", "limit"},
            "get_descriptor": {"descriptor_id"},
            "search_terms": {"query", "match", "limit"},
        }
        allowed = allowed_arguments.get(self.endpoint)
        if allowed is not None:
            unknown = sorted(set(arguments) - allowed)
            if unknown:
                return {
                    "status": "error",
                    "error": f"Unsupported parameter(s): {', '.join(unknown)}",
                }
        if self.endpoint == "search_descriptors":
            return self._search_descriptors(arguments)
        elif self.endpoint == "get_descriptor":
            return self._get_descriptor(arguments)
        elif self.endpoint == "search_terms":
            return self._search_terms(arguments)
        else:
            return {"status": "error", "error": f"Unknown endpoint: {self.endpoint}"}

    def _search_descriptors(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search MeSH descriptors (main headings) by label."""
        query = arguments.get("query")
        if not isinstance(query, str) or not query.strip():
            return {"status": "error", "error": "query must be a non-empty string"}
        query = query.strip()

        match_type = arguments.get("match", "contains")
        limit = arguments.get("limit", 20)
        if match_type not in {"contains", "exact", "startsWith"}:
            return {"status": "error", "error": "match is not supported by MeSH lookup"}
        if (
            isinstance(limit, bool)
            or not isinstance(limit, int)
            or not 1 <= limit <= 50
        ):
            return {"status": "error", "error": "limit must be an integer from 1 to 50"}

        url = f"{MESH_LOOKUP_URL}/descriptor"
        params = {
            "label": query,
            "match": match_type,
            "limit": limit,
        }

        response = requests.get(
            url,
            params=params,
            headers={"Accept": "application/json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, list) or any(
            not isinstance(item, dict) for item in data
        ):
            return {
                "status": "error",
                "error": "MeSH returned malformed search results",
            }

        results = []
        for item in data:
            resource_uri = item.get("resource")
            label = item.get("label")
            if (
                not isinstance(resource_uri, str)
                or not resource_uri.startswith(
                    (
                        "http://id.nlm.nih.gov/mesh/D",
                        "https://id.nlm.nih.gov/mesh/D",
                    )
                )
                or not isinstance(label, str)
            ):
                return {
                    "status": "error",
                    "error": "MeSH returned a malformed descriptor result",
                }
            normalized_label = label.casefold()
            normalized_query = query.casefold()
            matches = {
                "exact": normalized_label == normalized_query,
                "contains": normalized_query in normalized_label,
                "startsWith": normalized_label.startswith(normalized_query),
            }
            if not matches[match_type]:
                return {
                    "status": "error",
                    "error": "MeSH returned a descriptor that does not satisfy the requested match mode",
                    "returned_label": label,
                }
            # Extract descriptor ID from URI (e.g., http://id.nlm.nih.gov/mesh/D009369 -> D009369)
            descriptor_id = resource_uri.rsplit("/", 1)[-1]
            if (
                not descriptor_id.startswith("D")
                or len(descriptor_id[1:]) not in {6, 9}
                or not descriptor_id[1:].isdigit()
            ):
                return {
                    "status": "error",
                    "error": "MeSH returned an invalid descriptor identifier",
                }
            results.append(
                {
                    "descriptor_id": descriptor_id,
                    "label": label,
                    "resource_uri": resource_uri,
                }
            )

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "source": "NLM MeSH",
                "query": query,
                "match_type": match_type,
                "returned": len(results),
                "requested_limit": limit,
                "total_results": len(results) if len(results) < limit else None,
                "total_results_known": len(results) < limit,
                "possibly_truncated": len(results) == limit,
                "result_set_complete": len(results) < limit,
                "pagination_supported": False,
                "warning": "MeSH lookup provides no total or offset; refine the query because the 50-result ceiling was reached."
                if len(results) == limit
                else None,
            },
        }

    def _get_descriptor(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed information for a MeSH descriptor by its ID."""
        descriptor_id = arguments.get("descriptor_id")
        if not isinstance(descriptor_id, str) or not descriptor_id.strip():
            return {
                "status": "error",
                "error": "descriptor_id must be a non-empty string (e.g. D009369)",
            }
        descriptor_id = descriptor_id.strip().upper()
        if (
            not descriptor_id.startswith("D")
            or len(descriptor_id[1:]) not in {6, 9}
            or not descriptor_id[1:].isdigit()
        ):
            return {
                "status": "error",
                "error": "descriptor_id must have format D followed by six or nine digits",
            }

        url = f"{MESH_BASE_URL}/{descriptor_id}.json"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict) or data.get("identifier") != descriptor_id:
            return {
                "status": "error",
                "error": "MeSH returned a different descriptor than requested",
                "requested_descriptor_id": descriptor_id,
                "returned_descriptor_id": data.get("identifier")
                if isinstance(data, dict)
                else None,
            }

        # Extract label
        label = data.get("label", {})
        if isinstance(label, dict):
            label = label.get("@value", "")

        # Extract annotation
        annotation = data.get("annotation", {})
        if isinstance(annotation, dict):
            annotation = annotation.get("@value", "")

        # Extract history note
        history_note = data.get("historyNote", {})
        if isinstance(history_note, dict):
            history_note = history_note.get("@value", "")

        # Extract tree numbers
        tree_numbers_raw = data.get("treeNumber", [])
        if isinstance(tree_numbers_raw, str):
            tree_numbers_raw = [tree_numbers_raw]
        tree_numbers = []
        for tn in (
            tree_numbers_raw
            if isinstance(tree_numbers_raw, list)
            else [tree_numbers_raw]
        ):
            if isinstance(tn, str):
                tree_numbers.append(tn.split("/")[-1] if "/" in tn else tn)

        # Extract type
        entry_type = data.get("@type", "")
        if isinstance(entry_type, str):
            entry_type = (
                entry_type.split("#")[-1]
                if "#" in entry_type
                else entry_type.split("/")[-1]
            )

        # Extract consider also
        consider_also = data.get("considerAlso", {})
        if isinstance(consider_also, dict):
            consider_also = consider_also.get("@value", "")

        result = {
            "descriptor_id": data.get("identifier", descriptor_id),
            "label": label,
            "type": entry_type,
            "annotation": annotation if annotation else None,
            "tree_numbers": tree_numbers,
            "consider_also": consider_also if consider_also else None,
            "date_introduced": data.get("dateIntroduced"),
            "last_updated": data.get("lastUpdated"),
            "active": data.get("http://id.nlm.nih.gov/mesh/vocab#active"),
            "history_note": history_note if history_note else None,
            "public_mesh_note": data.get("publicMeSHNote"),
            "allowable_qualifiers": data.get("allowableQualifier", []),
            "concepts": data.get("concept", []),
            "preferred_concept": data.get("preferredConcept"),
            "preferred_term": data.get("preferredTerm"),
            "record": data,
        }

        return {
            "status": "success",
            "data": result,
            "metadata": {
                "source": "NLM MeSH",
                "query": descriptor_id,
                "returned_identifier_verified": True,
                "source_record_complete": True,
            },
        }

    def _search_terms(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search MeSH terms (entry terms/synonyms) by label."""
        query = arguments.get("query")
        if not isinstance(query, str) or not query.strip():
            return {"status": "error", "error": "query must be a non-empty string"}
        query = query.strip()

        match_type = arguments.get("match", "contains")
        limit = arguments.get("limit", 20)
        if match_type not in {"contains", "exact", "startsWith"}:
            return {"status": "error", "error": "match is not supported by MeSH lookup"}
        if (
            isinstance(limit, bool)
            or not isinstance(limit, int)
            or not 1 <= limit <= 50
        ):
            return {"status": "error", "error": "limit must be an integer from 1 to 50"}

        url = f"{MESH_LOOKUP_URL}/term"
        params = {
            "label": query,
            "match": match_type,
            "limit": limit,
        }

        response = requests.get(
            url,
            params=params,
            headers={"Accept": "application/json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, list) or any(
            not isinstance(item, dict) for item in data
        ):
            return {
                "status": "error",
                "error": "MeSH returned malformed search results",
            }

        results = []
        for item in data:
            resource_uri = item.get("resource")
            label = item.get("label")
            if (
                not isinstance(resource_uri, str)
                or not resource_uri.startswith(
                    (
                        "http://id.nlm.nih.gov/mesh/T",
                        "https://id.nlm.nih.gov/mesh/T",
                    )
                )
                or not isinstance(label, str)
            ):
                return {
                    "status": "error",
                    "error": "MeSH returned a malformed term result",
                }
            normalized_label = label.casefold()
            normalized_query = query.casefold()
            matches = {
                "exact": normalized_label == normalized_query,
                "contains": normalized_query in normalized_label,
                "startsWith": normalized_label.startswith(normalized_query),
            }
            if not matches[match_type]:
                return {
                    "status": "error",
                    "error": "MeSH returned a term that does not satisfy the requested match mode",
                    "returned_label": label,
                }
            term_id = resource_uri.rsplit("/", 1)[-1]
            if (
                not term_id.startswith("T")
                or len(term_id[1:]) not in {6, 9}
                or not term_id[1:].isdigit()
            ):
                return {
                    "status": "error",
                    "error": "MeSH returned an invalid term identifier",
                }
            results.append(
                {
                    "term_id": term_id,
                    "label": label,
                    "resource_uri": resource_uri,
                }
            )

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "source": "NLM MeSH",
                "query": query,
                "match_type": match_type,
                "returned": len(results),
                "requested_limit": limit,
                "total_results": len(results) if len(results) < limit else None,
                "total_results_known": len(results) < limit,
                "possibly_truncated": len(results) == limit,
                "result_set_complete": len(results) < limit,
                "pagination_supported": False,
                "warning": "MeSH lookup provides no total or offset; refine the query because the 50-result ceiling was reached."
                if len(results) == limit
                else None,
            },
        }
