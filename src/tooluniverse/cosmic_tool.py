"""
COSMIC (Catalogue of Somatic Mutations in Cancer) API tool for ToolUniverse.

COSMIC is a comprehensive database of somatic mutations in human cancer.
This tool uses the NLM Clinical Tables Search Service API for COSMIC data.

API Documentation: https://clinicaltables.nlm.nih.gov/apidoc/cosmic/v4/doc.html
"""

import re
from collections import OrderedDict
from typing import Any, Dict, Optional

import requests
from .base_tool import BaseTool
from .tool_registry import register_tool

# Base URL for COSMIC via NLM Clinical Tables API
COSMIC_API_URL = "https://clinicaltables.nlm.nih.gov/api/cosmic/v4/search"


@register_tool("COSMICTool")
class COSMICTool(BaseTool):
    """
    Tool for querying COSMIC (Catalogue of Somatic Mutations in Cancer).

    COSMIC provides:
    - Somatic mutation data in human cancers
    - Gene-level mutation information
    - Mutation coordinates and amino acid changes
    - Associated cancer types

    Uses NLM Clinical Tables API. No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout: int = tool_config.get("timeout", 30)
        self.parameter = tool_config.get("parameter", {})

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the COSMIC API call based on operation type."""
        operation = arguments.get("operation")
        if not operation:
            # Infer operation from tool config const value (each COSMIC tool
            # has a fixed const in the schema, e.g., "search" or "get_by_gene")
            schema_op = (
                self.parameter.get("properties", {}).get("operation", {}).get("const")
            )
            operation = schema_op or "search"

        if operation == "search":
            return self._search_mutations(arguments)
        elif operation == "get_by_gene":
            return self._get_mutations_by_gene(arguments)
        else:
            return {
                "status": "error",
                "error": f"Unknown operation: {operation}. Supported: search, get_by_gene",
            }

    def _search_mutations(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search COSMIC by free text without hiding its non-pageable window."""
        terms = arguments.get("terms")
        if not isinstance(terms, str) or not terms.strip():
            return {
                "status": "error",
                "error": "terms must be a non-empty string",
                "parameter": "terms",
            }
        validated = self._validate_controls(arguments, default_max_results=20)
        if isinstance(validated, dict):
            return validated
        max_results, genome_build = validated
        return self._query_mutations(
            terms=terms.strip(),
            max_results=max_results,
            genome_build=genome_build,
            query_filter=None,
        )

    def _get_mutations_by_gene(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get mutations for one HGNC-style gene symbol."""
        gene = arguments.get("gene")
        if not isinstance(gene, str) or not re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9._-]*", gene.strip()
        ):
            return {
                "status": "error",
                "error": "gene must be a non-empty gene symbol using letters, digits, '.', '_' or '-'",
                "parameter": "gene",
            }
        validated = self._validate_controls(arguments, default_max_results=100)
        if isinstance(validated, dict):
            return validated
        max_results, genome_build = validated
        gene = gene.strip()
        result = self._query_mutations(
            terms=gene,
            max_results=max_results,
            genome_build=genome_build,
            query_filter=f"GeneName:{gene}",
        )
        if result.get("status") == "success":
            result["data"]["gene"] = gene
            result["metadata"]["gene"] = gene
        return result

    @staticmethod
    def _validate_controls(arguments: Dict[str, Any], default_max_results: int):
        max_results = arguments.get("max_results", default_max_results)
        if (
            isinstance(max_results, bool)
            or not isinstance(max_results, int)
            or not 1 <= max_results <= 500
        ):
            return {
                "status": "error",
                "error": "max_results must be an integer between 1 and 500",
                "parameter": "max_results",
            }
        genome_build = arguments.get("genome_build", 37)
        if (
            isinstance(genome_build, bool)
            or not isinstance(genome_build, int)
            or genome_build not in (37, 38)
        ):
            return {
                "status": "error",
                "error": "genome_build must be 37 or 38",
                "parameter": "genome_build",
            }
        return max_results, genome_build

    @staticmethod
    def _field(extra_data: Dict[str, Any], field: str, index: int):
        values = extra_data.get(field)
        return values[index] if isinstance(values, list) and index < len(values) else None

    def _query_mutations(
        self,
        terms: str,
        max_results: int,
        genome_build: int,
        query_filter: Optional[str],
    ) -> Dict[str, Any]:
        """Retrieve and aggregate the one upstream window COSMIC permits.

        NLM explicitly disables pagination for this licensed data set.  We always
        request its full 500-record accessible window so result prefixes do not
        change with ``max_results`` and repeated sample contexts can be aggregated.
        """
        fields = (
            "MutationID,GeneName,MutationCDS,MutationAA,PrimarySite,"
            "PrimaryHistology,MutationGenomePosition,MutationStrand,Fathmm"
        )
        params = {
            "terms": terms,
            "maxList": 500,
            "grchv": genome_build,
            "df": "MutationID,GeneName,MutationCDS,MutationAA",
            "ef": fields,
        }
        if query_filter:
            params["q"] = query_filter

        try:
            response = requests.get(
                COSMIC_API_URL,
                params=params,
                timeout=self.timeout,
                headers={"User-Agent": "ToolUniverse/COSMIC"},
            )
            response.raise_for_status()
            payload = response.json()
        except requests.exceptions.Timeout:
            return {"status": "error", "error": f"Request timeout after {self.timeout} seconds"}
        except requests.exceptions.HTTPError as exc:
            return {"status": "error", "error": f"HTTP error: {exc.response.status_code}"}
        except requests.exceptions.RequestException as exc:
            return {"status": "error", "error": f"Request failed: {exc}"}
        except ValueError as exc:
            return {"status": "error", "error": f"Invalid JSON response: {exc}"}

        if not isinstance(payload, list) or len(payload) < 4:
            return {
                "status": "error",
                "error": "Invalid COSMIC API response format",
                "raw_response": payload,
            }

        try:
            total_count = int(payload[0])
        except (TypeError, ValueError):
            return {"status": "error", "error": "Invalid COSMIC total count"}
        codes = payload[1] if isinstance(payload[1], list) else []
        extra_data = payload[2] if isinstance(payload[2], dict) else {}

        grouped: OrderedDict[tuple, Dict[str, Any]] = OrderedDict()
        for index, code in enumerate(codes):
            gene = self._field(extra_data, "GeneName", index)
            mutation_cds = self._field(extra_data, "MutationCDS", index)
            mutation_aa = self._field(extra_data, "MutationAA", index)
            key = (code, gene, mutation_cds, mutation_aa)
            if key not in grouped:
                grouped[key] = {
                    "mutation_id": code,
                    "gene": gene,
                    "mutation_cds": mutation_cds,
                    "mutation_aa": mutation_aa,
                    "genome_position": self._field(
                        extra_data, "MutationGenomePosition", index
                    ),
                    "mutation_strand": self._field(extra_data, "MutationStrand", index),
                    "fathmm_prediction": self._field(extra_data, "Fathmm", index),
                    "cancer_contexts": [],
                }
            context = {
                "primary_site": self._field(extra_data, "PrimarySite", index),
                "primary_histology": self._field(
                    extra_data, "PrimaryHistology", index
                ),
            }
            if context not in grouped[key]["cancer_contexts"]:
                grouped[key]["cancer_contexts"].append(context)

        accessible_unique = list(grouped.values())
        results = accessible_unique[:max_results]
        raw_count = len(codes)
        upstream_truncated = total_count > raw_count
        has_more_in_window = len(accessible_unique) > len(results)
        total_may_be_capped = total_count >= 10_000
        warning = None
        if upstream_truncated:
            warning = (
                "The NLM COSMIC service does not support pagination due to source-data "
                "terms of use. These unique mutations are aggregated only from its first "
                f"{raw_count} matching source records; refine the query for other records."
            )
            if total_may_be_capped:
                warning += " The server-reported total is capped at 10,000 and may be lower than the actual total."

        data = {
            "total_count": total_count,
            "count": len(results),
            "results": results,
            "genome_build": f"GRCh{genome_build}",
        }
        metadata = {
            "source": "COSMIC via NLM Clinical Tables API",
            "query": terms,
            "server_reported_total": total_count,
            "server_total_may_be_capped": total_may_be_capped,
            "raw_records_retrieved": raw_count,
            "accessible_unique_mutations": len(accessible_unique),
            "returned_count": len(results),
            "max_results": max_results,
            "pagination_supported": False,
            "has_more_in_accessible_window": has_more_in_window,
            "upstream_truncated": upstream_truncated,
            "truncated": upstream_truncated or has_more_in_window,
            "result_set_complete": not upstream_truncated and not has_more_in_window,
            "next_offset": None,
            "warning": warning,
        }
        return {"status": "success", "data": data, "metadata": metadata}
