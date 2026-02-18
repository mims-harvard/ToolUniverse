# oxo_tool.py
"""
EBI OxO (Ontology Xref Service) tool for ToolUniverse.

Provides cross-reference mappings between ontology terms across biomedical
databases including Disease Ontology, HPO, MeSH, SNOMED-CT, UMLS, OMIM,
ICD-10, NCIt, Gene Ontology, ChEBI, and many more.

API: https://www.ebi.ac.uk/spot/oxo/
No authentication required. Free public access.
"""

import requests
from typing import Dict, Any, List
from .base_tool import BaseTool


OXO_BASE_URL = "https://www.ebi.ac.uk/spot/oxo/api"


class OxOTool(BaseTool):
    """
    Tool for EBI OxO (Ontology Xref Service) API providing cross-reference
    mappings between ontology terms across biomedical databases.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "get_mappings")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the OxO API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {"error": f"OxO API timed out after {self.timeout}s"}
        except requests.exceptions.ConnectionError:
            return {"error": "Failed to connect to EBI OxO API"}
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code if e.response is not None else "unknown"
            return {"error": f"OxO API HTTP error: {code}"}
        except Exception as e:
            return {"error": f"Unexpected error querying OxO API: {str(e)}"}

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint."""
        if self.endpoint == "get_mappings":
            return self._get_mappings(arguments)
        elif self.endpoint == "search_mappings":
            return self._search_mappings(arguments)
        else:
            return {"error": f"Unknown endpoint: {self.endpoint}"}

    def _get_mappings(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get cross-reference mappings for a single ontology term."""
        term_id = arguments.get("term_id", "")
        if not term_id:
            return {"error": "term_id parameter is required (e.g., 'HP:0001250')"}

        distance = min(arguments.get("distance", 1), 3)
        size = min(arguments.get("size", 20), 100)

        url = f"{OXO_BASE_URL}/search"
        params = {
            "ids": term_id,
            "distance": distance,
            "size": size,
        }
        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        embedded = data.get("_embedded", {})
        search_results = embedded.get("searchResults", [])

        if not search_results:
            return {
                "data": {
                    "query_id": term_id,
                    "query_label": None,
                    "total_mappings": 0,
                    "mappings": [],
                },
                "metadata": {
                    "source": "EBI OxO (Ontology Xref Service)",
                    "term_id": term_id,
                    "distance": distance,
                },
            }

        result = search_results[0]
        query_source = result.get("querySource", {})
        mapping_list = result.get("mappingResponseList", [])

        mappings = []
        for m in mapping_list:
            mappings.append(
                {
                    "curie": m.get("curie", ""),
                    "label": m.get("label"),
                    "prefix": m.get("targetPrefix", ""),
                    "distance": m.get("distance", 1),
                    "source_type": m.get("sourceType"),
                }
            )

        return {
            "data": {
                "query_id": result.get("queryId", term_id),
                "query_label": query_source.get("label")
                if isinstance(query_source, dict)
                else None,
                "total_mappings": len(mappings),
                "mappings": mappings,
            },
            "metadata": {
                "source": "EBI OxO (Ontology Xref Service)",
                "term_id": term_id,
                "distance": distance,
            },
        }

    def _search_mappings(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search mappings for multiple terms at once."""
        term_ids_str = arguments.get("term_ids", "")
        if not term_ids_str:
            return {"error": "term_ids parameter is required (comma-separated list)"}

        term_ids = [t.strip() for t in term_ids_str.split(",") if t.strip()]
        distance = min(arguments.get("distance", 1), 3)
        target_prefix = arguments.get("target_prefix")

        all_results = []
        for term_id in term_ids:
            url = f"{OXO_BASE_URL}/search"
            params = {
                "ids": term_id,
                "distance": distance,
                "size": 50,
            }
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()

            embedded = data.get("_embedded", {})
            search_results = embedded.get("searchResults", [])

            mappings = []
            if search_results:
                mapping_list = search_results[0].get("mappingResponseList", [])
                for m in mapping_list:
                    # Apply target prefix filter if specified
                    if target_prefix:
                        if (
                            target_prefix.lower()
                            not in m.get("targetPrefix", "").lower()
                        ):
                            continue
                    mappings.append(
                        {
                            "curie": m.get("curie", ""),
                            "label": m.get("label"),
                            "prefix": m.get("targetPrefix", ""),
                            "distance": m.get("distance", 1),
                        }
                    )

            all_results.append(
                {
                    "query_id": term_id,
                    "mappings_count": len(mappings),
                    "mappings": mappings,
                }
            )

        return {
            "data": {
                "queries": len(term_ids),
                "results": all_results,
            },
            "metadata": {
                "source": "EBI OxO (Ontology Xref Service)",
                "term_ids": term_ids,
                "distance": distance,
                "target_prefix": target_prefix,
            },
        }
