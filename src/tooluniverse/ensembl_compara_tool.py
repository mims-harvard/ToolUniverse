# ensembl_compara_tool.py
"""
Ensembl Compara API tool for ToolUniverse.

Ensembl Compara provides access to comparative genomics data including
orthologues, paralogues, gene trees, and genome alignments across species.

API: https://rest.ensembl.org/
No authentication required (rate limited to 15 req/s).
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

ENSEMBL_BASE_URL = "https://rest.ensembl.org"
ENSEMBL_HEADERS = {"User-Agent": "ToolUniverse/1.0", "Accept": "application/json"}


@register_tool("EnsemblComparaTool")
class EnsemblComparaTool(BaseTool):
    """
    Tool for querying Ensembl Compara comparative genomics data.

    Ensembl Compara contains whole-genome alignments, gene trees, and
    homology data for vertebrates and other eukaryotes. Supports finding
    orthologues (between-species homologs) and paralogues (within-species
    gene duplications).

    Supports: orthologue search, paralogue search, gene tree retrieval.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "orthologues")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the Ensembl Compara API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {"error": f"Ensembl Compara API timed out after {self.timeout}s"}
        except requests.exceptions.ConnectionError:
            return {"error": "Failed to connect to Ensembl REST API"}
        except requests.exceptions.HTTPError as e:
            return {"error": f"Ensembl API HTTP error: {e.response.status_code}"}
        except Exception as e:
            return {"error": f"Unexpected error querying Ensembl Compara: {str(e)}"}

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate Ensembl Compara endpoint."""
        if self.endpoint == "orthologues":
            return self._get_orthologues(arguments)
        elif self.endpoint == "paralogues":
            return self._get_paralogues(arguments)
        elif self.endpoint == "gene_tree":
            return self._get_gene_tree(arguments)
        else:
            return {"error": f"Unknown endpoint: {self.endpoint}"}

    def _get_orthologues(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get orthologues for a gene across species."""
        gene = arguments.get("gene", "")
        if not gene:
            return {"error": "gene parameter is required (symbol or Ensembl ID)"}

        species = arguments.get("species", "human")
        target_species = arguments.get("target_species")
        target_taxon = arguments.get("target_taxon")

        # Determine if gene is Ensembl ID or symbol
        if gene.startswith("ENS"):
            url = f"{ENSEMBL_BASE_URL}/homology/id/{species}/{gene}"
        else:
            url = f"{ENSEMBL_BASE_URL}/homology/symbol/{species}/{gene}"

        params = {"type": "orthologues", "format": "condensed"}
        if target_species:
            params["target_species"] = target_species
        if target_taxon:
            params["target_taxon"] = target_taxon

        headers = {**ENSEMBL_HEADERS, "Content-Type": "application/json"}
        response = requests.get(
            url, params=params, headers=headers, timeout=self.timeout
        )
        response.raise_for_status()
        data = response.json()

        results = []
        for d in data.get("data", []):
            gene_id = d.get("id")
            for h in d.get("homologies", []):
                results.append(
                    {
                        "source_gene": gene_id,
                        "target_gene": h.get("id"),
                        "target_protein": h.get("protein_id"),
                        "target_species": h.get("species"),
                        "homology_type": h.get("type"),
                        "taxonomy_level": h.get("taxonomy_level"),
                        "method": h.get("method_link_type"),
                    }
                )

        return {
            "data": results,
            "metadata": {
                "source": "Ensembl Compara",
                "query_gene": gene,
                "query_species": species,
                "total_orthologues": len(results),
            },
        }

    def _get_paralogues(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get within-species paralogues (gene duplicates) for a gene."""
        gene = arguments.get("gene", "")
        if not gene:
            return {"error": "gene parameter is required (symbol or Ensembl ID)"}

        species = arguments.get("species", "human")

        if gene.startswith("ENS"):
            url = f"{ENSEMBL_BASE_URL}/homology/id/{species}/{gene}"
        else:
            url = f"{ENSEMBL_BASE_URL}/homology/symbol/{species}/{gene}"

        params = {"type": "paralogues", "format": "condensed"}
        headers = {**ENSEMBL_HEADERS, "Content-Type": "application/json"}

        response = requests.get(
            url, params=params, headers=headers, timeout=self.timeout
        )
        response.raise_for_status()
        data = response.json()

        results = []
        for d in data.get("data", []):
            gene_id = d.get("id")
            for h in d.get("homologies", []):
                results.append(
                    {
                        "source_gene": gene_id,
                        "paralogue_gene": h.get("id"),
                        "paralogue_protein": h.get("protein_id"),
                        "species": h.get("species"),
                        "paralogy_type": h.get("type"),
                        "taxonomy_level": h.get("taxonomy_level"),
                    }
                )

        return {
            "data": results,
            "metadata": {
                "source": "Ensembl Compara",
                "query_gene": gene,
                "query_species": species,
                "total_paralogues": len(results),
            },
        }

    def _get_gene_tree(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get gene tree (phylogenetic tree of homologous genes)."""
        gene = arguments.get("gene", "")
        if not gene:
            return {"error": "gene parameter is required (Ensembl gene ID)"}

        species = arguments.get("species", "human")

        # Gene tree uses /genetree/member/id or /genetree/member/symbol
        if gene.startswith("ENS"):
            url = f"{ENSEMBL_BASE_URL}/genetree/member/id/{gene}"
        else:
            url = f"{ENSEMBL_BASE_URL}/genetree/member/symbol/{species}/{gene}"

        params = {"nh_format": "simple"}
        headers = {**ENSEMBL_HEADERS, "Content-Type": "application/json"}

        response = requests.get(
            url, params=params, headers=headers, timeout=self.timeout
        )
        response.raise_for_status()
        data = response.json()

        # Extract tree info
        tree_id = (
            data.get("tree", {}).get("id")
            if isinstance(data.get("tree"), dict)
            else data.get("id")
        )
        rooted = data.get("rooted", True)

        # Get Newick tree from the response if available
        newick = None
        tree_data = data.get("tree", data)
        if isinstance(tree_data, dict):
            newick = tree_data.get("newick")

        # Count members in the tree
        members = []
        self._collect_members(tree_data, members)

        return {
            "data": {
                "tree_id": tree_id,
                "newick": newick,
                "rooted": rooted,
                "members": members[:50],
                "total_members": len(members),
            },
            "metadata": {
                "source": "Ensembl Compara",
                "query_gene": gene,
            },
        }

    def _collect_members(self, node, members, max_members=200):
        """Recursively collect leaf members from gene tree."""
        if len(members) >= max_members:
            return
        if isinstance(node, dict):
            # Leaf node has 'id' and 'species'
            if "id" in node and "species" in node:
                gene_id = node.get("id", {})
                if isinstance(gene_id, dict):
                    gene_id = gene_id.get("accession", "")
                members.append(
                    {
                        "gene_id": str(gene_id),
                        "species": node.get("species", {}).get("scientific_name", "")
                        if isinstance(node.get("species"), dict)
                        else str(node.get("species", "")),
                    }
                )
            # Traverse children
            for child in node.get("children", []):
                self._collect_members(child, members, max_members)
