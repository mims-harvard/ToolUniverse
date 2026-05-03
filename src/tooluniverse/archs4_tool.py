"""
ARCHS4 Tool - All RNA-seq and ChIP-seq Sample and Signature Search

Provides access to ARCHS4 APIs for querying pre-computed gene expression
across tissues and cell lines, and gene co-expression correlations from
300K+ uniformly processed RNA-seq samples.

API base: https://maayanlab.cloud/archs4/
Correlation API: https://maayanlab.cloud/matrixapi/
No authentication required.

Reference: Lachmann et al., Nature Communications 2018
"""

import csv
import io
import requests
from typing import Dict, Any

from .base_tool import BaseTool
from .tool_registry import register_tool


ARCHS4_BASE_URL = "https://maayanlab.cloud/archs4"
MATRIX_API_URL = "https://maayanlab.cloud/matrixapi"


@register_tool("ARCHS4Tool")
class ARCHS4Tool(BaseTool):
    """
    Tool for querying the ARCHS4 gene expression database.

    ARCHS4 provides uniformly processed RNA-seq data from GEO, covering
    300K+ human and mouse samples with pre-computed expression levels
    and gene co-expression correlations.

    Supported operations:
    - get_gene_expression: Get expression across tissues/cell lines for a gene
    - get_gene_correlations: Get co-expressed genes (Pearson correlation)
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.parameter = tool_config.get("parameter", {})
        self.required = self.parameter.get("required", [])
        self.session = requests.Session()
        self.timeout = 30

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        operation = (
            arguments.get("operation")
            or self.tool_config.get("fields", {}).get("operation")
            or self.get_schema_const_operation()
        )
        if not operation:
            return {"status": "error", "error": "Missing required parameter: operation"}

        handlers = {
            "get_gene_expression": self._get_gene_expression,
            "get_gene_correlations": self._get_gene_correlations,
        }

        handler = handlers.get(operation)
        if not handler:
            return {
                "status": "error",
                "error": "Unknown operation: {}. Available: {}".format(
                    operation, list(handlers.keys())
                ),
            }

        try:
            return handler(arguments)
        except requests.exceptions.Timeout:
            return {"status": "error", "error": "ARCHS4 API request timed out"}
        except requests.exceptions.ConnectionError:
            return {"status": "error", "error": "Failed to connect to ARCHS4 API"}
        except Exception as e:
            return {"status": "error", "error": "ARCHS4 error: {}".format(str(e))}

    def _get_gene_expression(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get gene expression across tissues or cell lines from ARCHS4."""
        gene = arguments.get("gene") or arguments.get("search")
        if not gene:
            return {"status": "error", "error": "Missing required parameter: gene"}

        species = arguments.get("species", "human")
        expression_type = arguments.get("type", "tissue")

        params = {
            "search": gene,
            "species": species,
            "type": expression_type,
        }

        url = "{}/search/loadExpressionTissue.php".format(ARCHS4_BASE_URL)
        response = self.session.get(url, params=params, timeout=self.timeout)

        if response.status_code != 200:
            return {
                "status": "error",
                "error": "ARCHS4 expression API returned HTTP {}".format(
                    response.status_code
                ),
            }

        text = response.text.strip()
        if not text:
            return {
                "status": "error",
                "error": "No expression data found for gene: {}".format(gene),
            }

        # Parse CSV response
        reader = csv.reader(io.StringIO(text))
        header = next(reader, None)
        if not header:
            return {"status": "error", "error": "Empty response from ARCHS4"}

        tissues = []
        categories = []
        for row in reader:
            if len(row) < 6:
                continue
            tissue_id = row[0]
            min_val, q1, median, q3, max_val = row[1], row[2], row[3], row[4], row[5]

            # Skip category headers (no expression values)
            if not median:
                categories.append(tissue_id)
                continue

            entry = {
                "tissue": tissue_id,
                "min": float(min_val) if min_val else None,
                "q1": float(q1) if q1 else None,
                "median": float(median) if median else None,
                "q3": float(q3) if q3 else None,
                "max": float(max_val) if max_val else None,
            }
            tissues.append(entry)

        # Sort by median expression descending
        tissues.sort(key=lambda x: x.get("median") or 0, reverse=True)

        return {
            "status": "success",
            "data": tissues,
            "metadata": {
                "gene": gene,
                "species": species,
                "type": expression_type,
                "tissue_count": len(tissues),
                "unit": "log2(TPM+1)",
            },
        }

    def _get_gene_correlations(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get co-expressed genes for a query gene from ARCHS4."""
        gene = arguments.get("gene") or arguments.get("id")
        if not gene:
            return {"status": "error", "error": "Missing required parameter: gene"}

        count = arguments.get("count", 20)
        if count < 2:
            count = 2
        if count > 200:
            count = 200

        # Use the matrixapi POST endpoint
        url = "{}/coltop".format(MATRIX_API_URL)
        payload = {"id": gene, "count": count + 1}  # +1 because first result is self

        response = self.session.post(url, json=payload, timeout=self.timeout)

        if response.status_code != 200:
            return {
                "status": "error",
                "error": "ARCHS4 correlation API returned HTTP {}".format(
                    response.status_code
                ),
            }

        data = response.json()
        gene_ids = data.get("rowids", [])
        values = data.get("values", [])

        correlations = []
        for i, (gid, val) in enumerate(zip(gene_ids, values)):
            # Skip self-correlation (first entry)
            if gid.upper() == gene.upper():
                continue
            correlations.append(
                {
                    "gene": gid,
                    "pearson_correlation": round(val, 6),
                    "rank": len(correlations) + 1,
                }
            )

        return {
            "status": "success",
            "data": correlations,
            "metadata": {
                "query_gene": gene,
                "returned": len(correlations),
                "note": "Pearson correlation computed across 300K+ uniformly processed RNA-seq samples",
            },
        }
