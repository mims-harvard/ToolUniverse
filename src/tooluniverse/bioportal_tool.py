# bioportal_tool.py
"""
BioPortal (NCBO) API tool for ToolUniverse.

BioPortal is the world's most comprehensive repository of biomedical
ontologies, hosting 900+ ontologies including GO, HPO, DOID, SNOMED,
MeSH, CHEBI, and many more. It provides cross-ontology search, concept
details, hierarchical browsing, text annotation, and cross-ontology
mappings.

API: https://data.bioontology.org/
Uses public demo API key (free, no registration needed).
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

BIOPORTAL_BASE_URL = "https://data.bioontology.org"
# Public demo API key available at http://bioportal.bioontology.org/
BIOPORTAL_API_KEY = "8b5b7825-538d-40e0-9e9e-5ab9274a9aeb"


@register_tool("BioPortalTool")
class BioPortalTool(BaseTool):
    """
    Tool for querying BioPortal, the largest biomedical ontology repository.

    BioPortal hosts 900+ ontologies covering diseases (DOID, MONDO),
    phenotypes (HPO), gene function (GO), chemicals (CHEBI), anatomy
    (UBERON), drugs (RXNORM), and more.

    Supports: cross-ontology search, concept detail lookup, text annotation
    with ontology terms, and concept hierarchy traversal.

    Uses public demo API key (no registration required).
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "search")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the BioPortal API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"BioPortal API timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to BioPortal API (data.bioontology.org). The server may be blocking connections from your network or IP address.",
            }
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "error": f"BioPortal API HTTP error: {e.response.status_code}",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error querying BioPortal: {str(e)}",
            }

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate BioPortal endpoint."""
        if self.endpoint == "search":
            return self._search(arguments)
        elif self.endpoint == "get_concept":
            return self._get_concept(arguments)
        elif self.endpoint == "annotate_text":
            return self._annotate_text(arguments)
        elif self.endpoint == "get_hierarchy":
            return self._get_hierarchy(arguments)
        else:
            return {"status": "error", "error": f"Unknown endpoint: {self.endpoint}"}

    @staticmethod
    def _page_controls(arguments: Dict[str, Any], default: int, maximum: int):
        page_size = arguments.get("page_size", default)
        page = arguments.get("page", 1)
        if page_size is None:
            page_size = default
        if (
            isinstance(page_size, bool)
            or not isinstance(page_size, int)
            or not 1 <= page_size <= maximum
        ):
            return {
                "status": "error",
                "error": f"page_size must be an integer from 1 to {maximum}",
            }
        if isinstance(page, bool) or not isinstance(page, int) or page < 1:
            return {"status": "error", "error": "page must be a positive integer"}
        return page_size, page

    def _search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search across all (or specific) ontologies for terms."""
        query = arguments.get("query", "")
        if not query:
            return {"status": "error", "error": "query parameter is required"}

        ontologies = arguments.get("ontologies")
        controls = self._page_controls(arguments, 10, 50)
        if isinstance(controls, dict):
            return controls
        page_size, page = controls
        exact_match = arguments.get("exact_match", False)
        if exact_match is None:
            exact_match = False
        if not isinstance(exact_match, bool):
            return {"status": "error", "error": "exact_match must be a boolean"}

        url = f"{BIOPORTAL_BASE_URL}/search"
        params = {
            "q": query,
            "apikey": BIOPORTAL_API_KEY,
            "pagesize": page_size,
            "page": page,
            "display_links": "false",
            "display_context": "false",
        }
        if ontologies:
            params["ontologies"] = ontologies
        if exact_match:
            params["require_exact_match"] = "true"

        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()
        current_page = data.get("page", page)
        page_count = data.get("pageCount", 1)

        results = []
        for item in data.get("collection", []):
            synonyms = item.get("synonym") or []
            results.append(
                {
                    "label": item.get("prefLabel"),
                    "id": item.get("@id", "").split("/")[-1]
                    if item.get("@id")
                    else None,
                    "full_id": item.get("@id"),
                    "synonyms": synonyms,
                    "synonym_count": len(synonyms),
                    "definition": (item.get("definition") or [None])[0],
                    "ontology": item.get("@id", "").split("/obo/")[0].split("/")[-1]
                    if "/obo/" in item.get("@id", "")
                    else None,
                    "obsolete": item.get("obsolete", False),
                    "match_type": item.get("matchType"),
                }
            )

        total_count = data.get("totalCount", len(results))
        has_more = current_page < page_count
        stalled = bool(has_more and not results)
        return {
            "status": "success",
            "data": results,
            "metadata": {
                "source": "BioPortal (NCBO)",
                "total_count": total_count,
                "returned": len(results),
                "page_size": page_size,
                "page": current_page,
                "page_count": page_count,
                "has_more": has_more and not stalled,
                "next_page": current_page + 1 if has_more and not stalled else None,
                "truncated": current_page > 1 or has_more,
                "result_set_complete": current_page == 1
                and len(results) == total_count,
                "pagination_stalled": stalled,
                "warning": (
                    "BioPortal reported additional pages but returned an empty collection."
                    if stalled
                    else None
                ),
                "query": query,
            },
        }

    def _get_concept(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed information for a specific ontology concept."""
        ontology = arguments.get("ontology", "")
        concept_id = arguments.get("concept_id", "")
        if not ontology or not concept_id:
            return {
                "status": "error",
                "error": "Both ontology and concept_id are required",
            }

        # URL-encode the concept IRI (single encode only)
        import urllib.parse

        encoded_id = urllib.parse.quote(concept_id, safe="")

        url = f"{BIOPORTAL_BASE_URL}/ontologies/{ontology}/classes/{encoded_id}"
        params = {
            "apikey": BIOPORTAL_API_KEY,
            "display_links": "false",
            "display_context": "false",
        }

        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        return {
            "status": "success",
            "data": {
                "label": data.get("prefLabel"),
                "id": data.get("@id"),
                "synonyms": data.get("synonym", []),
                "definitions": data.get("definition", []),
                "obsolete": data.get("obsolete", False),
                "cui": data.get("cui", []),
                "semantic_type": data.get("semanticType", []),
            },
            "metadata": {
                "source": "BioPortal (NCBO)",
                "ontology": ontology,
            },
        }

    def _annotate_text(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Annotate biomedical text with ontology terms (named entity recognition)."""
        text = arguments.get("text", "")
        if not text:
            return {"status": "error", "error": "text parameter is required"}

        ontologies = arguments.get("ontologies")
        longest_only = arguments.get("longest_only")
        if longest_only is None:
            longest_only = True

        url = f"{BIOPORTAL_BASE_URL}/annotator"
        payload = {
            "apikey": BIOPORTAL_API_KEY,
            "text": text,
            "longest_only": str(longest_only).lower(),
            "include": "prefLabel",
            "display_links": "false",
            "display_context": "false",
        }
        if ontologies:
            payload["ontologies"] = ontologies

        response = requests.post(url, data=payload, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        annotations = []
        for ann in data:
            cls = ann.get("annotatedClass", {})
            for match in ann.get("annotations", []):
                annotations.append(
                    {
                        "matched_text": match.get("text"),
                        "from": match.get("from"),
                        "to": match.get("to"),
                        "match_type": match.get("matchType"),
                        "concept_label": cls.get("prefLabel"),
                        "concept_id": cls.get("@id", "").split("/")[-1]
                        if cls.get("@id")
                        else None,
                        "concept_full_id": cls.get("@id"),
                    }
                )

        return {
            "status": "success",
            "data": annotations,
            "metadata": {
                "source": "BioPortal Annotator (NCBO)",
                "total_annotations": len(annotations),
                "text_length": len(text),
            },
        }

    def _get_hierarchy(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get children or ancestors of an ontology concept."""
        ontology = arguments.get("ontology", "")
        concept_id = arguments.get("concept_id", "")
        direction = arguments.get("direction", "children")
        if not ontology or not concept_id:
            return {
                "status": "error",
                "error": "Both ontology and concept_id are required",
            }
        if direction is None:
            direction = "children"
        if direction not in {"children", "parents", "ancestors"}:
            return {
                "status": "error",
                "error": "direction must be children, parents, or ancestors",
            }

        import urllib.parse

        encoded_id = urllib.parse.quote(concept_id, safe="")

        if direction == "ancestors":
            url = f"{BIOPORTAL_BASE_URL}/ontologies/{ontology}/classes/{encoded_id}/ancestors"
        elif direction == "parents":
            url = f"{BIOPORTAL_BASE_URL}/ontologies/{ontology}/classes/{encoded_id}/parents"
        else:
            url = f"{BIOPORTAL_BASE_URL}/ontologies/{ontology}/classes/{encoded_id}/children"

        controls = self._page_controls(arguments, 25, 100)
        if isinstance(controls, dict):
            return controls
        page_size, page = controls
        params = {
            "apikey": BIOPORTAL_API_KEY,
            "display_links": "false",
            "display_context": "false",
            "pagesize": page_size,
            "page": page,
        }

        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        # Handle paginated vs flat list responses
        concepts = []
        if isinstance(data, list):
            items = data
            total = len(data)
            current_page = 1
            page_count = 1
        else:
            items = data.get("collection", [])
            total = data.get("totalCount", len(items))
            current_page = data.get("page", page)
            page_count = data.get("pageCount", 1)

        for item in items:
            synonyms = item.get("synonym") or []
            concepts.append(
                {
                    "label": item.get("prefLabel"),
                    "id": item.get("@id", "").split("/")[-1]
                    if item.get("@id")
                    else None,
                    "full_id": item.get("@id"),
                    "synonyms": synonyms,
                    "synonym_count": len(synonyms),
                    "definition": (item.get("definition") or [None])[0],
                    "obsolete": item.get("obsolete", False),
                }
            )

        has_more = current_page < page_count
        stalled = bool(has_more and not concepts)
        return {
            "status": "success",
            "data": concepts,
            "metadata": {
                "source": "BioPortal (NCBO)",
                "ontology": ontology,
                "direction": direction,
                "total_count": total,
                "returned": len(concepts),
                "page_size": page_size,
                "page": current_page,
                "page_count": page_count,
                "has_more": has_more and not stalled,
                "next_page": current_page + 1 if has_more and not stalled else None,
                "truncated": current_page > 1 or has_more,
                "result_set_complete": current_page == 1 and len(concepts) == total,
                "pagination_stalled": stalled,
                "warning": (
                    "BioPortal reported additional hierarchy pages but returned an empty collection."
                    if stalled
                    else None
                ),
                "concept_id": concept_id,
            },
        }
