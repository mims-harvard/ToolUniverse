import json
from typing import Any, Dict
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from tooluniverse.tool_registry import register_tool


def _http_get(
    url: str,
    headers: Dict[str, str] | None = None,
    timeout: int = 30,
) -> Dict[str, Any]:
    req = Request(url, headers=headers or {})
    with urlopen(req, timeout=timeout) as resp:
        data = resp.read()
        try:
            return json.loads(data.decode("utf-8", errors="ignore"))
        except Exception:
            return {"raw": data.decode("utf-8", errors="ignore")}


def _extract_data_list(api_response: Any) -> list:
    """Extract the data list from a GTEx API response.

    API returns {"data": [...], "paging_info": {...}}.
    Falls back to the response itself if it is a list, or empty list otherwise.
    """
    if isinstance(api_response, dict) and "data" in api_response:
        return api_response.get("data", [])
    return api_response if isinstance(api_response, list) else []


def _resolve_gene_id(gene_input: str, base_url: str, timeout: int) -> str:
    """Resolve a gene symbol or unversioned Ensembl ID to a versioned GENCODE ID.

    Queries GTEx /reference/gene to resolve to the correct GENCODE v26 version.
    If a user-provided versioned ID (e.g., ENSG00000142192.21) doesn't match
    GENCODE v26, strip the version and re-resolve.
    """
    # Try resolving the input (versioned or not) via the reference API
    query_id = gene_input.split(".")[0] if gene_input.startswith("ENS") else gene_input
    url = f"{base_url}/reference/gene?geneId={query_id}&gencodeVersion=v26"
    try:
        data = _http_get(url, headers={"Accept": "application/json"}, timeout=timeout)
        genes = data.get("data", [])
        if isinstance(genes, list) and genes:
            return genes[0].get("gencodeId", gene_input)
    except Exception:
        pass
    return gene_input


@register_tool(
    "GTExExpressionTool",
    config={
        "name": "GTEx_get_expression_summary",
        "type": "GTExExpressionTool",
        "description": "Get GTEx expression summary for a gene via /expression/geneExpression",
        "parameter": {
            "type": "object",
            "properties": {
                "gene_symbol": {
                    "type": "string",
                    "description": "Gene symbol (e.g., TP53, BRCA1). Auto-resolved to GENCODE ID.",
                },
                "ensembl_gene_id": {
                    "type": "string",
                    "description": "Ensembl gene ID, e.g., ENSG00000141510",
                },
            },
            "required": [],
        },
        "settings": {"base_url": "https://gtexportal.org/api/v2", "timeout": 30},
    },
)
class GTExExpressionTool:
    def __init__(self, tool_config=None):
        self.tool_config = tool_config or {}

    def run(self, arguments: Dict[str, Any]):
        base = self.tool_config.get("settings", {}).get(
            "base_url", "https://gtexportal.org/api/v2"
        )
        timeout = int(self.tool_config.get("settings", {}).get("timeout", 30))

        # Resolve gene symbol or unversioned Ensembl ID to versioned GENCODE ID
        gene_input = arguments.get("gene_symbol") or arguments.get(
            "ensembl_gene_id", ""
        )
        if not gene_input:
            return {
                "status": "error",
                "error": "Provide gene_symbol (e.g., 'TP53') or ensembl_gene_id (e.g., 'ENSG00000141510').",
            }
        gencode_id = _resolve_gene_id(gene_input, base, timeout)

        # Feature-80A: /expression/medianGeneExpression now requires tissueSiteDetailId.
        # Use /expression/clusteredMedianGeneExpression which returns all tissues.
        query = {
            "gencodeId": gencode_id,
            "datasetId": "gtex_v8",
        }
        url = f"{base}/expression/clusteredMedianGeneExpression?{urlencode(query)}"
        try:
            api_response = _http_get(
                url, headers={"Accept": "application/json"}, timeout=timeout
            )
            # clusteredMedianGeneExpression returns data under 'medianGeneExpression' key
            if isinstance(api_response, dict):
                expression_data = api_response.get("medianGeneExpression", [])
            else:
                expression_data = _extract_data_list(api_response)

            result = {
                "status": "success",
                "source": "GTEx",
                "endpoint": "expression/clusteredMedianGeneExpression",
                "query": query,
                "data": {"geneExpression": expression_data},
            }
            # Provide hint when results are empty due to GENCODE version mismatch
            if not expression_data and gencode_id == gene_input:
                result["note"] = (
                    f"No expression data found. Could not resolve '{gene_input}' to a "
                    "versioned GENCODE ID. Try providing an Ensembl gene ID "
                    "(e.g., 'ENSG00000141510') or use GTEx_get_median_gene_expression "
                    "with a versioned ID (e.g., 'ENSG00000141510.16')."
                )
            elif not expression_data:
                result["note"] = (
                    f"No expression data found for '{gencode_id}'. The GENCODE version "
                    "may not match gtex_v8 (GENCODE v26). Try GTEx_get_median_gene_expression "
                    "with a different version suffix."
                )
            return result
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "source": "GTEx",
                "endpoint": "expression/clusteredMedianGeneExpression",
            }


