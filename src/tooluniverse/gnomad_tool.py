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
