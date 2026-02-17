# gprofiler_tool.py
"""
g:Profiler tool for ToolUniverse.

g:Profiler (University of Tartu, Estonia) provides functional enrichment analysis,
gene ID conversion, and ortholog mapping. It integrates Gene Ontology, KEGG,
Reactome, WikiPathways, Human Phenotype Ontology, miRNA targets, CORUM complexes,
and transcription factor targets.

API: https://biit.cs.ut.ee/gprofiler/api/
No authentication required.
"""

import requests
from typing import Dict, Any, Optional
from .base_tool import BaseTool
from .tool_registry import register_tool

GPROFILER_BASE_URL = "https://biit.cs.ut.ee/gprofiler/api"


@register_tool("GProfilerTool")
class GProfilerTool(BaseTool):
    """
    Tool for g:Profiler functional enrichment, ID conversion, and ortholog mapping.

    Supports:
    - g:GOSt: Functional enrichment analysis (GO, KEGG, Reactome, WP, HP, MIRNA, CORUM)
    - g:Convert: Gene ID conversion between namespaces
    - g:Orth: Cross-species ortholog mapping

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 60)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "enrichment")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the g:Profiler API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {"error": f"g:Profiler API timed out after {self.timeout}s"}
        except requests.exceptions.ConnectionError:
            return {"error": "Failed to connect to g:Profiler API"}
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else "unknown"
            return {"error": f"g:Profiler API HTTP {status}"}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint."""
        if self.endpoint == "enrichment":
            return self._enrichment(arguments)
        elif self.endpoint == "convert_ids":
            return self._convert_ids(arguments)
        elif self.endpoint == "find_orthologs":
            return self._find_orthologs(arguments)
        elif self.endpoint == "snpense":
            return self._snpense(arguments)
        else:
            return {"error": f"Unknown endpoint: {self.endpoint}"}

    def _parse_gene_list(self, gene_list_str: str):
        """Parse comma-separated gene list into a list."""
        if not gene_list_str:
            return []
        return [g.strip() for g in gene_list_str.split(",") if g.strip()]

    def _enrichment(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Perform functional enrichment analysis (g:GOSt)."""
        gene_list_str = arguments.get("gene_list", "")
        genes = self._parse_gene_list(gene_list_str)
        if not genes:
            return {
                "error": "gene_list is required. Provide comma-separated gene symbols (e.g., 'TP53,BRCA1,EGFR')."
            }

        organism = arguments.get("organism", "hsapiens")
        sources_str = arguments.get("sources", "GO:BP,GO:MF,GO:CC,KEGG,REAC,WP,HP")
        sources = [s.strip() for s in sources_str.split(",") if s.strip()]

        url = f"{GPROFILER_BASE_URL}/gost/profile/"
        payload = {
            "organism": organism,
            "query": genes,
            "sources": sources,
            "user_threshold": 0.05,
            "significance_threshold_method": "g_SCS",
            "all_results": False,
            "ordered": False,
            "no_evidences": False,
        }

        response = requests.post(url, json=payload, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        results = data.get("result", [])

        # Format results
        enriched_terms = []
        for r in results:
            enriched_terms.append(
                {
                    "source": r.get("source"),
                    "native": r.get("native"),
                    "name": r.get("name"),
                    "p_value": r.get("p_value"),
                    "significant": r.get("significant"),
                    "term_size": r.get("term_size"),
                    "query_size": r.get("query_size"),
                    "intersection_size": r.get("intersection_size"),
                    "precision": r.get("precision"),
                    "recall": r.get("recall"),
                }
            )

        return {
            "data": enriched_terms,
            "metadata": {
                "source": "g:Profiler (biit.cs.ut.ee/gprofiler) - University of Tartu",
                "organism": organism,
                "total_results": len(enriched_terms),
                "query_genes": genes,
            },
        }

    def _convert_ids(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Convert gene identifiers between namespaces (g:Convert)."""
        gene_list_str = arguments.get("gene_list", "")
        genes = self._parse_gene_list(gene_list_str)
        if not genes:
            return {
                "error": "gene_list is required. Provide comma-separated identifiers (e.g., 'TP53,BRCA1')."
            }

        target = arguments.get("target_namespace", "ENSG")
        organism = arguments.get("organism", "hsapiens")

        url = f"{GPROFILER_BASE_URL}/convert/convert/"
        payload = {
            "organism": organism,
            "query": genes,
            "target": target,
        }

        response = requests.post(url, json=payload, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        results = data.get("result", [])
        converted = []
        for r in results:
            converted.append(
                {
                    "incoming": r.get("incoming"),
                    "converted": r.get("converted"),
                    "name": r.get("name"),
                    "description": r.get("description"),
                    "namespaces": r.get("namespaces"),
                }
            )

        return {
            "data": converted,
            "metadata": {
                "source": "g:Profiler g:Convert (biit.cs.ut.ee/gprofiler)",
                "organism": organism,
                "target_namespace": target,
            },
        }

    def _find_orthologs(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Find orthologs across species (g:Orth)."""
        gene_list_str = arguments.get("gene_list", "")
        genes = self._parse_gene_list(gene_list_str)
        if not genes:
            return {
                "error": "gene_list is required. Provide comma-separated gene symbols (e.g., 'TP53,BRCA1')."
            }

        source_organism = arguments.get("source_organism", "hsapiens")
        target_organism = arguments.get("target_organism", "mmusculus")

        url = f"{GPROFILER_BASE_URL}/orth/orth/"
        payload = {
            "organism": source_organism,
            "query": genes,
            "target": target_organism,
        }

        response = requests.post(url, json=payload, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        results = data.get("result", [])
        orthologs = []
        for r in results:
            orthologs.append(
                {
                    "incoming": r.get("incoming"),
                    "name": r.get("name"),
                    "ortholog_ensg": r.get("ortholog_ensg"),
                    "description": r.get("description"),
                }
            )

        return {
            "data": orthologs,
            "metadata": {
                "source": "g:Profiler g:Orth (biit.cs.ut.ee/gprofiler)",
                "source_organism": source_organism,
                "target_organism": target_organism,
            },
        }

    def _snpense(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Map SNP rsIDs to genes and annotate consequences (g:SNPense)."""
        snp_list_str = arguments.get("snp_list", "")
        if not snp_list_str:
            return {
                "error": "snp_list is required. Provide comma-separated rsIDs (e.g., 'rs11540652,rs429358,rs7903146')."
            }

        snps = [s.strip() for s in snp_list_str.split(",") if s.strip()]
        organism = arguments.get("organism", "hsapiens")

        url = f"{GPROFILER_BASE_URL}/snpense/snpense/"
        payload = {
            "organism": organism,
            "query": snps,
        }

        response = requests.post(url, json=payload, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        results = data.get("result", [])
        annotations = []
        for r in results:
            variants = r.get("variants", {})
            variant_summary = []
            for consequence, count in variants.items():
                variant_summary.append(
                    {
                        "consequence": consequence,
                        "count": count,
                    }
                )

            annotations.append(
                {
                    "rs_id": r.get("rs_id"),
                    "chromosome": r.get("chromosome"),
                    "start": r.get("start"),
                    "end": r.get("end"),
                    "strand": r.get("strand"),
                    "ensembl_gene_ids": r.get("ensgs", []),
                    "gene_names": r.get("gene_names", []),
                    "variant_consequences": variant_summary,
                }
            )

        return {
            "data": annotations,
            "metadata": {
                "source": "g:Profiler g:SNPense (biit.cs.ut.ee/gprofiler)",
                "organism": organism,
                "total_snps_queried": len(snps),
                "total_results": len(annotations),
            },
        }
