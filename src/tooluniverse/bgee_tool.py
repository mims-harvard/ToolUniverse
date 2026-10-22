# bgee_tool.py
"""
Bgee (dataBase for Gene Expression Evolution) API tool for ToolUniverse.

Bgee provides curated gene expression data across multiple animal species,
enabling comparisons of expression patterns across tissues, organs, and
developmental stages. Covers 29+ species with RNA-Seq, Affymetrix, EST,
and in situ hybridization data.

API: https://www.bgee.org/api/
No authentication required. Free public access.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

# NOTE: the trailing slash is REQUIRED. Requests to "https://www.bgee.org/api"
# (no slash) never reach the Bgee application -- they are intercepted by the
# site's Cloudflare WAF and answered with an HTTP 403 challenge page
# ("cf-mitigated: challenge"). Only "https://www.bgee.org/api/?..." is routed
# to the API. This is independent of User-Agent and of any request header.
BGEE_BASE_URL = "https://www.bgee.org/api/"


@register_tool("BgeeTool")
class BgeeTool(BaseTool):
    """
    Tool for querying the Bgee gene expression database.

    Bgee integrates expression data from multiple data types (RNA-Seq,
    Affymetrix, EST, in situ hybridization) and provides curated
    present/absent expression calls across tissues and developmental stages.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "gene_search")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the Bgee API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"Bgee API request timed out after {self.timeout} seconds",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to Bgee API. Check network connectivity.",
            }
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "error": self._http_error_message(e),
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error querying Bgee: {str(e)}",
            }

    def _http_error_message(self, exc: requests.exceptions.HTTPError) -> str:
        """Build an actionable message from a failed Bgee HTTP response.

        Bgee answers bad requests with a JSON body that carries a human
        readable ``message`` (e.g. an unknown gene ID yields HTTP 404 with
        ``"Page not found."``), so surface that instead of a bare status code.
        """
        response = exc.response
        status = getattr(response, "status_code", None)
        api_message = ""
        try:
            body = response.json()
            if isinstance(body, dict):
                api_message = str(body.get("message", "")).strip()
        except (ValueError, AttributeError):
            # non-JSON body (HTML error page) or no response attached
            api_message = ""

        message = f"Bgee API HTTP error: {status}"
        if api_message:
            message += f" - {api_message}"
        if status == 404:
            message += (
                " (check that the gene ID is a valid Ensembl ID present in Bgee"
                " for the requested species, e.g. gene_id=ENSG00000141510 with"
                " species_id=9606)"
            )
        return message

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate Bgee endpoint."""
        if self.endpoint == "gene_search":
            return self._gene_search(arguments)
        elif self.endpoint == "gene_expression":
            return self._gene_expression(arguments)
        elif self.endpoint == "species_list":
            return self._species_list(arguments)
        else:
            return {"status": "error", "error": f"Unknown endpoint: {self.endpoint}"}

    @staticmethod
    def _pagination_values(
        arguments: Dict[str, Any],
        *,
        default_limit: int,
        max_limit: int = 500,
        max_offset: int | None = None,
    ) -> tuple[int, int] | Dict[str, str]:
        """Validate pagination for direct callers as strictly as the JSON schema.

        Tool classes can be invoked without ToolUniverse's schema-validation
        layer, so coercing strings or booleans with ``int()`` would otherwise
        turn malformed inputs into plausible but incorrect pages.
        """
        limit = arguments.get("limit", default_limit)
        offset = arguments.get("offset", 0)
        if isinstance(limit, bool) or not isinstance(limit, int):
            return {"status": "error", "error": "limit must be an integer"}
        if not 1 <= limit <= max_limit:
            return {
                "status": "error",
                "error": f"limit must be between 1 and {max_limit}",
            }
        if isinstance(offset, bool) or not isinstance(offset, int):
            return {"status": "error", "error": "offset must be an integer"}
        if offset < 0:
            return {"status": "error", "error": "offset must be non-negative"}
        if max_offset is not None and offset > max_offset:
            return {
                "status": "error",
                "error": f"offset must not exceed {max_offset} for this endpoint",
            }
        return limit, offset

    def _gene_search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search for genes by name or symbol across species."""
        query = arguments.get("query", "")
        if not query:
            return {"status": "error", "error": "query parameter is required"}

        pagination = self._pagination_values(
            arguments, default_limit=20, max_offset=9_999
        )
        if isinstance(pagination, dict):
            return pagination
        limit, offset = pagination
        species_id = arguments.get("species_id")

        # Bgee's official CommandGene endpoint accepts ``limit`` (up to
        # 10,000), but hard-codes the search-service offset to zero.  Request
        # enough leading records to satisfy the requested page and then slice
        # locally.  The 10,000-record upstream ceiling is reported below so a
        # broad cross-species query never looks complete when it is not.
        upstream_limit = min(offset + limit, 10_000)
        params = {
            "page": "gene",
            "action": "search",
            "query": query,
            "limit": upstream_limit,
            "display_type": "json",
        }
        if species_id is not None:
            params["species_id"] = str(species_id)

        response = requests.get(BGEE_BASE_URL, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        if data.get("code") != 200:
            return {
                "status": "error",
                "error": f"Bgee API error: {data.get('message', 'Unknown error')}",
            }

        result_data = data.get("data", {})
        gene_matches = result_data.get("result", {}).get("geneMatches", [])

        page_matches = gene_matches[offset : offset + limit]
        results = []
        for match in page_matches:
            gene = match.get("gene", {})
            species = gene.get("species", {})
            results.append(
                {
                    "gene_id": gene.get("geneId"),
                    "name": gene.get("name"),
                    "description": gene.get("description"),
                    "species_id": species.get("id"),
                    "species_name": f"{species.get('genus', '')} {species.get('speciesName', '')}".strip(),
                    "common_name": species.get("name"),
                    "gene_biotype": gene.get("geneBioType", {}).get("name"),
                    "match_source": match.get("matchSource"),
                }
            )

        total_matches = int(
            result_data.get("result", {}).get("totalMatchCount", len(gene_matches))
        )
        accessible_matches = min(total_matches, 10_000)
        next_offset = offset + len(results)
        has_more = next_offset < accessible_matches
        pagination_stalled = not results and offset < accessible_matches

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "source": "Bgee",
                "query": query,
                "species_id": str(species_id) if species_id is not None else None,
                "total_matches": total_matches,
                "accessible_matches": accessible_matches,
                "returned": len(results),
                "limit": limit,
                "offset": offset,
                "has_more": has_more,
                "truncated": has_more or total_matches > accessible_matches,
                "next_offset": next_offset if has_more else None,
                "result_set_complete": bool(
                    offset == 0
                    and len(results) == total_matches
                    and total_matches <= accessible_matches
                ),
                "pagination_stalled": pagination_stalled,
                "warning": (
                    "Bgee reported additional accessible matches but returned no records at this offset."
                    if pagination_stalled
                    else None
                ),
                "upstream_truncated": total_matches > accessible_matches,
                "upstream_limit": 10_000,
            },
        }

    def _gene_expression(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get expression data for a gene across tissues/organs."""
        gene_id = arguments.get("gene_id", "")
        species_id = arguments.get("species_id", "")
        if not gene_id:
            return {
                "status": "error",
                "error": "gene_id parameter is required (Ensembl gene ID, e.g., ENSG00000141510)",
            }
        if not species_id:
            return {
                "status": "error",
                "error": "species_id parameter is required (NCBI taxon ID, e.g., 9606 for human)",
            }

        pagination = self._pagination_values(arguments, default_limit=50)
        if isinstance(pagination, dict):
            return pagination
        limit, offset = pagination
        params = {
            "page": "gene",
            "action": "expression",
            "gene_id": gene_id,
            "species_id": species_id,
            "display_type": "json",
        }

        response = requests.get(BGEE_BASE_URL, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        if data.get("code") != 200:
            return {
                "status": "error",
                "error": f"Bgee API error: {data.get('message', 'Unknown error')}",
            }

        expr_data = data.get("data", {})
        calls = expr_data.get("calls", [])

        results = []
        for call in calls[offset : offset + limit]:
            condition = call.get("condition", {})
            anat_entity = condition.get("anatEntity", {})
            cell_type = condition.get("cellType", {})
            score_info = call.get("expressionScore", {})

            entry = {
                "tissue_id": anat_entity.get("id"),
                "tissue_name": anat_entity.get("name"),
                "expression_score": score_info.get("expressionScore"),
                "score_confidence": score_info.get("expressionScoreConfidence"),
                "expression_state": call.get("expressionState"),
                "quality": call.get("expressionQuality"),
                "data_types": call.get("dataTypesWithData", []),
            }
            if cell_type.get("id"):
                entry["cell_type_id"] = cell_type.get("id")
                entry["cell_type_name"] = cell_type.get("name")

            results.append(entry)

        next_offset = offset + len(results)
        has_more = next_offset < len(calls)
        return {
            "status": "success",
            "data": results,
            "metadata": {
                "source": "Bgee",
                "gene_id": gene_id,
                "species_id": str(species_id),
                "total_calls": len(calls),
                "returned": len(results),
                "limit": limit,
                "offset": offset,
                "has_more": has_more,
                "truncated": has_more,
                "next_offset": next_offset if has_more else None,
                "result_set_complete": offset == 0 and len(results) == len(calls),
                "pagination_stalled": False,
                "data_types": expr_data.get("requestedDataTypes", []),
            },
        }

    def _species_list(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List all species available in Bgee."""
        params = {
            "page": "species",
            "display_type": "json",
        }

        response = requests.get(BGEE_BASE_URL, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        if data.get("code") != 200:
            return {
                "status": "error",
                "error": f"Bgee API error: {data.get('message', 'Unknown error')}",
            }

        species_data = data.get("data", {}).get("species", [])

        results = []
        for sp in species_data:
            results.append(
                {
                    "species_id": sp.get("id"),
                    "genus": sp.get("genus"),
                    "species_name": sp.get("speciesName"),
                    "common_name": sp.get("name"),
                    "genome_version": sp.get("genomeVersion"),
                    "full_name": f"{sp.get('genus', '')} {sp.get('speciesName', '')}".strip(),
                }
            )

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "source": "Bgee",
                "total_species": len(results),
            },
        }
