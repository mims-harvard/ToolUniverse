"""
Allen Brain Atlas REST API tool for ToolUniverse.

The Allen Brain Atlas provides comprehensive gene expression data across
the mouse and human brain, including in situ hybridization (ISH) data,
brain structure ontologies, and spatial gene expression.

API Documentation: https://help.brain-map.org/display/api/Allen+Brain+Atlas+API
No authentication required.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

ALLEN_BRAIN_BASE_URL = "https://api.brain-map.org/api/v2"


@register_tool("AllenBrainTool")
class AllenBrainTool(BaseTool):
    """Tool for querying the Allen Brain Atlas REST API."""

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        self.query_type = tool_config.get("fields", {}).get("query_type", "gene_search")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the Allen Brain Atlas API call."""
        try:
            query_type = self.query_type

            if query_type == "gene_search":
                return self._search_genes(arguments)
            elif query_type == "structure_search":
                return self._search_structures(arguments)
            elif query_type == "expression_data":
                return self._get_expression_data(arguments)
            elif query_type == "structure_lookup":
                return self._get_structure_by_id(arguments)
            else:
                return {"status": "error", "error": f"Unknown query type: {query_type}"}

        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"Allen Brain Atlas API request timed out after {self.timeout} seconds",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to Allen Brain Atlas API.",
            }
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response else "unknown"
            return {
                "status": "error",
                "error": f"Allen Brain Atlas API HTTP error: {status}",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error querying Allen Brain Atlas: {str(e)}",
            }

    def _make_rma_query(
        self, criteria: str, num_rows: int = 50, start_row: int = 0, include: str = None
    ) -> Dict[str, Any]:
        """Execute an RMA query against the Allen Brain Atlas API."""
        url = f"{ALLEN_BRAIN_BASE_URL}/data/query.json"
        params = {"criteria": criteria, "num_rows": num_rows, "start_row": start_row}
        if include:
            params["include"] = include
        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def _search_genes(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search for genes by acronym or name."""
        gene_acronym = arguments.get("gene_acronym", "")
        gene_name = arguments.get("gene_name", "")
        num_rows = arguments.get("num_rows", 50)

        if gene_acronym:
            criteria = f"model::Gene,rma::criteria,[acronym$eq'{gene_acronym}']"
        elif gene_name:
            criteria = f"model::Gene,rma::criteria,[name$li'*{gene_name}*']"
        else:
            return {
                "status": "error",
                "error": "Either gene_acronym or gene_name is required",
            }

        result = self._make_rma_query(criteria, num_rows=num_rows)
        if not result.get("success"):
            return {"status": "error", "error": "Allen Brain Atlas query failed"}

        records = result.get("msg", [])
        return {
            "status": "success",
            "data": records,
            "metadata": {
                "total_results": result.get("total_rows", len(records)),
                "num_rows": result.get("num_rows", num_rows),
                "start_row": result.get("start_row", 0),
            },
        }

    def _search_structures(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search for brain structures by acronym or name."""
        acronym = arguments.get("acronym", "")
        name = arguments.get("name", "")
        num_rows = arguments.get("num_rows", 50)

        if acronym:
            criteria = f"model::Structure,rma::criteria,[acronym$eq'{acronym}']"
        elif name:
            criteria = f"model::Structure,rma::criteria,[name$li'*{name}*']"
        else:
            return {"status": "error", "error": "Either acronym or name is required"}

        result = self._make_rma_query(criteria, num_rows=num_rows)
        if not result.get("success"):
            return {"status": "error", "error": "Allen Brain Atlas query failed"}

        records = result.get("msg", [])
        return {
            "status": "success",
            "data": records,
            "metadata": {
                "total_results": result.get("total_rows", len(records)),
                "num_rows": result.get("num_rows", num_rows),
            },
        }

    def _get_expression_data(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get gene expression data sets for a gene."""
        gene_acronym = arguments.get("gene_acronym", "")
        product_id = arguments.get("product_id", 1)  # 1=Mouse Brain ISH
        num_rows = arguments.get("num_rows", 50)

        if not gene_acronym:
            return {"status": "error", "error": "gene_acronym is required"}

        criteria = (
            f"model::SectionDataSet,"
            f"rma::criteria,"
            f"genes[acronym$eq'{gene_acronym}'],"
            f"products[id$eq{product_id}]"
        )

        result = self._make_rma_query(criteria, num_rows=num_rows, include="genes")
        if not result.get("success"):
            return {"status": "error", "error": "Allen Brain Atlas query failed"}

        all_records = result.get("msg", [])
        # Filter out QC-failed experiments so callers only see usable datasets
        records = [r for r in all_records if not r.get("failed", False)]
        return {
            "status": "success",
            "data": records,
            "metadata": {
                "total_results": len(records),
                "total_including_failed": len(all_records),
                "gene_acronym": gene_acronym,
                "product_id": product_id,
            },
        }

    def _get_structure_by_id(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get a brain structure by its numeric ID."""
        structure_id = arguments.get("structure_id")
        if structure_id is None:
            return {"status": "error", "error": "structure_id is required"}

        criteria = f"model::Structure,rma::criteria,[id$eq{structure_id}]"
        result = self._make_rma_query(criteria, num_rows=1)
        if not result.get("success"):
            return {"status": "error", "error": "Allen Brain Atlas query failed"}

        records = result.get("msg", [])
        if not records:
            return {
                "status": "error",
                "error": f"Structure not found with id: {structure_id}",
            }

        return {
            "status": "success",
            "data": records[0],
            "metadata": {"total_results": 1},
        }
