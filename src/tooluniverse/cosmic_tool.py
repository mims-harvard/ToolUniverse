"""
COSMIC (Catalogue of Somatic Mutations in Cancer) API tool for ToolUniverse.

COSMIC is a comprehensive database of somatic mutations in human cancer.
This tool uses the NLM Clinical Tables Search Service API for COSMIC data.

API Documentation: https://clinicaltables.nlm.nih.gov/apidoc/cosmic/v4/doc.html
"""

import requests
from typing import Dict, Any, Optional, List
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
        """
        Search COSMIC for mutations by term.

        Args:
            arguments: Dict containing:
                - terms: Search query (gene name, mutation, etc.)
                - max_results: Maximum results to return (default 20, max 500)
                - genome_build: Genome build version (37 or 38, default 37)
        """
        terms = (
            arguments.get("terms")
            or arguments.get("query")
            or arguments.get("gene", "")
        )
        if not terms:
            return {
                "status": "error",
                "error": "Missing required parameter: terms (or query/gene)",
            }

        max_results = min(arguments.get("max_results", 20), 500)
        genome_build = arguments.get("genome_build", 37)
        # Request more records than needed to compensate for deduplication:
        # COSMIC NLM API returns sample-level records (same mutation many times
        # across different cancer samples). Request up to 20x more to ensure
        # we get enough unique mutations after dedup. Cap at 500 (API limit).
        fetch_count = min(max_results * 20, 500)

        # Display fields: MutationID, GeneName, MutationCDS, MutationAA
        # Extra fields for more details
        params = {
            "terms": terms,
            "maxList": fetch_count,
            "grchv": genome_build,
            "df": "MutationID,GeneName,MutationCDS,MutationAA",
            "ef": "MutationID,GeneName,MutationCDS,MutationAA,PrimarySite,PrimaryHistology,MutationGenomePosition,MutationStrand",
        }

        try:
            response = requests.get(
                COSMIC_API_URL,
                params=params,
                timeout=self.timeout,
                headers={"User-Agent": "ToolUniverse/COSMIC"},
            )
            response.raise_for_status()
            data = response.json()

            # NLM API returns [total_count, code_list, extra_data, display_strings]
            if isinstance(data, list) and len(data) >= 4:
                total_count = data[0]
                codes = data[1] if data[1] else []
                # extra_data is a dict of field_name -> list (indexed by position)
                extra_data = data[2] if data[2] else {}

                # Parse and deduplicate results
                results = []
                seen = set()
                for i, code in enumerate(codes):
                    gene = (
                        extra_data.get("GeneName", [])[i]
                        if i < len(extra_data.get("GeneName", []))
                        else None
                    )
                    mutation_cds = (
                        extra_data.get("MutationCDS", [])[i]
                        if i < len(extra_data.get("MutationCDS", []))
                        else None
                    )
                    mutation_aa = (
                        extra_data.get("MutationAA", [])[i]
                        if i < len(extra_data.get("MutationAA", []))
                        else None
                    )
                    prim_site = (
                        extra_data.get("PrimarySite", [])[i]
                        if i < len(extra_data.get("PrimarySite", []))
                        else None
                    )
                    prim_hist = (
                        extra_data.get("PrimaryHistology", [])[i]
                        if i < len(extra_data.get("PrimaryHistology", []))
                        else None
                    )

                    # Skip entries where both CDS and AA changes are placeholders
                    _cds_placeholder = not mutation_cds or mutation_cds in ("c.?", "?")
                    _aa_placeholder = not mutation_aa or mutation_aa in ("p.?", "?")
                    if _cds_placeholder and _aa_placeholder:
                        continue

                    # Deduplicate by mutation_id + gene + CDS + AA (more specific key)
                    key = (code, gene, mutation_cds, mutation_aa)
                    if key in seen:
                        continue
                    seen.add(key)

                    result = {
                        "mutation_id": code,
                        "gene": gene,
                        "mutation_cds": mutation_cds,
                        "mutation_aa": mutation_aa,
                        "primary_site": prim_site,
                        "primary_histology": prim_hist,
                    }
                    results.append(result)
                    if len(results) >= max_results:
                        break

                return {
                    "status": "success",
                    "data": {
                        "total_count": total_count,
                        "results": results,
                        "genome_build": f"GRCh{genome_build}",
                    },
                    "metadata": {
                        "source": "COSMIC via NLM Clinical Tables API",
                        "query": terms,
                    },
                }
            else:
                return {
                    "status": "success",
                    "data": {"total_count": 0, "results": []},
                    "metadata": {"source": "COSMIC via NLM Clinical Tables API"},
                }

        except requests.exceptions.Timeout:
            return {"status": "error", "error": "Request timeout after 30 seconds"}
        except requests.exceptions.HTTPError as e:
            return {"status": "error", "error": f"HTTP error: {e.response.status_code}"}
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    def _get_mutations_by_gene(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get all mutations for a specific gene.

        Args:
            arguments: Dict containing:
                - gene: Gene symbol (e.g., BRAF, TP53)
                - max_results: Maximum results (default 100, max 500)
                - genome_build: Genome build version (37 or 38)
        """
        gene = arguments.get("gene") or arguments.get("gene_name", "")
        if not gene:
            return {
                "status": "error",
                "error": "Missing required parameter: gene (or gene_name)",
            }

        max_results = min(arguments.get("max_results", 100), 500)
        genome_build = arguments.get("genome_build", 37)
        fetch_count = min(max_results * 20, 500)

        params = {
            "terms": gene,
            "maxList": fetch_count,
            "grchv": genome_build,
            "q": f"GeneName:{gene}",
            "df": "MutationID,GeneName,MutationCDS,MutationAA",
            "ef": "MutationID,GeneName,MutationCDS,MutationAA,PrimarySite,PrimaryHistology,MutationGenomePosition,MutationStrand,Fathmm",
        }

        try:
            response = requests.get(
                COSMIC_API_URL,
                params=params,
                timeout=self.timeout,
                headers={"User-Agent": "ToolUniverse/COSMIC"},
            )
            response.raise_for_status()
            data = response.json()

            if isinstance(data, list) and len(data) >= 4:
                total_count = data[0]
                codes = data[1] if data[1] else []
                # extra_data is a dict of field_name -> list (indexed by position)
                extra_data = data[2] if data[2] else {}

                # Parse and deduplicate results
                results = []
                seen = set()
                for i, code in enumerate(codes):
                    gene_name = (
                        extra_data.get("GeneName", [])[i]
                        if i < len(extra_data.get("GeneName", []))
                        else gene
                    )
                    mutation_cds = (
                        extra_data.get("MutationCDS", [])[i]
                        if i < len(extra_data.get("MutationCDS", []))
                        else None
                    )
                    mutation_aa = (
                        extra_data.get("MutationAA", [])[i]
                        if i < len(extra_data.get("MutationAA", []))
                        else None
                    )
                    prim_site = (
                        extra_data.get("PrimarySite", [])[i]
                        if i < len(extra_data.get("PrimarySite", []))
                        else None
                    )
                    prim_hist = (
                        extra_data.get("PrimaryHistology", [])[i]
                        if i < len(extra_data.get("PrimaryHistology", []))
                        else None
                    )
                    genome_pos = (
                        extra_data.get("MutationGenomePosition", [])[i]
                        if i < len(extra_data.get("MutationGenomePosition", []))
                        else None
                    )
                    fathmm = (
                        extra_data.get("Fathmm", [])[i]
                        if i < len(extra_data.get("Fathmm", []))
                        else None
                    )

                    # Skip entries where both CDS and AA changes are placeholders
                    _cds_placeholder = not mutation_cds or mutation_cds in ("c.?", "?")
                    _aa_placeholder = not mutation_aa or mutation_aa in ("p.?", "?")
                    if _cds_placeholder and _aa_placeholder:
                        continue

                    # Deduplicate by mutation_id + gene + CDS + AA (more specific key)
                    key = (code, gene_name, mutation_cds, mutation_aa)
                    if key in seen:
                        continue
                    seen.add(key)

                    result = {
                        "mutation_id": code,
                        "gene": gene_name,
                        "mutation_cds": mutation_cds,
                        "mutation_aa": mutation_aa,
                        "primary_site": prim_site,
                        "primary_histology": prim_hist,
                        "genome_position": genome_pos,
                        "fathmm_prediction": fathmm,
                    }
                    results.append(result)
                    if len(results) >= max_results:
                        break

                return {
                    "status": "success",
                    "data": {
                        "gene": gene,
                        "total_count": total_count,
                        "results": results,
                        "genome_build": f"GRCh{genome_build}",
                    },
                    "metadata": {
                        "source": "COSMIC via NLM Clinical Tables API",
                        "gene": gene,
                    },
                }
            else:
                return {
                    "status": "success",
                    "data": {"gene": gene, "total_count": 0, "results": []},
                    "metadata": {"source": "COSMIC via NLM Clinical Tables API"},
                }

        except requests.exceptions.Timeout:
            return {"status": "error", "error": "Request timeout"}
        except requests.exceptions.HTTPError as e:
            return {"status": "error", "error": f"HTTP error: {e.response.status_code}"}
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}
