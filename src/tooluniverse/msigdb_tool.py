"""MSigDB (Molecular Signatures Database) tool — access 33,000+ gene sets.

Covers GTRD TF targets, miRDB miRNA targets, oncogenic signatures,
hallmark gene sets, GO terms, KEGG pathways, and more.

API: https://www.gsea-msigdb.org/gsea/msigdb/ (no authentication required)
"""

import json
import urllib.parse
import urllib.request
from typing import Any, Dict, List

from .base_tool import BaseTool
from .tool_registry import register_tool


MSIGDB_BASE = "https://www.gsea-msigdb.org/gsea/msigdb"


@register_tool("MSigDBTool")
class MSigDBTool(BaseTool):
    """Query MSigDB gene sets — TF targets, miRNA targets, oncogenic signatures, and more."""

    def __init__(self, tool_config: Dict[str, Any], **kwargs):
        super().__init__(tool_config)
        self.operation = tool_config.get("fields", {}).get("operation", "get_gene_set")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        operation = arguments.get("operation", self.operation)

        if operation == "get_gene_set":
            return self._get_gene_set(arguments)
        elif operation == "check_gene_in_set":
            return self._check_gene_in_set(arguments)
        elif operation == "search_gene_sets":
            return self._search_gene_sets(arguments)
        else:
            return {"status": "error", "error": f"Unknown operation: {operation}"}

    def _fetch_geneset(self, gene_set_name: str, species: str) -> Dict[str, Any] | None:
        """Fetch one gene set from a species-specific MSigDB endpoint.

        Returns the parsed ``{name: info}`` payload, or None when that endpoint
        does not serve the set. MSigDB answers an unknown name with an HTML
        error page rather than a 404, so a JSON decode failure means "not here"
        — not a transport error.
        """
        url = (
            f"{MSIGDB_BASE}/{species}/download_geneset.jsp"
            f"?geneSetName={urllib.parse.quote(gene_set_name)}&fileType=json"
        )
        req = urllib.request.Request(url, headers={"User-Agent": "ToolUniverse/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8", "replace")
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            return None
        return data or None

    def _get_gene_set(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch a gene set by exact name.

        MSigDB serves human (H/C1-C8) and mouse (MH/M1-M8, e.g. the ``MP_*``
        mammalian-phenotype sets) from separate endpoints. ``species`` selects
        one explicitly; the default "auto" tries human then mouse, so mouse-only
        sets resolve instead of failing with a JSON decode error.
        """
        gene_set_name = arguments.get("gene_set_name", "").strip()
        if not gene_set_name:
            return {"status": "error", "error": "gene_set_name is required"}

        species = (arguments.get("species") or "auto").strip().lower()
        if species in ("human", "mouse"):
            order = [species]
        else:
            order = ["human", "mouse"]

        try:
            data = None
            matched = None
            for sp in order:
                data = self._fetch_geneset(gene_set_name, sp)
                if data:
                    matched = sp
                    break

            if not data:
                tried = "/".join(order)
                return {
                    "status": "error",
                    "error": (
                        f"Gene set '{gene_set_name}' not found in MSigDB "
                        f"({tried} collections)"
                    ),
                }

            # Data is {gene_set_name: {info}}
            info = list(data.values())[0] if data else {}
            genes = info.get("geneSymbols", [])

            return {
                "status": "success",
                "data": {
                    "gene_set_name": gene_set_name,
                    "species": matched,
                    "systematic_name": info.get("systematicName", ""),
                    "collection": info.get("collection", ""),
                    "pmid": info.get("pmid", ""),
                    "num_genes": len(genes),
                    "genes": genes,
                    "description": info.get(
                        "briefDescription", info.get("exactSource", "")
                    ),
                    "external_url": info.get("externalDetailsURL", []),
                },
            }
        except urllib.error.HTTPError as e:
            return {"status": "error", "error": f"HTTP {e.code}: {gene_set_name}"}
        except Exception as e:
            return {"status": "error", "error": str(e)[:200]}

    def _check_gene_in_set(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Check if a gene is in a specific gene set."""
        gene_set_name = arguments.get("gene_set_name", "").strip()
        gene = arguments.get("gene", "").strip().upper()

        if not gene_set_name or not gene:
            return {
                "status": "error",
                "error": "Both 'gene_set_name' and 'gene' are required",
            }

        result = self._get_gene_set(
            {"gene_set_name": gene_set_name, "species": arguments.get("species")}
        )
        if result.get("status") != "success":
            return result

        genes = result["data"]["genes"]
        genes_upper = [g.upper() for g in genes]
        found = gene in genes_upper

        return {
            "status": "success",
            "data": {
                "gene_set_name": gene_set_name,
                "species": result["data"].get("species"),
                "gene": gene,
                "is_member": found,
                "total_genes_in_set": len(genes),
            },
        }

    def _search_gene_sets(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search for gene sets by name pattern."""
        query = arguments.get("query", "").strip()
        if not query:
            return {"status": "error", "error": "query is required"}

        # Try exact match first
        result = self._get_gene_set({"gene_set_name": query})
        if result.get("status") == "success":
            return {
                "status": "success",
                "data": {
                    "query": query,
                    "matches": [
                        {
                            "name": query,
                            "collection": result["data"]["collection"],
                            "num_genes": result["data"]["num_genes"],
                        }
                    ],
                },
            }

        # Try common name patterns
        candidates = self._generate_candidates(query)
        matches = []
        for candidate in candidates[:5]:
            r = self._get_gene_set({"gene_set_name": candidate})
            if r.get("status") == "success":
                matches.append(
                    {
                        "name": candidate,
                        "collection": r["data"]["collection"],
                        "num_genes": r["data"]["num_genes"],
                    }
                )

        if matches:
            return {"status": "success", "data": {"query": query, "matches": matches}}

        return {
            "status": "error",
            "error": f"No gene sets found matching '{query}'",
        }

    def _generate_candidates(self, query: str) -> List[str]:
        """Generate candidate gene set names from a query."""
        q = query.strip()
        candidates = [q]
        # GTRD TF targets: "ZNF549" → "ZNF549_TARGET_GENES"
        candidates.append(f"{q}_TARGET_GENES")
        # miRDB targets: "MIR675_3P" → "MIR675_3P_TARGET_GENES"
        candidates.append(f"{q}_TARGET_GENES")
        # With prefix: "hsa-miR-675-3p" → "MIR675_3P"
        if q.startswith("hsa-"):
            normalized = (
                q.replace("hsa-", "").replace("-", "_").replace("miR", "MIR").upper()
            )
            candidates.append(normalized)
            candidates.append(f"{normalized}_TARGET_GENES")
        return candidates
