"""
gnomAD GraphQL API Tool

This tool provides access to the gnomAD (Genome Aggregation Database) for
population genetics data, variant frequencies, and gene constraint metrics
using GraphQL.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool


class gnomADGraphQLTool(BaseTool):
    """Base class for gnomAD GraphQL API tools."""

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.endpoint_url = "https://gnomad.broadinstitute.org/api"
        # Prefer JSON-driven query definitions. Support both legacy top-level
        # `query_schema` and `fields.query_schema`.
        fields_cfg = tool_config.get("fields", {}) or {}
        self.query_schema = tool_config.get("query_schema") or fields_cfg.get(
            "query_schema", ""
        )
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "ToolUniverse/1.0",
            }
        )
        self.timeout = 30

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute GraphQL query with given arguments."""
        try:
            response = self.session.post(
                self.endpoint_url,
                json={"query": self.query_schema, "variables": arguments},
                timeout=self.timeout,
            )
            status_code = getattr(response, "status_code", None)
            response.raise_for_status()
            result = response.json()

            # GraphQL errors are returned with HTTP 200; surface them to users.
            errors = result.get("errors")
            if errors:
                first = errors[0] if isinstance(errors, list) and errors else None
                msg = first.get("message") if isinstance(first, dict) else None
                msg = msg or "gnomAD GraphQL query returned errors"
                return {
                    "status": "error",
                    "error": msg,
                    "url": getattr(response, "url", self.endpoint_url),
                    "status_code": status_code,
                    "detail": errors[:3],
                    "data": None,
                }

            data = result.get("data")
            if not data or all(not v for v in data.values()):
                return {
                    "status": "error",
                    "error": "No data returned from gnomAD API",
                    "url": getattr(response, "url", self.endpoint_url),
                    "status_code": status_code,
                    "data": None,
                }

            return {
                "status": "success",
                "data": data,
                "url": getattr(response, "url", self.endpoint_url),
            }

        except requests.exceptions.HTTPError as e:
            resp = getattr(e, "response", None)
            return {
                "status": "error",
                "error": (
                    f"gnomAD API returned HTTP {getattr(resp, 'status_code', None)}"
                ),
                "url": getattr(resp, "url", self.endpoint_url),
                "status_code": getattr(resp, "status_code", None),
                "detail": (getattr(resp, "text", "") or "")[:500] or None,
                "data": None,
            }
        except (requests.exceptions.RequestException, ValueError) as e:
            return {
                "status": "error",
                "error": f"gnomAD GraphQL request failed: {str(e)}",
                "url": self.endpoint_url,
                "status_code": None,
                "detail": None,
                "data": None,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"gnomAD GraphQL request failed: {str(e)}",
                "url": self.endpoint_url,
                "status_code": None,
                "detail": None,
                "data": None,
            }


@register_tool("gnomADGraphQLQueryTool")
class gnomADGraphQLQueryTool(gnomADGraphQLTool):
    """
    Generic gnomAD GraphQL tool driven by JSON config.

    Config fields supported:
    - fields.query_schema: GraphQL query string
    - fields.variable_map: map tool argument names -> GraphQL variable names
    - fields.default_variables: default GraphQL variable values
    """

    def __init__(self, tool_config):
        super().__init__(tool_config)
        fields_cfg = tool_config.get("fields", {}) or {}
        self.variable_map = fields_cfg.get("variable_map", {}) or {}
        self.default_variables = fields_cfg.get("default_variables", {}) or {}

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        # Merge defaults + map argument names to GraphQL variables
        variables: Dict[str, Any] = dict(self.default_variables)
        for k, v in (arguments or {}).items():
            if v is None:
                continue
            variables[self.variable_map.get(k, k)] = v
        return super().run(variables)


