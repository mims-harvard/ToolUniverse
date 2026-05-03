# panther_tool.py
"""
PANTHER REST API tool for ToolUniverse.

PANTHER (Protein ANalysis THrough Evolutionary Relationships) classifies
proteins and their genes by function using a library of phylogenetic trees.
It provides gene functional classification, pathway analysis, and
overrepresentation (enrichment) analysis for gene lists.

API: https://pantherdb.org/services/oai/pantherdb/
No authentication required. Free for all use.
Supports 144 organisms.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

PANTHER_BASE_URL = "https://pantherdb.org/services/oai/pantherdb"


@register_tool("PANTHERTool")
class PANTHERTool(BaseTool):
    """
    Tool for querying PANTHER gene classification and enrichment analysis.

    Provides gene functional annotation, overrepresentation analysis
    with GO/pathway enrichment, and ortholog mapping across 144 organisms.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 60)
        self.endpoint_type = tool_config.get("fields", {}).get(
            "endpoint_type", "gene_info"
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the PANTHER API call."""
        try:
            return self._dispatch(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"PANTHER API request timed out after {self.timeout} seconds",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to PANTHER API. Check network connectivity.",
            }
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "error": f"PANTHER API HTTP error: {e.response.status_code}",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error querying PANTHER: {str(e)}",
            }

    def _dispatch(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint based on config."""
        if self.endpoint_type == "gene_info":
            return self._gene_info(arguments)
        elif self.endpoint_type == "enrichment":
            return self._enrichment(arguments)
        elif self.endpoint_type == "ortholog":
            return self._ortholog(arguments)
        else:
            return {
                "status": "error",
                "error": f"Unknown endpoint_type: {self.endpoint_type}",
            }

    def _gene_info(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get gene classification and functional annotation from PANTHER."""
        gene_id = arguments.get("gene_id", "")
        organism = arguments.get("organism", 9606)
        if not gene_id:
            return {
                "status": "error",
                "error": "gene_id parameter is required (e.g., 'P04637' for TP53)",
            }
        if organism is None:
            organism = 9606

        url = f"{PANTHER_BASE_URL}/geneinfo"
        params = {
            "geneInputList": gene_id,
            "organism": organism,
            "type": "ortholog",
        }

        response = requests.get(
            url,
            params=params,
            headers={"Accept": "application/json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        raw = response.json()

        search = raw.get("search", {})
        mapped = search.get("mapped_genes", {})
        gene_data = mapped.get("gene", {})

        # Handle both single gene (dict) and multiple genes (list)
        if isinstance(gene_data, list):
            gene_data = gene_data[0] if gene_data else {}

        family_id = gene_data.get("family_id", None)
        sf_id = gene_data.get("sf_id", None)

        # Extract annotations by category
        annotations = []
        ann_type_list = gene_data.get("annotation_type_list", {}).get(
            "annotation_data_type", []
        )
        if isinstance(ann_type_list, dict):
            ann_type_list = [ann_type_list]

        for ann_type in ann_type_list:
            category = ann_type.get("content", "")
            ann_list = ann_type.get("annotation_list", {}).get("annotation", [])
            if isinstance(ann_list, dict):
                ann_list = [ann_list]

            terms = []
            for ann in ann_list:
                terms.append(
                    {
                        "id": ann.get("id", ""),
                        "name": ann.get("name", ""),
                    }
                )

            if terms:
                annotations.append(
                    {
                        "category": category,
                        "terms": terms,
                    }
                )

        result = {
            "gene_id": gene_id,
            "organism": organism,
            "family_id": family_id,
            "subfamily_id": sf_id,
            "annotations": annotations,
        }

        return {
            "status": "success",
            "data": result,
            "metadata": {
                "source": "PANTHER",
                "query": gene_id,
                "endpoint": "geneinfo",
            },
        }

    def _enrichment(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Perform gene set enrichment (overrepresentation) analysis."""
        gene_list = arguments.get("gene_list", "")
        organism = arguments.get("organism", 9606)
        annotation_dataset = arguments.get("annotation_dataset", "GO:0008150")

        if not gene_list:
            return {
                "status": "error",
                "error": "gene_list parameter is required (e.g., 'TP53,BRCA1,EGFR,KRAS')",
            }
        if organism is None:
            organism = 9606
        if annotation_dataset is None:
            annotation_dataset = "GO:0008150"

        url = f"{PANTHER_BASE_URL}/enrich/overrep"
        params = {
            "geneInputList": gene_list,
            "organism": organism,
            "annotDataSet": annotation_dataset,
            "enrichmentTestType": "FISHER",
            "correction": "FDR",
        }

        response = requests.get(
            url,
            params=params,
            headers={"Accept": "application/json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        raw = response.json()

        results = raw.get("results", {}).get("result", [])
        if isinstance(results, dict):
            results = [results]

        # Filter to significant results (FDR < 0.05) and sort by fold enrichment
        enriched = []
        for r in results:
            fdr = r.get("fdr", 1.0)
            if fdr is None or not isinstance(fdr, (int, float)):
                continue
            fold = r.get("fold_enrichment", 0)
            if fold is None or not isinstance(fold, (int, float)):
                continue

            term = r.get("term", {})
            enriched.append(
                {
                    "term_id": term.get("id", ""),
                    "term_label": term.get("label", ""),
                    "number_in_list": r.get("number_in_list", 0),
                    "number_in_reference": r.get("number_in_reference", 0),
                    "expected": r.get("expected", 0.0),
                    "fold_enrichment": fold,
                    "pvalue": r.get("pValue", 1.0),
                    "fdr": fdr,
                    "direction": r.get("plus_minus", ""),
                }
            )

        # Sort by FDR then fold enrichment
        enriched.sort(key=lambda x: (x["fdr"], -x["fold_enrichment"]))

        # Return top 50 most significant
        enriched_top = enriched[:50]

        result = {
            "gene_list": gene_list,
            "organism": organism,
            "annotation_dataset": annotation_dataset,
            "result_count": len(enriched_top),
            "enriched_terms": enriched_top,
        }

        return {
            "status": "success",
            "data": result,
            "metadata": {
                "source": "PANTHER",
                "query": gene_list,
                "endpoint": "enrich/overrep",
            },
        }

    def _ortholog(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Find orthologs of a gene across species."""
        gene_id = arguments.get("gene_id", "")
        organism = arguments.get("organism", 9606)
        target_organism = arguments.get("target_organism", 10090)
        ortholog_type = arguments.get("ortholog_type", "LDO")

        if not gene_id:
            return {
                "status": "error",
                "error": "gene_id parameter is required (e.g., 'P04637' for TP53)",
            }
        if organism is None:
            organism = 9606
        if target_organism is None:
            target_organism = 10090
        if ortholog_type is None:
            ortholog_type = "LDO"

        url = f"{PANTHER_BASE_URL}/ortholog/matchortho"
        params = {
            "geneInputList": gene_id,
            "organism": organism,
            "targetOrganism": target_organism,
            "orthologType": ortholog_type,
        }

        response = requests.get(
            url,
            params=params,
            headers={"Accept": "application/json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        raw = response.json()

        search = raw.get("search", {})
        mapping_data = search.get("mapping", {})
        mapped = mapping_data.get("mapped", {})

        mapping = None
        if mapped:
            # Handle single mapping (dict) or multiple (list)
            if isinstance(mapped, list):
                mapped = mapped[0] if mapped else {}

            mapping = {
                "source_gene": mapped.get("gene", ""),
                "target_gene": mapped.get("target_gene", ""),
                "target_gene_symbol": mapped.get("target_gene_symbol", None),
                "ortholog_type": mapped.get("ortholog", ""),
                "persistent_id": mapped.get("persistent_id", None),
                "target_persistent_id": mapped.get("target_persistent_id", None),
            }

        result = {
            "gene_id": gene_id,
            "source_organism": organism,
            "target_organism": target_organism,
            "ortholog_type": ortholog_type,
            "mapping": mapping,
        }

        return {
            "status": "success",
            "data": result,
            "metadata": {
                "source": "PANTHER",
                "query": gene_id,
                "endpoint": "ortholog/matchortho",
            },
        }
