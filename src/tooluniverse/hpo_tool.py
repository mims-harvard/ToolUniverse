# hpo_tool.py
"""
Human Phenotype Ontology (HPO) API tool for ToolUniverse.

HPO provides a standardized vocabulary of phenotypic abnormalities
encountered in human disease. Each term describes a phenotypic
feature (sign, symptom, or finding) and is organized in a directed
acyclic graph (DAG) hierarchy.

API: https://ontology.jax.org/api/
No authentication required. Free public access.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

HPO_BASE_URL = "https://ontology.jax.org/api/hp"


@register_tool("HPOTool")
class HPOTool(BaseTool):
    """
    Tool for querying the Human Phenotype Ontology (HPO) at JAX.

    HPO provides structured phenotype terms used in clinical genetics,
    rare disease research, and differential diagnosis. Each term has
    definitions, synonyms, cross-references, and hierarchical relationships.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "get_term")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the HPO API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"HPO API request timed out after {self.timeout} seconds",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to HPO API. Check network connectivity.",
            }
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "error": f"HPO API HTTP error: {e.response.status_code}",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error querying HPO: {str(e)}",
            }

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate HPO endpoint."""
        if self.endpoint == "get_term":
            return self._get_term(arguments)
        elif self.endpoint == "search_terms":
            return self._search_terms(arguments)
        elif self.endpoint == "get_term_hierarchy":
            return self._get_term_hierarchy(arguments)
        else:
            return {"status": "error", "error": f"Unknown endpoint: {self.endpoint}"}

    def _get_term(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed information about an HPO term by its ID."""
        term_id = arguments.get("term_id", "")
        if not term_id:
            return {
                "status": "error",
                "error": "term_id parameter is required (e.g., 'HP:0001250')",
            }

        # Normalize the ID format
        if not term_id.startswith("HP:"):
            term_id = f"HP:{term_id}"

        url = f"{HPO_BASE_URL}/terms/{term_id}"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        result = {
            "id": data.get("id"),
            "name": data.get("name"),
            "definition": data.get("definition"),
            "comment": data.get("comment"),
            "synonyms": data.get("synonyms", []),
            "descendant_count": data.get("descendantCount"),
            "xrefs": data.get("xrefs", []),
        }

        # Extract translations if available
        translations = data.get("translations", [])
        if translations:
            result["translations"] = [
                {"language": t.get("language"), "name": t.get("name")}
                for t in translations[:5]
                if t and t.get("name")
            ]

        return {
            "status": "success",
            "data": result,
            "metadata": {
                "source": "HPO (JAX Ontology)",
                "term_id": term_id,
            },
        }

    def _search_terms(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search for HPO terms by keyword."""
        query = arguments.get("query", "")
        if not query:
            return {"status": "error", "error": "query parameter is required"}

        max_results = arguments.get("max_results", 10)
        if max_results > 50:
            max_results = 50

        url = f"{HPO_BASE_URL}/search"
        params = {"q": query, "max": max_results}

        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        terms = data.get("terms", [])
        results = []
        for term in terms:
            results.append(
                {
                    "id": term.get("id"),
                    "name": term.get("name"),
                    "definition": term.get("definition"),
                    "descendant_count": term.get("descendantCount"),
                    "synonyms": term.get("synonyms", [])[:5],
                }
            )

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "source": "HPO (JAX Ontology)",
                "query": query,
                "total_results": len(results),
            },
        }

    def _get_term_hierarchy(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get parent and child terms in the HPO hierarchy."""
        term_id = arguments.get("term_id", "")
        if not term_id:
            return {
                "status": "error",
                "error": "term_id parameter is required (e.g., 'HP:0001250')",
            }

        if not term_id.startswith("HP:"):
            term_id = f"HP:{term_id}"

        direction = arguments.get("direction", "children")

        url = f"{HPO_BASE_URL}/terms/{term_id}/{direction}"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        results = []
        if isinstance(data, list):
            for term in data:
                results.append(
                    {
                        "id": term.get("id"),
                        "name": term.get("name"),
                    }
                )

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "source": "HPO (JAX Ontology)",
                "term_id": term_id,
                "direction": direction,
                "total_results": len(results),
            },
        }
