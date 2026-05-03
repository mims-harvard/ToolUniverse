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

import requests
from typing import Dict, Any
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
        query = arguments.get("query", "")
        if not query:
            return {"status": "error", "error": "query parameter is required"}

        match_type = arguments.get("match", "contains")
        limit = arguments.get("limit", 20)

        url = f"{MESH_LOOKUP_URL}/descriptor"
        params = {
            "label": query,
            "match": match_type,
            "limit": min(limit, 50),
        }

        response = requests.get(
            url,
            params=params,
            headers={"Accept": "application/json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()

        results = []
        for item in data:
            resource_uri = item.get("resource", "")
            # Extract descriptor ID from URI (e.g., http://id.nlm.nih.gov/mesh/D009369 -> D009369)
            descriptor_id = resource_uri.split("/")[-1] if resource_uri else None
            results.append(
                {
                    "descriptor_id": descriptor_id,
                    "label": item.get("label"),
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
                "total_results": len(results),
            },
        }

    def _get_descriptor(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed information for a MeSH descriptor by its ID."""
        descriptor_id = arguments.get("descriptor_id", "")
        if not descriptor_id:
            return {
                "status": "error",
                "error": "descriptor_id parameter is required (e.g. D009369 for Neoplasms)",
            }

        url = f"{MESH_BASE_URL}/{descriptor_id}.json"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

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
        }

        return {
            "status": "success",
            "data": result,
            "metadata": {
                "source": "NLM MeSH",
                "query": descriptor_id,
            },
        }

    def _search_terms(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search MeSH terms (entry terms/synonyms) by label."""
        query = arguments.get("query", "")
        if not query:
            return {"status": "error", "error": "query parameter is required"}

        match_type = arguments.get("match", "contains")
        limit = arguments.get("limit", 20)

        url = f"{MESH_LOOKUP_URL}/term"
        params = {
            "label": query,
            "match": match_type,
            "limit": min(limit, 50),
        }

        response = requests.get(
            url,
            params=params,
            headers={"Accept": "application/json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()

        results = []
        for item in data:
            resource_uri = item.get("resource", "")
            term_id = resource_uri.split("/")[-1] if resource_uri else None
            results.append(
                {
                    "term_id": term_id,
                    "label": item.get("label"),
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
                "total_results": len(results),
            },
        }
