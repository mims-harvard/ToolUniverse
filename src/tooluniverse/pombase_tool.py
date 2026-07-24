# pombase_tool.py
"""
PomBase REST API tool for ToolUniverse.

PomBase is the comprehensive database for the fission yeast
Schizosaccharomyces pombe. It provides curated gene information,
protein domains, phenotypes, GO annotations, and interactions.
Complements SGD (budding yeast S. cerevisiae).

API: https://www.pombase.org/api/v1/dataset/latest/data
No authentication required. Free for academic/research use.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

POMBASE_BASE_URL = "https://www.pombase.org/api/v1/dataset/latest/data"


@register_tool("PomBaseTool")
class PomBaseTool(BaseTool):
    """
    Tool for querying PomBase, the S. pombe genome database.

    Provides detailed gene information for fission yeast including
    protein domains, GO annotations, phenotypes, and more.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        self.endpoint_type = tool_config.get("fields", {}).get(
            "endpoint_type", "gene_detail"
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the PomBase API call."""
        try:
            return self._dispatch(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"PomBase API request timed out after {self.timeout} seconds",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to PomBase API. Check network connectivity.",
            }
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "error": f"PomBase API HTTP error: {e.response.status_code}",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error querying PomBase: {str(e)}",
            }

    def _dispatch(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint based on config."""
        if self.endpoint_type == "gene_detail":
            return self._gene_detail(arguments)
        elif self.endpoint_type == "gene_summary_search":
            return self._gene_summary_search(arguments)
        elif self.endpoint_type == "gene_phenotypes":
            return self._gene_phenotypes(arguments)
        elif self.endpoint_type == "gene_orthologs":
            return self._gene_orthologs(arguments)
        elif self.endpoint_type == "gene_interactions":
            return self._gene_interactions(arguments)
        elif self.endpoint_type == "gene_go_annotations":
            return self._gene_go_annotations(arguments)
        else:
            return {
                "status": "error",
                "error": f"Unknown endpoint_type: {self.endpoint_type}",
            }

    def _gene_detail(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed gene information from PomBase by systematic ID."""
        gene_id = arguments.get("gene_id", "")
        if not gene_id:
            return {
                "status": "error",
                "error": "gene_id parameter is required (e.g., 'SPBC11B10.09' for cdc2)",
            }

        url = f"{POMBASE_BASE_URL}/gene/{gene_id}"
        response = requests.get(
            url,
            headers={"Accept": "application/json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        raw = response.json()

        # Extract key fields
        interpro = []
        for match in raw.get("interpro_matches", [])[:15]:
            interpro.append(
                {
                    "id": match.get("id"),
                    "db": match.get("dbname"),
                    "name": match.get("name"),
                    "description": match.get("description")
                    or match.get("interpro_description"),
                    "interpro_id": match.get("interpro_id"),
                    "start": match.get("match_start"),
                    "end": match.get("match_end"),
                }
            )

        # Extract TM domains if present
        tm_domains = raw.get("tm_domain_coords", [])

        result = {
            "systematic_id": raw.get("uniquename"),
            "gene_name": raw.get("name"),
            "product": raw.get("product"),
            "taxon_id": raw.get("taxonid"),
            "uniprot_id": raw.get("uniprot_identifier"),
            "deletion_viability": raw.get("deletion_viability"),
            "biogrid_id": raw.get("biogrid_interactor_id"),
            "interpro_domains": interpro,
            "tm_domains": tm_domains[:10] if tm_domains else [],
            "characterisation_status": raw.get("characterisation_status"),
        }

        return {
            "status": "success",
            "data": result,
            "metadata": {
                "source": "PomBase",
                "query": gene_id,
                "endpoint": "gene_detail",
            },
        }

    def _gene_summary_search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search PomBase gene summaries by gene name or keyword."""
        query = arguments.get("query", "").lower()
        if not query:
            return {
                "status": "error",
                "error": "query parameter is required (e.g., 'cdc2', 'kinase', 'pom1')",
            }

        limit = min(arguments.get("limit", 10), 50)

        # Fetch gene summaries (cached in practice)
        url = f"{POMBASE_BASE_URL}/gene_summaries"
        response = requests.get(
            url,
            headers={"Accept": "application/json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        all_genes = response.json()

        # Search by gene name, systematic ID, or product description
        # gene_summaries returns a list of dicts (not a dict)
        results = []
        for gene_entry in all_genes:
            sys_id = gene_entry.get("uniquename", "")
            gene_name = (gene_entry.get("name") or "").lower()
            product = (gene_entry.get("product") or "").lower()
            sys_lower = sys_id.lower()

            if query in gene_name or query in sys_lower or query in product:
                results.append(
                    {
                        "systematic_id": sys_id,
                        "gene_name": gene_entry.get("name"),
                        "product": gene_entry.get("product"),
                        "uniprot_id": gene_entry.get("uniprot_identifier"),
                    }
                )
                if len(results) >= limit:
                    break

        total_genes = len(all_genes) if isinstance(all_genes, list) else 0

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "source": "PomBase",
                "total_genes": total_genes,
                "returned": len(results),
                "query": query,
                "endpoint": "gene_summary_search",
            },
        }

    def _gene_phenotypes(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get phenotype information for a PomBase gene."""
        gene_id = arguments.get("gene_id", "")
        if not gene_id:
            return {
                "status": "error",
                "error": "gene_id parameter is required (e.g., 'SPBC11B10.09' for cdc2)",
            }

        # Get full gene data
        url = f"{POMBASE_BASE_URL}/gene/{gene_id}"
        response = requests.get(
            url,
            headers={"Accept": "application/json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        raw = response.json()

        # Extract phenotype annotations from cv_annotations
        phenotypes = []
        cv_annotations = raw.get("cv_annotations", {})
        terms_lookup = raw.get("terms_by_termid", {})

        # Phenotype annotations are under single_locus_phenotype / multi_locus_phenotype
        for cv_name, annotations in cv_annotations.items():
            if "phenotype" in cv_name.lower():
                for ann in annotations[:30]:
                    term_id = ann.get("term", "")
                    # Look up term name from the terms_by_termid dict
                    term_info = terms_lookup.get(term_id, {})
                    term_name = (
                        term_info.get("name") if isinstance(term_info, dict) else None
                    )
                    phenotypes.append(
                        {
                            "term_id": term_id,
                            "term_name": term_name,
                            "cv_name": cv_name,
                            "is_not": ann.get("is_not", False),
                        }
                    )

        # Also check physical_interactions and genetic_interactions counts
        gene_name = raw.get("name", gene_id)
        deletion_viability = raw.get("deletion_viability")

        result = {
            "systematic_id": raw.get("uniquename"),
            "gene_name": gene_name,
            "deletion_viability": deletion_viability,
            "phenotype_count": len(phenotypes),
            "phenotypes": phenotypes[:50],
        }

        return {
            "status": "success",
            "data": result,
            "metadata": {
                "source": "PomBase",
                "query": gene_id,
                "endpoint": "gene_phenotypes",
            },
        }

    def _fetch_gene(self, gene_id: str) -> Dict[str, Any]:
        """Fetch the full PomBase gene record for the given systematic ID."""
        url = f"{POMBASE_BASE_URL}/gene/{gene_id}"
        response = requests.get(
            url,
            headers={"Accept": "application/json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def _gene_orthologs(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get human and S. cerevisiae orthologs of a fission-yeast gene."""
        gene_id = arguments.get("gene_id", "")
        if not gene_id:
            return {
                "status": "error",
                "error": "gene_id parameter is required (e.g., 'SPBC11B10.09' for cdc2)",
            }

        raw = self._fetch_gene(gene_id)

        taxon_names = {9606: "Homo sapiens", 4932: "Saccharomyces cerevisiae"}
        orthologs = []
        for o in raw.get("ortholog_annotations", []):
            taxon_id = o.get("ortholog_taxonid")
            orthologs.append(
                {
                    "ortholog_id": o.get("ortholog_uniquename"),
                    "ortholog_taxon_id": taxon_id,
                    "ortholog_species": taxon_names.get(taxon_id, str(taxon_id)),
                }
            )

        result = {
            "systematic_id": raw.get("uniquename"),
            "gene_name": raw.get("name"),
            "ortholog_count": len(orthologs),
            "orthologs": orthologs,
        }

        return {
            "status": "success",
            "data": result,
            "metadata": {
                "source": "PomBase",
                "query": gene_id,
                "endpoint": "gene_orthologs",
            },
        }

    def _gene_interactions(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get physical and genetic interactions for a fission-yeast gene."""
        gene_id = arguments.get("gene_id", "")
        if not gene_id:
            return {
                "status": "error",
                "error": "gene_id parameter is required (e.g., 'SPBC11B10.09' for cdc2)",
            }

        raw = self._fetch_gene(gene_id)
        genes_lookup = raw.get("genes_by_uniquename", {})

        def _gene_name(uniquename):
            info = genes_lookup.get(uniquename) or {}
            return info.get("name") if isinstance(info, dict) else None

        physical = []
        for i in raw.get("physical_interactions", [])[:75]:
            if not isinstance(i, dict):
                continue
            partner = (
                i.get("gene_uniquename")
                if i.get("gene_uniquename") != gene_id
                else i.get("interactor_uniquename")
            )
            physical.append(
                {
                    "interactor_id": partner,
                    "interactor_name": _gene_name(partner),
                    "evidence": i.get("evidence"),
                    "reference": i.get("reference_uniquename"),
                    "throughput": i.get("throughput"),
                    "source_database": i.get("source_database"),
                }
            )

        # genetic_interactions entries are [pair_dict, [evidence_dicts]] pairs.
        genetic = []
        for entry in raw.get("genetic_interactions", [])[:75]:
            pair = None
            evidence = None
            if isinstance(entry, (list, tuple)) and entry:
                pair = entry[0] if isinstance(entry[0], dict) else None
                if len(entry) > 1 and isinstance(entry[1], list) and entry[1]:
                    evidence = entry[1][0] if isinstance(entry[1][0], dict) else None
            elif isinstance(entry, dict):
                pair = entry
            if not isinstance(pair, dict):
                continue
            gene_a = pair.get("gene_a_uniquename")
            gene_b = pair.get("gene_b_uniquename")
            partner = gene_b if gene_a == gene_id else gene_a
            ev = evidence or {}
            genetic.append(
                {
                    "interactor_id": partner,
                    "interactor_name": _gene_name(partner),
                    "interaction_type": pair.get("interaction_type"),
                    "reference": ev.get("reference_uniquename"),
                    "throughput": ev.get("throughput"),
                    "source_database": ev.get("source_database"),
                }
            )

        result = {
            "systematic_id": raw.get("uniquename"),
            "gene_name": raw.get("name"),
            "physical_interaction_count": len(raw.get("physical_interactions", [])),
            "physical_interactions": physical,
            "genetic_interaction_count": len(raw.get("genetic_interactions", [])),
            "genetic_interactions": genetic,
        }

        return {
            "status": "success",
            "data": result,
            "metadata": {
                "source": "PomBase",
                "query": gene_id,
                "endpoint": "gene_interactions",
            },
        }

    def _gene_go_annotations(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get GO annotations (BP/MF/CC) for a fission-yeast gene."""
        gene_id = arguments.get("gene_id", "")
        if not gene_id:
            return {
                "status": "error",
                "error": "gene_id parameter is required (e.g., 'SPBC11B10.09' for cdc2)",
            }

        raw = self._fetch_gene(gene_id)
        cv_annotations = raw.get("cv_annotations", {})
        terms_lookup = raw.get("terms_by_termid", {})

        aspects = {
            "biological_process": "BP",
            "molecular_function": "MF",
            "cellular_component": "CC",
        }

        go_terms = []
        aspect_counts = {}
        for cv_name, code in aspects.items():
            annotations = cv_annotations.get(cv_name, [])
            aspect_counts[cv_name] = len(annotations)
            for ann in annotations[:30]:
                if not isinstance(ann, dict):
                    continue
                term_id = ann.get("term", "")
                term_info = terms_lookup.get(term_id, {})
                term_name = (
                    term_info.get("name") if isinstance(term_info, dict) else None
                )
                go_terms.append(
                    {
                        "term_id": term_id,
                        "term_name": term_name,
                        "aspect": cv_name,
                        "aspect_code": code,
                        "is_not": ann.get("is_not", False),
                    }
                )

        result = {
            "systematic_id": raw.get("uniquename"),
            "gene_name": raw.get("name"),
            "aspect_counts": aspect_counts,
            "go_term_count": len(go_terms),
            "go_terms": go_terms,
        }

        return {
            "status": "success",
            "data": result,
            "metadata": {
                "source": "PomBase",
                "query": gene_id,
                "endpoint": "gene_go_annotations",
            },
        }
