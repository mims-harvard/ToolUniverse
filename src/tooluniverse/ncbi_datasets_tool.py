# ncbi_datasets_tool.py
"""
NCBI Datasets API v2 tool for ToolUniverse.

NCBI Datasets provides programmatic access to gene, genome, and taxonomy
data from NCBI. The API covers gene metadata, gene orthologs, genome
assembly reports, and taxonomic classification across all organisms.

API: https://api.ncbi.nlm.nih.gov/datasets/v2
No authentication required (optional API key for higher rate limits).
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

NCBI_DATASETS_BASE = "https://api.ncbi.nlm.nih.gov/datasets/v2"


@register_tool("NCBIDatasetsTool")
class NCBIDatasetsTool(BaseTool):
    """
    Tool for querying the NCBI Datasets API v2.

    Provides access to gene information by ID/symbol, gene orthologs,
    genome assembly reports by taxon, taxonomy details by taxon ID,
    and taxonomy name suggestions.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        self.endpoint_type = tool_config.get("fields", {}).get(
            "endpoint_type", "gene_by_id"
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the NCBI Datasets API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"NCBI Datasets API request timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to NCBI Datasets API. Check network connectivity.",
            }
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "error": f"NCBI Datasets API HTTP error: {e.response.status_code}",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error querying NCBI Datasets: {str(e)}",
            }

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to the appropriate NCBI Datasets endpoint."""
        endpoint_type = self.endpoint_type

        if endpoint_type == "gene_by_id":
            return self._get_gene_by_id(arguments)
        elif endpoint_type == "gene_by_symbol":
            return self._get_gene_by_symbol(arguments)
        elif endpoint_type == "gene_orthologs":
            return self._get_gene_orthologs(arguments)
        elif endpoint_type == "taxonomy":
            return self._get_taxonomy(arguments)
        elif endpoint_type == "taxonomy_suggest":
            return self._get_taxonomy_suggest(arguments)
        elif endpoint_type == "genome_assembly":
            return self._get_genome_assembly(arguments)
        elif endpoint_type == "genomes_by_taxon":
            return self._list_genomes_by_taxon(arguments)
        elif endpoint_type == "sequence_reports":
            return self._get_sequence_reports(arguments)
        else:
            return {
                "status": "error",
                "error": f"Unknown endpoint type: {endpoint_type}",
            }

    def _get_gene_by_id(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get gene information by NCBI Gene ID."""
        gene_id = arguments.get("gene_id", "")
        if not gene_id:
            return {"status": "error", "error": "gene_id parameter is required"}

        url = f"{NCBI_DATASETS_BASE}/gene/id/{gene_id}"
        response = requests.get(
            url, headers={"Accept": "application/json"}, timeout=self.timeout
        )
        response.raise_for_status()
        result = response.json()

        reports = result.get("reports", [])
        if not reports:
            return {
                "status": "success",
                "data": {},
                "metadata": {"total_results": 0, "query_gene_id": str(gene_id)},
            }

        gene_data = reports[0].get("gene", {})
        return {
            "status": "success",
            "data": {
                "gene_id": gene_data.get("gene_id"),
                "symbol": gene_data.get("symbol"),
                "description": gene_data.get("description"),
                "tax_id": gene_data.get("tax_id"),
                "taxname": gene_data.get("taxname"),
                "common_name": gene_data.get("common_name"),
                "type": gene_data.get("type"),
                "chromosomes": gene_data.get("chromosomes", []),
                "orientation": gene_data.get("orientation"),
                "swiss_prot_accessions": gene_data.get("swiss_prot_accessions", []),
                "ensembl_gene_ids": gene_data.get("ensembl_gene_ids", []),
                "omim_ids": gene_data.get("omim_ids", []),
                "synonyms": gene_data.get("synonyms", []),
                "nomenclature_authority": gene_data.get("nomenclature_authority"),
                "genomic_locations": self._extract_locations(gene_data),
            },
            "metadata": {
                "total_results": len(reports),
                "query_gene_id": str(gene_id),
                "source": "NCBI Datasets API v2",
            },
        }

    def _get_gene_by_symbol(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get gene information by gene symbol and taxon."""
        symbol = arguments.get("symbol", "")
        taxon = arguments.get("taxon", "human")
        if not symbol:
            return {"status": "error", "error": "symbol parameter is required"}

        url = f"{NCBI_DATASETS_BASE}/gene/symbol/{symbol}/taxon/{taxon}"
        response = requests.get(
            url, headers={"Accept": "application/json"}, timeout=self.timeout
        )
        response.raise_for_status()
        result = response.json()

        reports = result.get("reports", [])
        if not reports:
            return {
                "status": "success",
                "data": [],
                "metadata": {
                    "total_results": 0,
                    "query_symbol": symbol,
                    "query_taxon": taxon,
                },
            }

        genes = []
        for report in reports:
            gene_data = report.get("gene", {})
            genes.append(
                {
                    "gene_id": gene_data.get("gene_id"),
                    "symbol": gene_data.get("symbol"),
                    "description": gene_data.get("description"),
                    "tax_id": gene_data.get("tax_id"),
                    "taxname": gene_data.get("taxname"),
                    "type": gene_data.get("type"),
                    "chromosomes": gene_data.get("chromosomes", []),
                    "swiss_prot_accessions": gene_data.get("swiss_prot_accessions", []),
                    "ensembl_gene_ids": gene_data.get("ensembl_gene_ids", []),
                    "synonyms": gene_data.get("synonyms", []),
                }
            )

        return {
            "status": "success",
            "data": genes,
            "metadata": {
                "total_results": len(genes),
                "query_symbol": symbol,
                "query_taxon": taxon,
                "source": "NCBI Datasets API v2",
            },
        }

    def _get_gene_orthologs(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get orthologs for a gene by NCBI Gene ID."""
        gene_id = arguments.get("gene_id", "")
        if not gene_id:
            return {"status": "error", "error": "gene_id parameter is required"}

        page_size = arguments.get("page_size", 20)
        url = f"{NCBI_DATASETS_BASE}/gene/id/{gene_id}/orthologs"
        params = {"page_size": min(int(page_size), 100)}

        response = requests.get(
            url,
            params=params,
            headers={"Accept": "application/json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        result = response.json()

        reports = result.get("reports", [])
        orthologs = []
        for report in reports:
            gene_data = report.get("gene", {})
            orthologs.append(
                {
                    "gene_id": gene_data.get("gene_id"),
                    "symbol": gene_data.get("symbol"),
                    "description": gene_data.get("description"),
                    "tax_id": gene_data.get("tax_id"),
                    "taxname": gene_data.get("taxname"),
                    "common_name": gene_data.get("common_name"),
                    "type": gene_data.get("type"),
                    "chromosomes": gene_data.get("chromosomes", []),
                }
            )

        return {
            "status": "success",
            "data": orthologs,
            "metadata": {
                "total_results": len(orthologs),
                "query_gene_id": str(gene_id),
                "source": "NCBI Datasets API v2",
            },
        }

    def _get_taxonomy(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get taxonomy information by NCBI Taxonomy ID."""
        tax_id = arguments.get("tax_id", "")
        if not tax_id:
            return {"status": "error", "error": "tax_id parameter is required"}

        url = f"{NCBI_DATASETS_BASE}/taxonomy/taxon/{tax_id}"
        response = requests.get(
            url, headers={"Accept": "application/json"}, timeout=self.timeout
        )
        response.raise_for_status()
        result = response.json()

        nodes = result.get("taxonomy_nodes", [])
        if not nodes:
            return {
                "status": "success",
                "data": {},
                "metadata": {"total_results": 0, "query_tax_id": str(tax_id)},
            }

        tax_data = nodes[0].get("taxonomy", {})
        return {
            "status": "success",
            "data": {
                "tax_id": tax_data.get("tax_id"),
                "organism_name": tax_data.get("organism_name"),
                "genbank_common_name": tax_data.get("genbank_common_name"),
                "rank": tax_data.get("rank"),
                "blast_name": tax_data.get("blast_name"),
                "lineage": tax_data.get("lineage", []),
                "children": tax_data.get("children", []),
                "counts": tax_data.get("counts", []),
            },
            "metadata": {
                "total_results": len(nodes),
                "query_tax_id": str(tax_id),
                "source": "NCBI Datasets API v2",
            },
        }

    def _get_taxonomy_suggest(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Suggest taxonomy names matching a query string."""
        query = arguments.get("query", "")
        if not query:
            return {"status": "error", "error": "query parameter is required"}

        url = f"{NCBI_DATASETS_BASE}/taxonomy/taxon_suggest/{query}"
        response = requests.get(
            url, headers={"Accept": "application/json"}, timeout=self.timeout
        )
        response.raise_for_status()
        result = response.json()

        suggestions = result.get("sci_name_and_ids", [])
        items = []
        for s in suggestions:
            items.append(
                {
                    "scientific_name": s.get("sci_name"),
                    "tax_id": s.get("tax_id"),
                    "common_name": s.get("common_name"),
                    "rank": s.get("rank"),
                    "group_name": s.get("group_name"),
                    "matched_term": s.get("matched_term"),
                }
            )

        return {
            "status": "success",
            "data": items,
            "metadata": {
                "total_results": len(items),
                "query": query,
                "source": "NCBI Datasets API v2",
            },
        }

    @staticmethod
    def _summarize_assembly(report: Dict[str, Any]) -> Dict[str, Any]:
        """Curate a genome dataset_report record into key assembly fields."""
        info = report.get("assembly_info", {})
        stats = report.get("assembly_stats", {})
        org = report.get("organism", {})
        ann = report.get("annotation_info", {})
        return {
            "accession": report.get("accession"),
            "paired_accession": report.get("paired_accession"),
            "source_database": report.get("source_database"),
            "organism_name": org.get("organism_name"),
            "tax_id": org.get("tax_id"),
            "strain": (org.get("infraspecific_names") or {}).get("strain"),
            "assembly_name": info.get("assembly_name"),
            "assembly_level": info.get("assembly_level"),
            "assembly_status": info.get("assembly_status"),
            "refseq_category": info.get("refseq_category"),
            "release_date": info.get("release_date"),
            "submitter": info.get("submitter"),
            "bioproject_accession": info.get("bioproject_accession"),
            "total_sequence_length": stats.get("total_sequence_length"),
            "number_of_chromosomes": stats.get("total_number_of_chromosomes"),
            "number_of_contigs": stats.get("number_of_contigs"),
            "contig_n50": stats.get("contig_n50"),
            "scaffold_n50": stats.get("scaffold_n50"),
            "gc_percent": stats.get("gc_percent"),
            "annotation_provider": ann.get("provider"),
            "annotation_name": ann.get("name"),
        }

    def _get_genome_assembly(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get genome assembly metadata by assembly accession (GCF_/GCA_)."""
        accession = (arguments.get("accession") or "").strip()
        if not accession:
            return {"status": "error", "error": "accession parameter is required"}

        url = f"{NCBI_DATASETS_BASE}/genome/accession/{accession}/dataset_report"
        response = requests.get(
            url, headers={"Accept": "application/json"}, timeout=self.timeout
        )
        response.raise_for_status()
        reports = response.json().get("reports", []) or []
        if not reports:
            return {
                "status": "success",
                "data": {},
                "metadata": {"total_results": 0, "query_accession": accession},
            }
        return {
            "status": "success",
            "data": self._summarize_assembly(reports[0]),
            "metadata": {
                "total_results": len(reports),
                "query_accession": accession,
                "source": "NCBI Datasets API v2",
            },
        }

    def _list_genomes_by_taxon(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List genome assemblies for a taxon (tax id or scientific name)."""
        taxon = str(arguments.get("taxon") or "").strip()
        if not taxon:
            return {"status": "error", "error": "taxon parameter is required"}
        try:
            page_size = int(arguments.get("limit") or 20)
        except (TypeError, ValueError):
            page_size = 20
        page_size = max(1, min(page_size, 100))

        url = f"{NCBI_DATASETS_BASE}/genome/taxon/{taxon}/dataset_report"
        params = {"page_size": page_size}
        ref_only = arguments.get("reference_only")
        if ref_only:
            params["filters.reference_only"] = "true"
        response = requests.get(
            url,
            params=params,
            headers={"Accept": "application/json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        result = response.json()
        reports = result.get("reports", []) or []
        return {
            "status": "success",
            "data": [self._summarize_assembly(r) for r in reports],
            "metadata": {
                "total_available": result.get("total_count"),
                "returned": len(reports),
                "query_taxon": taxon,
                "page_size": page_size,
                "source": "NCBI Datasets API v2",
            },
        }

    def _get_sequence_reports(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get per-sequence (chromosome/scaffold) reports for an assembly."""
        accession = (arguments.get("accession") or "").strip()
        if not accession:
            return {"status": "error", "error": "accession parameter is required"}

        url = f"{NCBI_DATASETS_BASE}/genome/accession/{accession}/sequence_reports"
        response = requests.get(
            url, headers={"Accept": "application/json"}, timeout=self.timeout
        )
        response.raise_for_status()
        reports = response.json().get("reports", []) or []
        sequences = [
            {
                "chr_name": s.get("chr_name"),
                "sequence_name": s.get("sequence_name"),
                "role": s.get("role"),
                "location_type": s.get("assigned_molecule_location_type"),
                "refseq_accession": s.get("refseq_accession"),
                "genbank_accession": s.get("genbank_accession"),
                "length": s.get("length"),
                "gc_percent": s.get("gc_percent"),
            }
            for s in reports
        ]
        return {
            "status": "success",
            "data": sequences,
            "metadata": {
                "total_results": len(sequences),
                "query_accession": accession,
                "source": "NCBI Datasets API v2",
            },
        }

    def _extract_locations(self, gene_data: Dict[str, Any]) -> list:
        """Extract genomic location information from annotations."""
        locations = []
        for ann in gene_data.get("annotations", []):
            for loc in ann.get("genomic_locations", []):
                genomic_range = loc.get("genomic_range", {})
                locations.append(
                    {
                        "assembly": ann.get("assembly_name"),
                        "accession": loc.get("genomic_accession_version"),
                        "chromosome": loc.get("sequence_name"),
                        "begin": genomic_range.get("begin"),
                        "end": genomic_range.get("end"),
                        "orientation": genomic_range.get("orientation"),
                    }
                )
        return locations
