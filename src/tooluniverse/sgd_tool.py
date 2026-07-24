# sgd_tool.py
"""
SGD (Saccharomyces Genome Database) REST API tool for ToolUniverse.

SGD is the comprehensive resource for yeast (Saccharomyces cerevisiae)
genomics and molecular biology. It provides curated gene information,
phenotypes, GO annotations, genetic/physical interactions, and literature.

API: https://www.yeastgenome.org/backend
No authentication required. Free for academic/research use.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

SGD_BASE_URL = "https://www.yeastgenome.org/backend"


@register_tool("SGDTool")
class SGDTool(BaseTool):
    """
    Tool for querying the Saccharomyces Genome Database (SGD).

    SGD provides curated information about the budding yeast S. cerevisiae,
    including gene function, phenotypes, interactions, GO annotations,
    pathways, and literature.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        self.endpoint_type = tool_config.get("fields", {}).get("endpoint_type", "locus")
        self.query_mode = tool_config.get("fields", {}).get("query_mode", "overview")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the SGD API call."""
        try:
            return self._dispatch(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"SGD API request timed out after {self.timeout} seconds",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to SGD API. Check network connectivity.",
            }
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "error": f"SGD API HTTP error: {e.response.status_code}",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error querying SGD: {str(e)}",
            }

    def _dispatch(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint based on config."""
        if self.endpoint_type == "locus" and self.query_mode == "overview":
            return self._locus_overview(arguments)
        elif self.endpoint_type == "locus" and self.query_mode == "phenotype":
            return self._locus_phenotypes(arguments)
        elif self.endpoint_type == "locus" and self.query_mode == "go":
            return self._locus_go(arguments)
        elif self.endpoint_type == "locus" and self.query_mode == "interaction":
            return self._locus_interactions(arguments)
        elif self.endpoint_type == "locus" and self.query_mode == "regulation":
            return self._locus_regulation(arguments)
        elif self.endpoint_type == "locus" and self.query_mode == "sequence":
            return self._locus_sequence(arguments)
        elif self.endpoint_type == "locus" and self.query_mode == "disease":
            return self._locus_disease(arguments)
        elif self.endpoint_type == "search":
            return self._search(arguments)
        else:
            return {
                "status": "error",
                "error": f"Unknown endpoint_type/query_mode: {self.endpoint_type}/{self.query_mode}",
            }

    def _locus_overview(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get gene/locus overview from SGD by SGD ID."""
        sgd_id = arguments.get("sgd_id", "")
        if not sgd_id:
            return {
                "status": "error",
                "error": "sgd_id parameter is required (e.g., S000003219 or S000000259)",
            }

        url = f"{SGD_BASE_URL}/locus/{sgd_id}"
        response = requests.get(
            url, headers={"Accept": "application/json"}, timeout=self.timeout
        )
        response.raise_for_status()
        raw = response.json()

        result = {
            "sgd_id": raw.get("sgdid"),
            "display_name": raw.get("display_name"),
            "gene_name": raw.get("gene_name"),
            "systematic_name": raw.get("format_name"),
            "locus_type": raw.get("locus_type"),
            "qualifier": raw.get("qualifier"),
            "description": raw.get("description"),
            "name_description": raw.get("name_description"),
            "uniprot_id": raw.get("uniprot_id"),
            "aliases": [a.get("display_name") for a in raw.get("aliases", [])[:10]],
            "qualities": raw.get("qualities", []),
        }

        return {
            "status": "success",
            "data": result,
            "metadata": {
                "source": "SGD",
                "query": sgd_id,
                "endpoint": "locus/overview",
            },
        }

    def _locus_phenotypes(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get phenotype annotations for a yeast gene."""
        sgd_id = arguments.get("sgd_id", "")
        if not sgd_id:
            return {"status": "error", "error": "sgd_id parameter is required"}

        url = f"{SGD_BASE_URL}/locus/{sgd_id}/phenotype_details"
        response = requests.get(
            url, headers={"Accept": "application/json"}, timeout=self.timeout
        )
        response.raise_for_status()
        raw = response.json()

        results = []
        for p in raw[:50]:  # Limit to 50 results
            phenotype = p.get("phenotype", {})
            results.append(
                {
                    "phenotype": phenotype.get("display_name"),
                    "qualifier": phenotype.get("qualifier"),
                    "mutant_type": p.get("mutant_type"),
                    "experiment_type": p.get("experiment", {}).get("display_name")
                    if p.get("experiment")
                    else None,
                    "strain_name": p.get("strain", {}).get("display_name")
                    if p.get("strain")
                    else None,
                    "allele": p.get("allele", {}).get("display_name")
                    if p.get("allele")
                    else None,
                    "chemical": p.get("chemical", {}).get("display_name")
                    if p.get("chemical")
                    else None,
                    "reference": p.get("reference", {}).get("display_name")
                    if p.get("reference")
                    else None,
                }
            )

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "source": "SGD",
                "total_results": len(raw),
                "returned": len(results),
                "query": sgd_id,
                "endpoint": "locus/phenotype_details",
            },
        }

    def _locus_go(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get Gene Ontology annotations for a yeast gene."""
        sgd_id = arguments.get("sgd_id", "")
        if not sgd_id:
            return {"status": "error", "error": "sgd_id parameter is required"}

        url = f"{SGD_BASE_URL}/locus/{sgd_id}/go_details"
        response = requests.get(
            url, headers={"Accept": "application/json"}, timeout=self.timeout
        )
        response.raise_for_status()
        raw = response.json()

        results = []
        for g in raw[:50]:
            go = g.get("go", {})
            results.append(
                {
                    "go_id": go.get("go_id"),
                    "go_term": go.get("display_name"),
                    "go_aspect": g.get("go_aspect"),
                    "qualifier": g.get("qualifier"),
                    "evidence_code": g.get("evidence_code"),
                    "annotation_type": g.get("annotation_type"),
                    "source": g.get("source", {}).get("display_name")
                    if g.get("source")
                    else None,
                    "reference": g.get("reference", {}).get("display_name")
                    if g.get("reference")
                    else None,
                }
            )

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "source": "SGD",
                "total_results": len(raw),
                "returned": len(results),
                "query": sgd_id,
                "endpoint": "locus/go_details",
            },
        }

    def _locus_interactions(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get genetic and physical interactions for a yeast gene."""
        sgd_id = arguments.get("sgd_id", "")
        if not sgd_id:
            return {"status": "error", "error": "sgd_id parameter is required"}

        url = f"{SGD_BASE_URL}/locus/{sgd_id}/interaction_details"
        response = requests.get(
            url, headers={"Accept": "application/json"}, timeout=self.timeout
        )
        response.raise_for_status()
        raw = response.json()

        results = []
        for i in raw[:50]:
            locus1 = i.get("locus1", {})
            locus2 = i.get("locus2", {})
            results.append(
                {
                    "interaction_type": i.get("interaction_type"),
                    "experiment_type": i.get("experiment_type"),
                    "bait_gene": locus1.get("display_name"),
                    "hit_gene": locus2.get("display_name"),
                    "bait_sgdid": locus1.get("link", "").split("/")[-1]
                    if locus1.get("link")
                    else None,
                    "hit_sgdid": locus2.get("link", "").split("/")[-1]
                    if locus2.get("link")
                    else None,
                    "annotation_type": i.get("annotation_type"),
                    "source": i.get("source", {}).get("display_name")
                    if i.get("source")
                    else None,
                    "reference": i.get("reference", {}).get("display_name")
                    if i.get("reference")
                    else None,
                }
            )

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "source": "SGD",
                "total_results": len(raw),
                "returned": len(results),
                "query": sgd_id,
                "endpoint": "locus/interaction_details",
            },
        }

    @staticmethod
    def _sgdid_from_link(link: str) -> str:
        """Extract the SGD identifier (S0000...) from a '/locus/S000...' link."""
        return link.split("/")[-1] if link else None

    def _locus_regulation(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get transcriptional regulation network (regulator<->target pairs)."""
        sgd_id = arguments.get("sgd_id", "")
        if not sgd_id:
            return {
                "status": "error",
                "error": "sgd_id parameter is required (e.g., S000000364 for CDC28)",
            }

        url = f"{SGD_BASE_URL}/locus/{sgd_id}/regulation_details"
        response = requests.get(
            url, headers={"Accept": "application/json"}, timeout=self.timeout
        )
        response.raise_for_status()
        raw = response.json() or []

        results = []
        for r in raw[:100]:
            locus1 = r.get("locus1") or {}
            locus2 = r.get("locus2") or {}
            evidence = r.get("evidence") or {}
            reference = r.get("reference") or {}
            results.append(
                {
                    "regulator": locus1.get("display_name"),
                    "regulator_sgdid": self._sgdid_from_link(locus1.get("link")),
                    "target": locus2.get("display_name"),
                    "target_sgdid": self._sgdid_from_link(locus2.get("link")),
                    "regulation_of": r.get("regulation_of"),
                    "direction": r.get("direction"),
                    "happens_during": r.get("happens_during"),
                    "evidence": evidence.get("display_name"),
                    "annotation_type": r.get("annotation_type"),
                    "reference": reference.get("display_name"),
                    "pubmed_id": reference.get("pubmed_id"),
                }
            )

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "source": "SGD",
                "total_results": len(raw),
                "returned": len(results),
                "query": sgd_id,
                "endpoint": "locus/regulation_details",
            },
        }

    def _locus_sequence(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get genomic/coding/protein sequence and coordinates for a yeast gene."""
        sgd_id = arguments.get("sgd_id", "")
        if not sgd_id:
            return {
                "status": "error",
                "error": "sgd_id parameter is required (e.g., S000000364 for CDC28)",
            }

        url = f"{SGD_BASE_URL}/locus/{sgd_id}/sequence_details"
        response = requests.get(
            url, headers={"Accept": "application/json"}, timeout=self.timeout
        )
        response.raise_for_status()
        raw = response.json() or {}

        def _first_block(entries):
            """Take the reference (S288C) sequence block, falling back to first."""
            if not isinstance(entries, list) or not entries:
                return {}
            for e in entries:
                strain = e.get("strain") or {}
                if "S288C" in (strain.get("display_name") or ""):
                    return e
            return entries[0]

        genomic = _first_block(raw.get("genomic_dna"))
        coding = _first_block(raw.get("coding_dna"))
        protein = _first_block(raw.get("protein"))

        result = {
            "sgd_id": sgd_id,
            "genomic_dna": {
                "start": genomic.get("start"),
                "end": genomic.get("end"),
                "strand": genomic.get("strand"),
                "length": len(genomic.get("residues") or ""),
                "residues": genomic.get("residues"),
            },
            "coding_dna": {
                "length": len(coding.get("residues") or ""),
                "residues": coding.get("residues"),
            },
            "protein": {
                "length": len(protein.get("residues") or ""),
                "residues": protein.get("residues"),
            },
        }

        return {
            "status": "success",
            "data": result,
            "metadata": {
                "source": "SGD",
                "query": sgd_id,
                "endpoint": "locus/sequence_details",
            },
        }

    def _locus_disease(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get curated gene-disease (DOID) associations for a yeast gene."""
        sgd_id = arguments.get("sgd_id", "")
        if not sgd_id:
            return {
                "status": "error",
                "error": "sgd_id parameter is required (e.g., S000000364 for CDC28)",
            }

        url = f"{SGD_BASE_URL}/locus/{sgd_id}/disease_details"
        response = requests.get(
            url, headers={"Accept": "application/json"}, timeout=self.timeout
        )
        response.raise_for_status()
        raw = response.json() or []

        results = []
        for r in raw[:50]:
            disease = r.get("disease") or {}
            locus = r.get("locus") or {}
            reference = r.get("reference") or {}
            source = r.get("source") or {}
            results.append(
                {
                    "disease_name": disease.get("display_name"),
                    "disease_id": disease.get("disease_id"),
                    "annotation_type": r.get("annotation_type"),
                    "qualifier": r.get("qualifier"),
                    "locus": locus.get("display_name"),
                    "locus_sgdid": self._sgdid_from_link(locus.get("link")),
                    "source": source.get("display_name"),
                    "reference": reference.get("display_name"),
                    "pubmed_id": reference.get("pubmed_id"),
                }
            )

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "source": "SGD",
                "total_results": len(raw),
                "returned": len(results),
                "query": sgd_id,
                "endpoint": "locus/disease_details",
            },
        }

    def _search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search SGD for genes, GO terms, phenotypes, etc."""
        query = arguments.get("query", "")
        if not query:
            return {"status": "error", "error": "query parameter is required"}

        limit = min(arguments.get("limit", 10), 50)
        offset = arguments.get("offset", 0)
        category = arguments.get("category", "")

        params = {
            "query": query,
            "limit": limit,
            "offset": offset,
        }
        if category:
            params["category"] = category

        url = f"{SGD_BASE_URL}/get_search_results"
        response = requests.get(
            url,
            params=params,
            headers={"Accept": "application/json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        raw = response.json()

        if raw is None:
            return {
                "status": "success",
                "data": [],
                "metadata": {"total_results": 0, "query": query, "source": "SGD"},
            }

        results = []
        for r in raw.get("results", []):
            results.append(
                {
                    "name": r.get("name"),
                    "category": r.get("category"),
                    "description": (r.get("description") or "")[:200],
                    "href": r.get("href"),
                    "aliases": r.get("aliases"),
                }
            )

        # Extract aggregation info
        categories = {}
        for agg in raw.get("aggregations", []):
            if agg.get("key") == "category":
                for v in agg.get("values", []):
                    categories[v["key"]] = v["total"]

        total = raw.get("total", {})

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "total_results": total.get("value", len(results)),
                "categories": categories,
                "query": query,
                "offset": offset,
                "limit": limit,
                "source": "SGD",
                "endpoint": "search",
            },
        }
