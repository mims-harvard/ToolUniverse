"""
4DN Data Portal API Tool

This tool provides access to the 4D Nucleome Data Portal, which hosts
350+ uniformly processed Hi-C contact files and chromatin conformation data.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool


FOURDN_BASE_URL = "https://data.4dnucleome.org"


@register_tool("FourDNTool")
class FourDNTool(BaseTool):
    """
    4DN Data Portal API tool for accessing Hi-C and
    chromatin conformation data.
    """

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool with given arguments."""
        try:
            operation = arguments.get("operation", "search")

            if operation == "search":
                return self._search(arguments)
            elif operation == "get_file_metadata":
                return self._get_file_metadata(arguments)
            elif operation == "get_experiment_metadata":
                return self._get_experiment_metadata(arguments)
            elif operation == "download_file_url":
                return self._download_file_url(arguments)
            else:
                return {
                    "status": "error",
                    "data": {"error": f"Unknown operation: {operation}"},
                }

        except Exception as e:
            return {"status": "error", "data": {"error": str(e)}}

    def _search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search 4DN data portal for files or experiments."""
        try:
            query = arguments.get("query", "*")
            item_type = arguments.get("item_type", "File")
            limit = arguments.get("limit", 25)

            # Build search URL
            url = f"{FOURDN_BASE_URL}/search/"
            params = {"type": item_type, "q": query, "limit": limit, "format": "json"}

            # Add filters
            if "file_type" in arguments:
                params["file_type"] = arguments["file_type"]
            if "assay_title" in arguments:
                params["assay_title"] = arguments["assay_title"]
            if "biosource_name" in arguments:
                params["biosource_name"] = arguments["biosource_name"]

            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()

            api_data = response.json()
            results = api_data.get("@graph", [])

            result = {
                "status": "success",
                "num_results": len(results),
                "total": api_data.get("total", 0),
                "results": results[:limit],
                "search_url": response.url,
            }

            return {"status": "success", "data": result}

        except Exception as e:
            return {"status": "error", "data": {"error": str(e)}}

    def _get_file_metadata(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get metadata for a specific file."""
        try:
            file_accession = arguments.get("file_accession")
            include_full_metadata = arguments.get("include_full_metadata", False)

            if not file_accession:
                return {
                    "status": "error",
                    "data": {"error": "file_accession is required"},
                }

            # Use frame=object for smaller response (84% reduction)
            url = f"{FOURDN_BASE_URL}/{file_accession}/?format=json&frame=object"
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            api_data = response.json()

            # Handle file_format - can be dict or string with frame=object
            file_format = api_data.get("file_format")
            if isinstance(file_format, dict):
                file_format = file_format.get("display_title")
            elif isinstance(file_format, str):
                # Extract format from URL like /file-formats/bw/
                file_format = (
                    file_format.split("/")[-2] if "/" in file_format else file_format
                )

            result = {
                "status": "success",
                "accession": file_accession,
                "file_type": api_data.get("file_type"),
                "file_format": file_format,
                "file_size": api_data.get("file_size"),
                "description": api_data.get("description"),
                "data_status": api_data.get("status"),
                "biosource": api_data.get("biosource"),
                "experiment": api_data.get("experiment"),
                "download_url": (f"{FOURDN_BASE_URL}/{file_accession}/@@download"),
            }

            # Only include full metadata if explicitly requested
            # This reduces response size by ~97% in typical cases
            if include_full_metadata:
                result["metadata"] = api_data

            return {"status": "success", "data": result}

        except Exception as e:
            return {"status": "error", "data": {"error": str(e)}}

    def _get_experiment_metadata(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get metadata for a specific experiment."""
        try:
            experiment_accession = arguments.get("experiment_accession")
            include_full_metadata = arguments.get("include_full_metadata", False)

            if not experiment_accession:
                return {
                    "status": "error",
                    "data": {"error": "experiment_accession is required"},
                }

            # Use frame=object for smaller response
            url = f"{FOURDN_BASE_URL}/{experiment_accession}/?format=json&frame=object"
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            api_data = response.json()

            # Extract biosource from biosample
            # (biosource is nested inside biosample)
            biosample = api_data.get("biosample", {})
            # Handle biosample - can be dict or string with frame=object
            if isinstance(biosample, str):
                biosample = {"@id": biosample}
                biosource_list = []
                biosource_summary = ""
            else:
                biosource_list = biosample.get("biosource", [])
                biosource_summary = biosample.get("biosource_summary", "")

            # Combine files from different possible fields
            files = api_data.get("files", [])
            if not files:
                files = api_data.get("processed_files", [])

            # Handle experiment_type - can be dict or string
            exp_type = api_data.get("experiment_type")
            if isinstance(exp_type, dict):
                exp_type_name = exp_type.get("display_title")
            elif isinstance(exp_type, str):
                # Extract from URL like /experiment-types/in-situ-hi-c/
                exp_type_name = (
                    exp_type.split("/")[-2].replace("-", " ")
                    if "/" in exp_type
                    else exp_type
                )
            else:
                exp_type_name = None

            result = {
                "status": "success",
                "accession": experiment_accession,
                "experiment_type": exp_type_name,
                "biosample": biosample,
                "biosource": biosource_list,
                "biosource_summary": biosource_summary,
                "description": api_data.get("description"),
                "data_status": api_data.get("status"),
                "files": files,
            }

            # Only include full metadata if explicitly requested
            if include_full_metadata:
                result["metadata"] = api_data

            return {"status": "success", "data": result}

        except Exception as e:
            return {"status": "error", "data": {"error": str(e)}}

    def _download_file_url(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get download URL for file (requires authentication)."""
        try:
            file_accession = arguments.get("file_accession")

            if not file_accession:
                return {
                    "status": "error",
                    "data": {"error": "file_accession is required"},
                }

            # Get DRS API information
            drs_url = f"{FOURDN_BASE_URL}/ga4gh/drs/v1/objects/{file_accession}"

            result = {
                "status": "success",
                "accession": file_accession,
                "download_url": (f"{FOURDN_BASE_URL}/{file_accession}/@@download"),
                "drs_url": drs_url,
                "note": (
                    "File download requires authentication. "
                    "Use curl with access key: "
                    "curl -O -L --user <key>:<secret> <download-url>"
                ),
                "instruction": ("Create access key at https://data.4dnucleome.org/me"),
            }

            return {"status": "success", "data": result}

        except Exception as e:
            return {"status": "error", "data": {"error": str(e)}}
