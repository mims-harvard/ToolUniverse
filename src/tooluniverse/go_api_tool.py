# go_api_tool.py
"""
Gene Ontology (GO) REST API tool for ToolUniverse.

The Gene Ontology provides a standardized framework for describing gene
and gene product attributes across species. The GO API provides programmatic
access to ontology terms, gene annotations, and functional associations.

API: https://api.geneontology.org/api/
No authentication required. Free public access.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

GO_BASE_URL = "https://api.geneontology.org/api"


@register_tool("GOAPITool")
class GOAPITool(BaseTool):
    """
    Tool for querying the Gene Ontology (GO) REST API.

    The GO API provides access to three major ontology domains:
    - Biological Process (BP): cellular/organismal processes
    - Molecular Function (MF): molecular-level activities
    - Cellular Component (CC): locations of gene products

    Supports: GO term lookup, gene GO annotations, gene function associations.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "term")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the GO API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"GO API timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {"status": "error", "error": "Failed to connect to GO API"}
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "error": f"GO API HTTP error: {e.response.status_code}",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error querying GO API: {str(e)}",
            }

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate GO endpoint."""
        if self.endpoint == "term":
            return self._get_term(arguments)
        elif self.endpoint == "gene_functions":
            return self._get_gene_functions(arguments)
        elif self.endpoint == "search_annotations":
            return self._search_annotations(arguments)
        else:
            return {"status": "error", "error": f"Unknown endpoint: {self.endpoint}"}

    def _get_term(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get GO term details by GO ID."""
        go_id = arguments.get("go_id", "")
        if not go_id:
            return {
                "status": "error",
                "error": "go_id parameter is required (e.g., GO:0006915)",
            }

        # Normalize GO ID
        if not go_id.startswith("GO:"):
            go_id = f"GO:{go_id}"

        url = f"{GO_BASE_URL}/ontology/term/{go_id}"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        # Clean up synonyms (they have @ artifacts)
        synonyms = [s.strip("@").strip() for s in data.get("synonyms", [])]
        related_synonyms = [
            s.strip("@").strip() for s in data.get("relatedSynonyms", [])
        ]

        return {
            "status": "success",
            "data": {
                "go_id": data.get("goid"),
                "label": data.get("label"),
                "definition": data.get("definition"),
                "synonyms": synonyms,
                "related_synonyms": related_synonyms,
                "xrefs": [x.strip("@").strip() for x in data.get("xrefs", [])],
                "alternative_ids": [
                    a.strip("@").strip() for a in data.get("alternativeIds", [])
                ],
            },
            "metadata": {
                "source": "Gene Ontology (GO)",
            },
        }

    def _get_gene_functions(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get GO annotations (functions/processes/components) for a gene."""
        gene_id = arguments.get("gene_id", "")
        if not gene_id:
            return {
                "status": "error",
                "error": "gene_id parameter is required (e.g., HGNC:11998 or UniProtKB:P04637)",
            }

        rows = arguments.get("rows") or 20
        aspect = arguments.get("aspect")  # P=process, F=function, C=component

        url = f"{GO_BASE_URL}/bioentity/gene/{gene_id}/function"
        params = {"rows": min(rows, 100)}
        if aspect:
            params["fq"] = f'aspect:"{aspect}"'

        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        associations = []
        for a in data.get("associations", []):
            obj = a.get("object", {})
            categories = obj.get("category", [])
            category = categories[0] if categories else None

            associations.append(
                {
                    "go_id": obj.get("id"),
                    "go_label": obj.get("label"),
                    "category": category,
                    "evidence_type": a.get("evidence_type"),
                    "evidence_label": a.get("evidence_label"),
                    "provided_by": a.get("provided_by", []),
                    "references": a.get("reference", []),
                }
            )

        return {
            "status": "success",
            "data": associations,
            "metadata": {
                "source": "Gene Ontology (GO)",
                "gene_id": gene_id,
                "total_results": data.get("numFound", len(associations)),
            },
        }

    def _search_annotations(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search for genes annotated with a specific GO term."""
        go_id = arguments.get("go_id", "")
        if not go_id:
            return {
                "status": "error",
                "error": "go_id parameter is required (e.g., GO:0006915)",
            }

        if not go_id.startswith("GO:"):
            go_id = f"GO:{go_id}"

        rows = arguments.get("rows") or 20
        taxon = arguments.get("taxon")  # e.g., NCBITaxon:9606

        url = f"{GO_BASE_URL}/bioentity/function/{go_id}/genes"
        params = {"rows": min(rows, 100)}
        if taxon:
            params["taxon"] = taxon

        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        genes = []
        for a in data.get("associations", []):
            subj = a.get("subject", {})
            taxon_info = subj.get("taxon", {})

            genes.append(
                {
                    "gene_id": subj.get("id"),
                    "gene_label": subj.get("label"),
                    "taxon_id": taxon_info.get("id"),
                    "taxon_label": taxon_info.get("label"),
                    "evidence_type": a.get("evidence_type"),
                    "references": a.get("reference", []),
                }
            )

        return {
            "status": "success",
            "data": genes,
            "metadata": {
                "source": "Gene Ontology (GO)",
                "go_id": go_id,
                "total_results": data.get("numFound", len(genes)),
            },
        }