@register_tool("gnomADGetVariantPopulations")
class gnomADGetVariantPopulations(gnomADGraphQLTool):
    """
    Get per-ancestry (population-stratified) allele frequencies for a variant.

    The gnomAD API returns per-population `ac` and `an` only; this tool computes
    `af = ac / an` (guarding `an == 0` -> `af = None`) and separates the rows by
    genome vs exome callset.
    """

    def __init__(self, tool_config):
        super().__init__(tool_config)
        if not self.query_schema:
            self.query_schema = (
                "query($variantId: String!, $dataset: DatasetId!) { "
                "variant(variantId: $variantId, dataset: $dataset) { "
                "variant_id chrom pos ref alt rsid "
                "genome { ac an populations { id ac an } } "
                "exome { ac an populations { id ac an } } } }"
            )

    @staticmethod
    def _compute_af(ac, an):
        """Return ac/an, or None when an is missing/zero."""
        if not an:  # covers None and 0
            return None
        return ac / an

    def _build_callset(self, callset):
        """Build a callset summary (overall af + per-population rows)."""
        if not callset:
            return None
        populations = []
        for pop in callset.get("populations") or []:
            ac = pop.get("ac")
            an = pop.get("an")
            populations.append(
                {
                    "id": pop.get("id"),
                    "ac": ac,
                    "an": an,
                    "af": self._compute_af(ac, an),
                }
            )
        return {
            "ac": callset.get("ac"),
            "an": callset.get("an"),
            "af": self._compute_af(callset.get("ac"), callset.get("an")),
            "populations": populations,
        }

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch a variant's per-ancestry allele frequencies."""
        arguments = arguments or {}
        variant_id = arguments.get("variant_id")
        if not variant_id:
            return {"status": "error", "error": "variant_id is required", "data": None}

        dataset = arguments.get("dataset") or "gnomad_r4"
        graphql_args = {"variantId": variant_id, "dataset": dataset}

        result = super().run(graphql_args)
        if result.get("status") != "success":
            return result

        variant = (result.get("data") or {}).get("variant")
        if not variant:
            return {
                "status": "error",
                "error": f"No variant found for variant_id '{variant_id}' in dataset '{dataset}'",
                "url": result.get("url"),
                "data": None,
            }

        data = {
            "variant_id": variant.get("variant_id"),
            "chrom": variant.get("chrom"),
            "pos": variant.get("pos"),
            "ref": variant.get("ref"),
            "alt": variant.get("alt"),
            "rsid": variant.get("rsid"),
            "dataset": dataset,
            "genome": self._build_callset(variant.get("genome")),
            "exome": self._build_callset(variant.get("exome")),
        }

        return {
            "status": "success",
            "data": data,
            "url": result.get("url"),
        }


@register_tool("gnomADGetGeneConstraints")
class gnomADGetGeneConstraints(gnomADGraphQLTool):
    """Get gene constraint metrics from gnomAD."""

    def __init__(self, tool_config):
        super().__init__(tool_config)
        # Set default query schema if not provided in config
        if not self.query_schema:
            self.query_schema = """
query GeneConstraints(
  $geneSymbol: String!,
  $referenceGenome: ReferenceGenomeId!
) {
  gene(gene_symbol: $geneSymbol, reference_genome: $referenceGenome) {
    symbol
    gene_id
    exac_constraint {
      exp_lof
      obs_lof
      pLI
      exp_mis
      obs_mis
      exp_syn
      obs_syn
    }
    gnomad_constraint {
      exp_lof
      obs_lof
      oe_lof
      pLI
      exp_mis
      obs_mis
      oe_mis
      exp_syn
      obs_syn
      oe_syn
    }
  }
}
"""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get gene constraints."""
        gene_symbol = arguments.get("gene_symbol", "")
        if not gene_symbol:
            return {"status": "error", "error": "gene_symbol is required"}

        reference_genome = arguments.get("reference_genome") or "GRCh38"

        # Convert tool args to GraphQL variables
        graphql_args = {
            "geneSymbol": gene_symbol,
            "referenceGenome": reference_genome,
        }

        result = super().run(graphql_args)

        # Add gene_symbol to result for reference
        if result.get("status") == "success":
            result["gene_symbol"] = gene_symbol

        return result
