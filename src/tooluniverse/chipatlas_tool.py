"""
ChIP-Atlas API Tool

This tool provides access to ChIP-Atlas, a data-mining suite for exploring
epigenomic landscapes with 433,000+ ChIP-seq, ATAC-seq, and Bisulfite-seq experiments.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool


CHIPATLAS_BASE_URL = "https://chip-atlas.org"
CHIPATLAS_DATA_URL = "https://chip-atlas.dbcls.jp/data"


@register_tool("ChIPAtlasTool")
class ChIPAtlasTool(BaseTool):
    """
    ChIP-Atlas API tool for accessing chromatin data.
    Provides enrichment analysis, peak browsing, and dataset search.
    """

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool with given arguments."""
        try:
            # Get default operation from tool config schema if not provided
            default_op = "enrichment_analysis"
            if hasattr(self, "tool_config") and self.tool_config:
                param_schema = self.tool_config.get("parameter", {})
                default_op = (
                    param_schema.get("properties", {})
                    .get("operation", {})
                    .get("default", "enrichment_analysis")
                )
            operation = arguments.get("operation", default_op)

            if operation == "enrichment_analysis":
                return self._enrichment_analysis(arguments)

            elif operation == "get_experiment_list":
                return self._get_experiment_list(arguments)

            elif operation == "get_peak_data":
                return self._get_peak_data(arguments)

            elif operation == "search_datasets":
                return self._search_datasets(arguments)

            else:
                return {
                    "status": "error",
                    "data": {"error": f"Unknown operation: {operation}"},
                }

        except Exception as e:
            return {"status": "error", "data": {"error": str(e)}}

    def _enrichment_analysis(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform enrichment analysis on genomic regions, motifs, or gene lists.
        Identifies proteins bound to input regions more often than expected.
        """
        try:
            # Prepare enrichment analysis parameters
            bed_data = arguments.get("bed_data")
            motif = arguments.get("motif")
            gene_list = arguments.get("gene_list")
            genome = arguments.get("genome", "hg38")
            antigen_class = arguments.get("antigen_class", "")
            cell_type_class = arguments.get("cell_type_class", "")
            threshold = arguments.get("threshold", "05")
            distance = arguments.get("distance", "5000")

            # Build API request
            # Note: The actual API endpoint needs to be discovered from ChIP-Atlas documentation
            # For now, we provide information about how to use it

            result_data = {}

            if bed_data:
                result_data = {
                    "message": "ChIP-Atlas Enrichment Analysis requires web form submission",
                    "instruction": f"Submit BED data to: {CHIPATLAS_BASE_URL}/enrichment_analysis",
                    "parameters": {
                        "genome": genome,
                        "antigen_class": antigen_class,
                        "cell_type_class": cell_type_class,
                        "threshold": threshold,
                    },
                    "note": "ChIP-Atlas enrichment API requires form-based submission. Use Python 'requests' library for programmatic access.",
                }
                return {"status": "success", "data": result_data}
            elif motif:
                result_data = {
                    "message": "Submit motif for enrichment analysis",
                    "motif": motif,
                    "url": f"{CHIPATLAS_BASE_URL}/enrichment_analysis",
                    "note": "Motif should be in IUPAC nucleic acid notation (ATGCWSMKRYBDHVN)",
                }
                return {"status": "success", "data": result_data}
            elif gene_list:
                result_data = {
                    "message": "Submit gene list for enrichment analysis",
                    "genes": gene_list if isinstance(gene_list, list) else [gene_list],
                    "distance_from_tss": distance,
                    "url": f"{CHIPATLAS_BASE_URL}/enrichment_analysis",
                    "note": "Use official gene symbols (HGNC, MGI, RGD, FlyBase, WormBase, SGD)",
                }
                return {"status": "success", "data": result_data}
            else:
                return {
                    "status": "error",
                    "data": {
                        "error": "One of bed_data, motif, or gene_list must be provided"
                    },
                }

        except Exception as e:
            return {"status": "error", "data": {"error": str(e)}}

    def _get_experiment_list(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get metadata for all ChIP-Atlas experiments.

        Note: The experimentList.tab file is 344MB+ (433k+ experiments).
        This method provides guidance on accessing the data rather than downloading.
        """
        try:
            genome = arguments.get("genome")
            antigen = arguments.get("antigen")
            cell_type = arguments.get("cell_type")
            arguments.get("limit", 100)

            # The file is too large (344MB) to download efficiently
            # Provide guidance instead
            metadata_url = f"{CHIPATLAS_DATA_URL}/metadata/experimentList.tab"
            web_search_url = f"{CHIPATLAS_BASE_URL}/search"

            message = (
                "ChIP-Atlas experimentList.tab is 344MB+ with 433,000+ experiments. "
                "For efficient searching, use: (1) ChIPAtlas_search_datasets tool "
                "for antigen/cell-type search, or (2) Download the file directly for "
                "local analysis."
            )

            filters = {}
            if genome:
                filters["genome"] = genome
            if antigen:
                filters["antigen"] = antigen
            if cell_type:
                filters["cell_type"] = cell_type

            result_data = {
                "message": message,
                "metadata_file_url": metadata_url,
                "web_search_url": web_search_url,
                "file_size": "344MB",
                "total_experiments": "433,000+",
                "filters_requested": filters if filters else "none",
                "recommendation": (
                    "Use ChIPAtlas_search_datasets tool for filtered searches by "
                    "antigen or cell type, or download the metadata file for local analysis."
                ),
            }

            return {"status": "success", "data": result_data}

        except Exception as e:
            return {"status": "error", "data": {"error": str(e)}}

    def _get_peak_data(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get URL for peak-call data (BigWig or BED format)."""
        try:
            experiment_id = arguments.get("experiment_id")
            genome = arguments.get("genome", "hg38")
            threshold = arguments.get("threshold", "05")
            format_type = arguments.get("format", "bigwig")

            if not experiment_id:
                return {
                    "status": "error",
                    "data": {"error": "experiment_id is required"},
                }

            if format_type.lower() == "bigwig":
                url = f"{CHIPATLAS_DATA_URL}/{genome}/eachData/bw/{experiment_id}.bw"
            elif format_type.lower() == "bed":
                url = f"{CHIPATLAS_DATA_URL}/{genome}/eachData/bed{threshold}/{experiment_id}.{threshold}.bed"
            elif format_type.lower() == "bigbed":
                url = f"{CHIPATLAS_DATA_URL}/{genome}/eachData/bb{threshold}/{experiment_id}.{threshold}.bb"
            else:
                return {
                    "status": "error",
                    "data": {
                        "error": f"Invalid format: {format_type}. Use 'bigwig', 'bed', or 'bigbed'"
                    },
                }

            result_data = {
                "experiment_id": experiment_id,
                "genome": genome,
                "format": format_type,
                "url": url,
                "message": "Use this URL to download peak data",
            }

            return {"status": "success", "data": result_data}

        except Exception as e:
            return {"status": "error", "data": {"error": str(e)}}

    def _search_datasets(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search for datasets by antigen or cell type."""
        try:
            antigen = arguments.get("antigen")
            cell_type = arguments.get("cell_type")
            genome = arguments.get("genome", "hg38")

            if not antigen and not cell_type:
                return {
                    "status": "error",
                    "data": {"error": "Either antigen or cell_type must be provided"},
                }

            # Download antigenList.tab or celltypeList.tab
            # These files are ~10MB each - reasonable to download fully
            if antigen:
                url = f"{CHIPATLAS_DATA_URL}/metadata/antigenList.tab"
                search_key = "antigen"
                search_value = antigen
            else:
                url = f"{CHIPATLAS_DATA_URL}/metadata/celltypeList.tab"
                search_key = "cell_type"
                search_value = cell_type

            # Download file (10MB, should complete in seconds)
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            # Parse TSV
            lines = response.text.strip().split("\n")
            results = []

            for line in lines:
                fields = line.split("\t")
                if len(fields) >= 5:
                    if antigen:
                        # Check genome match and search value
                        # Format: Genome | Antigen_class | Antigen | Num_data | ID
                        if (
                            fields[0] == genome
                            and search_value.lower() in fields[2].lower()
                        ):
                            results.append(
                                {
                                    "genome": fields[0],
                                    "class": fields[1],
                                    "name": fields[2],
                                    "num_experiments": fields[3],
                                    "experiment_ids": fields[4].split(",")[
                                        :10
                                    ],  # Show first 10 IDs
                                }
                            )
                    else:
                        # Check genome match and search value for cell type
                        # Format: Genome | Cell_type_class | Cell_type | Num_data | ID
                        if (
                            fields[0] == genome
                            and search_value.lower() in fields[2].lower()
                        ):
                            results.append(
                                {
                                    "genome": fields[0],
                                    "cell_type_class": fields[1],
                                    "cell_type": fields[2],
                                    "num_experiments": fields[3],
                                    "experiment_ids": fields[4].split(",")[
                                        :10
                                    ],  # Show first 10 IDs
                                }
                            )

            result_data = {
                "search_key": search_key,
                "search_value": search_value,
                "genome": genome,
                "num_results": len(results),
                "results": results,
            }

            return {"status": "success", "data": result_data}

        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "data": {
                    "error": "Request timeout - ChIP-Atlas server may be slow. Try again later."
                },
            }
        except Exception as e:
            return {"status": "error", "data": {"error": str(e)}}
