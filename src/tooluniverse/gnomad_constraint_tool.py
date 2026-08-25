"""
gnomAD Gene Constraint Tool

Fetches gene-level constraint metrics from the gnomAD (Genome Aggregation
Database) GraphQL API and returns a flat, curated summary including pLI,
LOEUF (= oe_lof_upper), missense Z, synonymous Z, and observed/expected
loss-of-function counts.

No API key is required. Endpoint: https://gnomad.broadinstitute.org/api
"""

import requests
from typing import Dict, Any, Optional
from .base_tool import BaseTool
from .gnomad_tool import describe_dataset, resolve_dataset_assembly
from .tool_registry import register_tool


# gnomAD's `gnomad_constraint` field does NOT accept a dataset argument; the
# constraint table is selected by `reference_genome`. We expose a `dataset`
# parameter (matching gnomAD's variant-dataset naming) for a familiar interface
# and translate it to the appropriate reference genome:
#   gnomad_r4 / gnomad_r3  -> GRCh38 (gnomAD v4 constraint)
#   gnomad_r2_1 / exac     -> GRCh37 (gnomAD v2.1.1 / ExAC-era constraint)
# The dataset-to-assembly table lives in gnomad_tool so the whole gnomAD family
# resolves assemblies the same way; it matches by prefix, so subsets such as
# gnomad_r3_non_cancer resolve by rule instead of falling through to a default.

_QUERY = """
query GeneConstraint($geneSymbol: String, $geneId: String, $referenceGenome: ReferenceGenomeId!) {
  gene(gene_symbol: $geneSymbol, gene_id: $geneId, reference_genome: $referenceGenome) {
    symbol
    gene_id
    gnomad_constraint {
      pli
      oe_lof
      oe_lof_lower
      oe_lof_upper
      mis_z
      syn_z
      exp_lof
      obs_lof
    }
  }
}
"""


@register_tool("GnomADConstraintTool")
class GnomADConstraintTool(BaseTool):
    """
    Get gene-level constraint metrics (pLI, LOEUF, missense/synonymous Z,
    observed/expected LoF) from gnomAD for a gene symbol or Ensembl gene ID.
    """

    ENDPOINT_URL = "https://gnomad.broadinstitute.org/api"

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.timeout = 30

    @staticmethod
    def _resolve_reference(dataset: Optional[str]) -> str:
        """Map a gnomAD dataset id to the constraint reference genome."""
        return resolve_dataset_assembly(dataset)

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch curated gene constraint metrics from gnomAD."""
        arguments = arguments or {}
        gene_symbol = arguments.get("gene_symbol")
        gene_id = arguments.get("gene_id")

        if not gene_symbol and not gene_id:
            return {
                "status": "error",
                "error": "Provide either 'gene_symbol' (e.g. BRCA1) or 'gene_id' (Ensembl, e.g. ENSG00000012048).",
            }

        dataset = arguments.get("dataset") or "gnomad_r4"
        reference_genome = self._resolve_reference(dataset)

        variables = {
            "geneSymbol": gene_symbol,
            "geneId": gene_id,
            "referenceGenome": reference_genome,
        }

        try:
            response = requests.post(
                self.ENDPOINT_URL,
                json={"query": _QUERY, "variables": variables},
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "User-Agent": "ToolUniverse/1.0",
                },
                timeout=self.timeout,
            )
        except requests.exceptions.RequestException as exc:
            return {
                "status": "error",
                "error": f"gnomAD GraphQL request failed: {exc}",
            }

        try:
            payload = response.json()
        except ValueError:
            return {
                "status": "error",
                "error": (
                    f"gnomAD API returned a non-JSON response "
                    f"(HTTP {response.status_code})."
                ),
            }

        # GraphQL surfaces errors with HTTP 200; check the errors array first.
        errors = payload.get("errors")
        if errors:
            first = errors[0] if isinstance(errors, list) and errors else None
            message = (
                first.get("message")
                if isinstance(first, dict)
                else "gnomAD GraphQL query returned errors"
            )
            return {"status": "error", "error": message or "gnomAD GraphQL error"}

        gene = (payload.get("data") or {}).get("gene")
        if not gene:
            target = gene_symbol or gene_id
            return {
                "status": "error",
                "error": (
                    f"No gene found for '{target}' in gnomAD "
                    f"(reference {reference_genome}). "
                    f"Check the symbol/Ensembl ID (gnomAD uses current HGNC symbols, "
                    f"e.g. GBA1 not GBA)."
                ),
            }

        constraint = gene.get("gnomad_constraint")
        if not constraint:
            return {
                "status": "error",
                "error": (
                    f"Gene '{gene.get('symbol') or gene_id}' found, but no gnomAD "
                    f"constraint metrics are available (reference {reference_genome})."
                ),
            }

        oe_lof_upper = constraint.get("oe_lof_upper")
        data = {
            "gene_symbol": gene.get("symbol"),
            "gene_id": gene.get("gene_id"),
            # Same provenance block as the rest of the gnomAD family, so a key
            # added there can never skip this tool. Constraint has no
            # exome/genome split, so no `dataset_note` ever applies.
            **describe_dataset(dataset, assembly=reference_genome),
            "pLI": constraint.get("pli"),
            "oe_lof": constraint.get("oe_lof"),
            "oe_lof_lower": constraint.get("oe_lof_lower"),
            "oe_lof_upper": oe_lof_upper,
            # LOEUF is the upper bound of the observed/expected LoF confidence interval.
            "loeuf": oe_lof_upper,
            "mis_z": constraint.get("mis_z"),
            "syn_z": constraint.get("syn_z"),
            "exp_lof": constraint.get("exp_lof"),
            "obs_lof": constraint.get("obs_lof"),
        }

        return {"status": "success", "data": data}
