# wormbase_tool.py
"""
WormBase REST API tool for ToolUniverse.

WormBase is the central repository for research using the model organism
Caenorhabditis elegans and related nematodes. It provides curated gene
information, phenotypes, expression data, and orthologs.

API: https://rest.wormbase.org
No authentication required. Free for academic/research use.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

WORMBASE_BASE_URL = "https://rest.wormbase.org/rest"
ALLIANCE_SEARCH_URL = "https://www.alliancegenome.org/api/search"

# Module-level cache: gene name (lower) -> WBGene ID, avoids repeated lookups
_WBGENE_CACHE: dict = {}


def _resolve_wbgene_id(gene_input: str) -> str:
    """Resolve a gene name (e.g. 'unc-86') to a WBGene ID via the Alliance API.

    If the input already looks like a WBGene ID, return it unchanged.
    Returns the resolved WBGene ID or the original input if resolution fails.
    """
    if gene_input.upper().startswith("WBGENE"):
        return gene_input

    cache_key = gene_input.lower()
    if cache_key in _WBGENE_CACHE:
        return _WBGENE_CACHE[cache_key]

    try:
        params = {
            "category": "gene",
            "q": gene_input,
            "species": "Caenorhabditis elegans",
            "limit": 5,
        }
        resp = requests.get(ALLIANCE_SEARCH_URL, params=params, timeout=10)
        if resp.status_code != 200:
            return gene_input
        results = resp.json().get("results", [])
        for r in results:
            symbol = r.get("symbol", "")
            if symbol.lower() == cache_key:
                raw_id = r.get("id", "")
                # Alliance returns "WB:WBGene00006818" — strip the "WB:" prefix
                resolved = raw_id.split(":")[-1] if ":" in raw_id else raw_id
                _WBGENE_CACHE[cache_key] = resolved
                return resolved
        return gene_input
    except Exception:
        return gene_input


@register_tool("WormBaseTool")
class WormBaseTool(BaseTool):
    """
    Tool for querying WormBase, the C. elegans genome database.

    Provides detailed gene information for C. elegans and other
    nematodes including phenotypes, expression data, orthologs,
    and functional annotations.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        self.endpoint_type = tool_config.get("fields", {}).get(
            "endpoint_type", "gene_overview"
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the WormBase API call."""
        try:
            return self._dispatch(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"WormBase API request timed out after {self.timeout} seconds",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to WormBase API. Check network connectivity.",
            }
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "error": f"WormBase API HTTP error: {e.response.status_code}",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error querying WormBase: {str(e)}",
            }

    def _dispatch(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint based on config."""
        if self.endpoint_type == "gene_overview":
            return self._gene_overview(arguments)
        elif self.endpoint_type == "gene_phenotypes":
            return self._gene_phenotypes(arguments)
        elif self.endpoint_type == "gene_expression":
            return self._gene_expression(arguments)
        else:
            return {
                "status": "error",
                "error": f"Unknown endpoint_type: {self.endpoint_type}",
            }

    def _gene_overview(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed gene overview from WormBase by WBGene ID or gene name."""
        gene_input = arguments.get("gene_id", "")
        if not gene_input:
            return {
                "status": "error",
                "error": "gene_id parameter is required (e.g., 'WBGene00006763' or 'unc-86')",
            }
        gene_id = _resolve_wbgene_id(gene_input)

        url = f"{WORMBASE_BASE_URL}/widget/gene/{gene_id}/overview"
        response = requests.get(
            url,
            headers={"Accept": "application/json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        raw = response.json()

        fields = raw.get("fields", {})

        # Extract name info
        name_data = fields.get("name", {}).get("data", {})
        gene_name = name_data.get("label", "") if isinstance(name_data, dict) else ""
        wb_id = name_data.get("id", gene_id) if isinstance(name_data, dict) else gene_id

        # Extract taxonomy
        taxonomy_data = fields.get("taxonomy", {}).get("data", {})
        species = ""
        if isinstance(taxonomy_data, dict):
            genus = taxonomy_data.get("genus", "")
            sp = taxonomy_data.get("species", "")
            species = f"{genus} {sp}".strip()

        # Extract description
        desc_data = fields.get("concise_description", {}).get("data", {})
        description = ""
        if isinstance(desc_data, dict):
            description = desc_data.get("text", "")
        elif isinstance(desc_data, str):
            description = desc_data

        # Legacy description
        legacy_data = fields.get("legacy_manual_description", {}).get("data", {})
        legacy_desc = ""
        if isinstance(legacy_data, dict):
            legacy_desc = legacy_data.get("text", "")

        # Sequence name
        seq_name = fields.get("sequence_name", {}).get("data", "")

        # Classification
        classification = fields.get("classification", {}).get("data", {})
        gene_type = None
        if isinstance(classification, dict):
            gene_type = classification.get("type", None)
            if isinstance(gene_type, dict):
                gene_type = gene_type.get("label", None)

        # Status
        status = fields.get("status", {}).get("data", "")

        result = {
            "wormbase_id": wb_id,
            "gene_name": gene_name,
            "sequence_name": seq_name,
            "species": species,
            "description": description or legacy_desc,
            "gene_type": gene_type,
            "status": status,
        }

        return {
            "status": "success",
            "data": result,
            "metadata": {
                "source": "WormBase",
                "query": gene_id,
                "endpoint": "gene_overview",
            },
        }

    def _gene_phenotypes(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get phenotype annotations for a C. elegans gene from WormBase."""
        gene_input = arguments.get("gene_id", "")
        if not gene_input:
            return {
                "status": "error",
                "error": "gene_id parameter is required (e.g., 'WBGene00006763' or 'unc-86')",
            }
        gene_id = _resolve_wbgene_id(gene_input)

        url = f"{WORMBASE_BASE_URL}/widget/gene/{gene_id}/phenotype"
        response = requests.get(
            url,
            headers={"Accept": "application/json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        raw = response.json()

        fields = raw.get("fields", {})

        # Gene name
        name_data = fields.get("name", {}).get("data", {})
        gene_name = name_data.get("label", "") if isinstance(name_data, dict) else ""

        # Observed phenotypes
        phenotypes = []
        pheno_data = fields.get("phenotype", {}).get("data", [])
        if isinstance(pheno_data, list):
            for p in pheno_data[:50]:
                if isinstance(p, dict):
                    pheno_info = p.get("phenotype", {})
                    pheno_entry = {
                        "phenotype_id": pheno_info.get("id", "")
                        if isinstance(pheno_info, dict)
                        else "",
                        "phenotype_name": pheno_info.get("label", "")
                        if isinstance(pheno_info, dict)
                        else str(pheno_info),
                    }
                    # Evidence
                    evidence = p.get("evidence", [])
                    if isinstance(evidence, list) and evidence:
                        first_ev = evidence[0] if isinstance(evidence[0], dict) else {}
                        pheno_entry["evidence_type"] = first_ev.get("label", "")
                    phenotypes.append(pheno_entry)

        # Not-observed phenotypes
        not_observed = []
        not_pheno_data = fields.get("phenotype_not_observed", {}).get("data", [])
        if isinstance(not_pheno_data, list):
            for p in not_pheno_data[:20]:
                if isinstance(p, dict):
                    pheno_info = p.get("phenotype", {})
                    not_observed.append(
                        {
                            "phenotype_id": pheno_info.get("id", "")
                            if isinstance(pheno_info, dict)
                            else "",
                            "phenotype_name": pheno_info.get("label", "")
                            if isinstance(pheno_info, dict)
                            else str(pheno_info),
                        }
                    )

        result = {
            "wormbase_id": gene_id,
            "gene_name": gene_name,
            "phenotype_count": len(pheno_data) if isinstance(pheno_data, list) else 0,
            "phenotypes": phenotypes,
            "not_observed_count": len(not_pheno_data)
            if isinstance(not_pheno_data, list)
            else 0,
            "phenotypes_not_observed": not_observed,
        }

        return {
            "status": "success",
            "data": result,
            "metadata": {
                "source": "WormBase",
                "query": gene_id,
                "endpoint": "gene_phenotypes",
            },
        }

    def _gene_expression(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get expression data for a C. elegans gene from WormBase."""
        gene_input = arguments.get("gene_id", "")
        if not gene_input:
            return {
                "status": "error",
                "error": "gene_id parameter is required (e.g., 'WBGene00006763' or 'unc-86')",
            }
        gene_id = _resolve_wbgene_id(gene_input)

        url = f"{WORMBASE_BASE_URL}/widget/gene/{gene_id}/expression"
        response = requests.get(
            url,
            headers={"Accept": "application/json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        raw = response.json()

        fields = raw.get("fields", {})

        # Gene name
        name_data = fields.get("name", {}).get("data", {})
        gene_name = name_data.get("label", "") if isinstance(name_data, dict) else ""

        # Tissues expressed in
        expressed_in = []
        tissue_data = fields.get("expressed_in", {}).get("data", [])
        if isinstance(tissue_data, list):
            for t in tissue_data[:30]:
                if isinstance(t, dict):
                    ontology_term = t.get("ontology_term", {})
                    expressed_in.append(
                        {
                            "term_id": ontology_term.get("id", "")
                            if isinstance(ontology_term, dict)
                            else "",
                            "term_name": ontology_term.get("label", "")
                            if isinstance(ontology_term, dict)
                            else str(t),
                        }
                    )

        # Developmental stages
        expressed_during = []
        stage_data = fields.get("expressed_during", {}).get("data", [])
        if isinstance(stage_data, list):
            for s in stage_data[:20]:
                if isinstance(s, dict):
                    ontology_term = s.get("ontology_term", {})
                    expressed_during.append(
                        {
                            "term_id": ontology_term.get("id", "")
                            if isinstance(ontology_term, dict)
                            else "",
                            "term_name": ontology_term.get("label", "")
                            if isinstance(ontology_term, dict)
                            else str(s),
                        }
                    )

        # Subcellular localization
        subcellular = []
        sub_data = fields.get("subcellular_localization", {}).get("data", [])
        if isinstance(sub_data, list):
            for loc in sub_data[:10]:
                if isinstance(loc, dict):
                    ontology_term = loc.get("ontology_term", {})
                    subcellular.append(
                        {
                            "term_id": ontology_term.get("id", "")
                            if isinstance(ontology_term, dict)
                            else "",
                            "term_name": ontology_term.get("label", "")
                            if isinstance(ontology_term, dict)
                            else str(loc),
                        }
                    )

        # Expression clusters
        clusters = []
        cluster_data = fields.get("expression_cluster", {}).get("data", [])
        if isinstance(cluster_data, list):
            for c in cluster_data[:15]:
                if isinstance(c, dict):
                    cluster_info = c.get("expression_cluster", {})
                    clusters.append(
                        {
                            "cluster_id": cluster_info.get("id", "")
                            if isinstance(cluster_info, dict)
                            else "",
                            "cluster_label": cluster_info.get("label", "")
                            if isinstance(cluster_info, dict)
                            else str(c),
                        }
                    )

        result = {
            "wormbase_id": gene_id,
            "gene_name": gene_name,
            "expressed_in_count": len(tissue_data)
            if isinstance(tissue_data, list)
            else 0,
            "expressed_in": expressed_in,
            "expressed_during": expressed_during,
            "subcellular_localization": subcellular,
            "expression_clusters_count": len(cluster_data)
            if isinstance(cluster_data, list)
            else 0,
            "expression_clusters": clusters,
        }

        return {
            "status": "success",
            "data": result,
            "metadata": {
                "source": "WormBase",
                "query": gene_id,
                "endpoint": "gene_expression",
            },
        }
