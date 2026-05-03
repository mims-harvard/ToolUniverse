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
        else:
            return {"status": "error", "error": f"Unknown endpoint: {self.endpoint}"}

    def _search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search NCI Thesaurus by term."""
        term = arguments.get("term", "")
        if not term:
            return {"status": "error", "error": "term parameter is required"}

        page_size = arguments.get("page_size") or 10

        url = f"{NCI_BASE_URL}/concept/ncit/search"
        params = {
            "term": term,
            "type": "match",
            "include": "minimal",
            "pageSize": min(page_size, 100),
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

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "source": "NCI Thesaurus (NCIt)",
                "total_results": data.get("total", len(results)),
                "query": term,
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
        definition = definitions[0].get("definition") if definitions else None

        # Extract synonyms
        synonyms_raw = data.get("synonyms", [])
        synonyms = []
        for s in synonyms_raw:
            synonyms.append(
                {
                    "name": s.get("name", ""),
                    "type": s.get("termType"),
                    "source": s.get("source"),
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
                }
            )

        return {
            "status": "success",
            "data": {
                "code": data.get("code", ""),
                "name": data.get("name", ""),
                "definition": definition,
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