@register_tool(
    "GTExEQTLTool",
    config={
        "name": "GTEx_query_eqtl",
        "type": "GTExEQTLTool",
        "description": "Query GTEx single-tissue eQTL via /association/singleTissueEqtl",
        "parameter": {
            "type": "object",
            "properties": {
                "gene_symbol": {
                    "type": "string",
                    "description": "Gene symbol (e.g., TP53, BRCA1). Auto-resolved to GENCODE ID.",
                },
                "ensembl_gene_id": {
                    "type": "string",
                    "description": "Ensembl gene ID, e.g., ENSG00000141510",
                },
                "page": {
                    "type": "integer",
                    "default": 1,
                    "minimum": 1,
                    "description": "Page number (1-based)",
                },
                "size": {
                    "type": "integer",
                    "default": 10,
                    "minimum": 1,
                    "maximum": 100,
                    "description": "Page size (1–100)",
                },
            },
            "required": [],
        },
        "settings": {"base_url": "https://gtexportal.org/api/v2", "timeout": 30},
    },
)
class GTExEQTLTool:
    def __init__(self, tool_config=None):
        self.tool_config = tool_config or {}

    def run(self, arguments: Dict[str, Any]):
        base = self.tool_config.get("settings", {}).get(
            "base_url", "https://gtexportal.org/api/v2"
        )
        timeout = int(self.tool_config.get("settings", {}).get("timeout", 30))

        # Resolve gene symbol or unversioned Ensembl ID to versioned GENCODE ID
        gene_input = (
            arguments.get("gene_symbol")
            or arguments.get("ensembl_gene_id")
            or arguments.get("gene_id")  # alias: agents pass 'gene_id'
            or arguments.get("gene")
            or arguments.get("gene_input")  # alias: legacy param name
        )
        if not gene_input:
            return {
                "status": "error",
                "error": (
                    "Provide 'gene_symbol' (e.g. 'VKORC1'), 'ensembl_gene_id' "
                    "(e.g. 'ENSG00000197708'), or 'gene' to query eQTLs."
                ),
            }
        gencode_id = _resolve_gene_id(gene_input, base, timeout)

        query: Dict[str, Any] = {
            "gencodeId": gencode_id,
            "datasetId": arguments.get("dataset_id", "gtex_v8"),
        }
        # Pass tissue filter if provided (tissueSiteDetailId is case-sensitive, e.g. 'Brain_Cortex')
        tissue = arguments.get("tissue_id") or arguments.get("tissue")
        if tissue:
            query["tissueSiteDetailId"] = tissue
        if "page" in arguments:
            # User-facing page is 1-indexed; GTEx API is 0-indexed
            query["page"] = max(0, int(arguments["page"]) - 1)
        if "size" in arguments:
            query["pageSize"] = int(arguments["size"])

        url = f"{base}/association/singleTissueEqtl?{urlencode(query)}"
        try:
            api_response = _http_get(
                url, headers={"Accept": "application/json"}, timeout=timeout
            )
            eqtl_data = _extract_data_list(api_response)

            return {
                "status": "success",
                "data": {"singleTissueEqtl": eqtl_data},
                "metadata": {
                    "source": "GTEx",
                    "endpoint": "association/singleTissueEqtl",
                    "query": query,
                },
            }
        except Exception as e:
            err = str(e)
            if "422" in err or "Unprocessable" in err:
                err = (
                    f"{err} — GTEx tissue IDs are case-sensitive "
                    "(e.g., 'Brain_Frontal_Cortex_BA9', not 'Brain_Frontal_Cortex_Ba9'). "
                    "Use GTEx_get_expression_summary to discover valid tissue IDs."
                )
            return {"status": "error", "error": err}
