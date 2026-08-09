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
            return {
                "status": "error",
                "error": f"Ensembl Compara API timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {"status": "error", "error": "Failed to connect to Ensembl REST API"}
        except requests.exceptions.HTTPError as e:
            # Include the response body instead of just the status code --
            # Ensembl's 400s carry a JSON {"error": "..."} explaining what
            # wasn't recognized (e.g. an unresolved gene symbol), and
            # silently dropping it left a bare "HTTP error: 400" with no
            # indication of what to fix. Matches the error-body-extraction
            # pattern already used by ensembl_map_tool.py and
            # ensembl_variation_ext_tool.py.
            status = e.response.status_code if e.response is not None else "unknown"
            body = ""
            if e.response is not None:
                try:
                    body = e.response.json().get("error", "")
                except Exception:
                    body = e.response.text[:200]
            gene = arguments.get("gene", "")
            hint = (
                f" -- gene symbol '{gene}' may not exist for the requested "
                "species; verify it via ensembl_lookup_gene or "
                "HGNC_search_genes."
                if gene
                else ""
            )
            return {
                "status": "error",
                "error": (
                    f"Ensembl API HTTP {status}{f': {body}' if body else ''}{hint}"
                ),
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error querying Ensembl Compara: {str(e)}",
            }

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate Ensembl Compara endpoint."""
        if self.endpoint == "orthologues":
            return self._get_orthologues(arguments)
        elif self.endpoint == "paralogues":
            return self._get_paralogues(arguments)
        elif self.endpoint == "gene_tree":
            return self._get_gene_tree(arguments)
        elif self.endpoint == "cafe_tree":
            return self._get_cafe_tree(arguments)
        else:
            return {"status": "error", "error": f"Unknown endpoint: {self.endpoint}"}

    def _get_orthologues(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get orthologues for a gene across species."""
        gene = arguments.get("gene", "")
        if not gene:
            return {
                "status": "error",
                "error": "gene parameter is required (symbol or Ensembl ID)",
            }

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
            "status": "success",
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
            return {
                "status": "error",
                "error": "gene parameter is required (symbol or Ensembl ID)",
            }

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
            "status": "success",
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
            return {
                "status": "error",
                "error": "gene parameter is required (Ensembl gene ID)",
            }

        species = arguments.get("species", "human")

        # Gene tree uses /genetree/member/id or /genetree/member/symbol --
        # confirmed live that the id form 404s without a {species} path
        # segment (e.g. /genetree/member/id/ENSG00000141510 alone 404s;
        # /genetree/member/id/human/ENSG00000141510 works).
        if gene.startswith("ENS"):
            url = f"{ENSEMBL_BASE_URL}/genetree/member/id/{species}/{gene}"
        else:
            url = f"{ENSEMBL_BASE_URL}/genetree/member/symbol/{species}/{gene}"

        params = {"nh_format": "simple"}
        headers = {**ENSEMBL_HEADERS, "Content-Type": "application/json"}

        response = requests.get(
            url, params=params, headers=headers, timeout=self.timeout
        )
        response.raise_for_status()
        data = response.json()

        # Extract tree info. The tree's own id is a top-level field, not
        # nested under "tree" (confirmed live: {"type", "rooted", "tree",
        # "id"} -- "tree" itself carries no "id" key).
        tree_id = data.get("id")
        rooted = data.get("rooted", True)
        tree_data = data.get("tree", data)

        # Ensembl's JSON genetree response never embeds a "newick" field
        # regardless of nh_format -- Newick text is only served as a
        # separate plain-text response via the "text/x-nh" content type.
        # Fetch it as a best-effort second call; a failure here shouldn't
        # fail the whole tool.
        newick = None
        try:
            nh_resp = requests.get(
                url,
                params=params,
                headers={**ENSEMBL_HEADERS, "Content-Type": "text/x-nh"},
                timeout=self.timeout,
            )
            if nh_resp.status_code == 200 and nh_resp.text.strip():
                newick = nh_resp.text.strip()
        except requests.exceptions.RequestException:
            pass

        # Count members in the tree
        members = []
        self._collect_members(tree_data, members)

        return {
            "status": "success",
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
            # Leaf nodes carry a gene "id" and have no "children"; internal
            # (ancestral) nodes have "taxonomy" too but no "id". Confirmed
            # live: leaves have no "species" key at all -- species info
            # lives under "taxonomy", which the previous check never read.
            if "id" in node and not node.get("children"):
                gene_id = node.get("id", {})
                if isinstance(gene_id, dict):
                    gene_id = gene_id.get("accession", "")
                taxonomy = node.get("taxonomy", {})
                members.append(
                    {
                        "gene_id": str(gene_id),
                        "species": taxonomy.get("scientific_name", "")
                        if isinstance(taxonomy, dict)
                        else str(taxonomy),
                    }
                )
            # Traverse children
            for child in node.get("children", []):
                self._collect_members(child, members, max_members)

    def _get_cafe_tree(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get the CAFE gene-family gain/loss tree for a gene family."""
        gene_tree_id = arguments.get("gene_tree_id")
        gene = arguments.get("gene")
        species = arguments.get("species", "human")

        if gene_tree_id:
            url = f"{ENSEMBL_BASE_URL}/cafe/genetree/id/{gene_tree_id}"
        elif gene:
            if gene.startswith("ENS"):
                url = f"{ENSEMBL_BASE_URL}/cafe/genetree/member/id/{gene}"
            else:
                url = f"{ENSEMBL_BASE_URL}/cafe/genetree/member/symbol/{species}/{gene}"
        else:
            return {
                "status": "error",
                "error": (
                    "Provide gene_tree_id (e.g. 'ENSGT00390000003602') or gene "
                    "(symbol e.g. 'BRCA2' or Ensembl gene ID)"
                ),
            }

        headers = {**ENSEMBL_HEADERS, "Content-Type": "application/json"}
        response = requests.get(url, headers=headers, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        tree = data.get("tree", {}) if isinstance(data, dict) else {}

        # Recursively collect per-node gene-family size dynamics.
        nodes = []
        self._collect_cafe_nodes(tree, nodes)

        # The root node carries the family-wide birth-death (lambda) rate.
        root_lambda = tree.get("lambda") if isinstance(tree, dict) else None

        return {
            "status": "success",
            "data": {
                "type": data.get("type"),
                "rooted": data.get("rooted"),
                "pvalue_avg": data.get("pvalue_avg"),
                "lambda": root_lambda,
                "root_n_members": tree.get("n_members")
                if isinstance(tree, dict)
                else None,
                "nodes": nodes[:200],
                "total_nodes": len(nodes),
            },
            "metadata": {
                "source": "Ensembl Compara - CAFE",
                "query": gene_tree_id or gene,
            },
        }

    def _collect_cafe_nodes(self, node, nodes, max_nodes=400):
        """Recursively collect gene-family size dynamics at every CAFE node."""
        if not isinstance(node, dict) or len(nodes) >= max_nodes:
            return
        tax = node.get("tax") or {}
        nodes.append(
            {
                "name": node.get("name"),
                "scientific_name": tax.get("scientific_name"),
                "taxon_id": tax.get("id"),
                "n_members": node.get("n_members"),
                "pvalue": node.get("pvalue"),
                "p_value_lim": node.get("p_value_lim"),
                "lambda": node.get("lambda"),
            }
        )
        for child in node.get("children", []):
            self._collect_cafe_nodes(child, nodes, max_nodes)
