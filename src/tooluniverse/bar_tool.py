# bar_tool.py
"""
BAR (Bio-Analytic Resource for Plant Biology) tools for ToolUniverse.

The BAR (bar.utoronto.ca), a Global Core Biodata Resource, is the
standard resource for Arabidopsis and other plant species' gene
annotation and expression data -- something ToolUniverse's existing
plant tool (plant_reactome_tool.py, pathway-level only) has no
equivalent for. It publishes a documented, unauthenticated OpenAPI
spec at /api/swagger.json; this wraps two of its endpoints: per-gene
annotation/position/aliases, and RNA-seq expression (including
single-cell cluster-level expression means).

API: https://bar.utoronto.ca/api
No authentication required.
"""

from typing import Any, Dict

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

BAR_API_URL = "https://bar.utoronto.ca/api"


def _bar_get(url: str, timeout: int):
    """GET a BAR endpoint, returning (payload, error_envelope).

    Exactly one of the two is non-None; the error envelope is the standard
    {"status": "error", ...} dict so callers never raise.
    """
    try:
        resp = requests.get(url, timeout=timeout)
    except requests.exceptions.Timeout:
        return None, {"status": "error", "error": f"BAR request timed out after {timeout}s"}
    except requests.exceptions.RequestException as e:
        return None, {"status": "error", "error": f"BAR request failed: {e}"}

    if resp.status_code == 400:
        try:
            detail = resp.json().get("error")
        except ValueError:
            detail = None
        return None, {"status": "error", "error": detail or "BAR rejected the request."}
    resp.raise_for_status()
    try:
        payload = resp.json()
    except ValueError:
        return None, {"status": "error", "error": "BAR returned a non-JSON response."}
    if not payload.get("wasSuccessful", True):
        return None, {
            "status": "error",
            "error": payload.get("error") or "BAR reported an unsuccessful request.",
        }
    return payload, None


@register_tool("BARTool")
class BARTool(BaseTool):
    """
    Tool for querying the BAR (Bio-Analytic Resource for Plant Biology),
    dispatched by fields.operation:
      - "get_gene_info"        : gene position, strand, aliases, annotation
      - "get_rnaseq_expression" : RNA-seq expression (bulk or single-cell
                                  cluster means) for a gene

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        self.operation = tool_config.get("fields", {}).get(
            "operation", "get_gene_info"
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if self.operation == "get_gene_info":
            return self._get_gene_info(arguments)
        if self.operation == "get_rnaseq_expression":
            return self._get_rnaseq_expression(arguments)
        return {"status": "error", "error": f"Unknown operation: {self.operation}"}

    def _get_gene_info(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        species = (arguments.get("species") or "arabidopsis").strip()
        gene_id = (arguments.get("gene_id") or "").strip()
        if not gene_id:
            return {
                "status": "error",
                "error": "gene_id is required, e.g. 'AT1G01010'.",
            }

        payload, err = _bar_get(
            f"{BAR_API_URL}/gene_information/single_gene_query/{species}/{gene_id}",
            self.timeout,
        )
        if err is not None:
            return err

        record = (payload.get("data") or {}).get(gene_id.upper()) or next(
            iter((payload.get("data") or {}).values()), None
        )
        if not record:
            return {
                "status": "error",
                "error": f"No BAR gene record found for '{gene_id}' in '{species}'.",
            }

        return {
            "status": "success",
            "data": record,
            "metadata": {"species": species, "gene_id": gene_id, "source": "BAR (bar.utoronto.ca)"},
        }

    def _get_rnaseq_expression(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        species = (arguments.get("species") or "arabidopsis").strip()
        database = (arguments.get("database") or "single_cell").strip()
        gene_id = (arguments.get("gene_id") or "").strip()
        if not gene_id:
            return {
                "status": "error",
                "error": "gene_id is required, e.g. 'At1g01010'.",
            }

        payload, err = _bar_get(
            f"{BAR_API_URL}/rnaseq_gene_expression/{species}/{database}/{gene_id}",
            self.timeout,
        )
        if err is not None:
            return err

        expression = payload.get("data") or {}
        return {
            "status": "success",
            "data": expression,
            "metadata": {
                "species": species,
                "database": database,
                "gene_id": gene_id,
                "sample_count": len(expression),
                "source": "BAR (bar.utoronto.ca)",
            },
        }
