"""
Rfam Database API Tool

This tool provides access to the Rfam database (v15.1, January 2026) containing
4,227 RNA families. Rfam provides multiple sequence alignments, consensus secondary
structures, covariance models, and annotations for non-coding RNA families.
"""

import requests
import time
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

RFAM_BASE_URL = "https://rfam.org"
RFAM_BATCH_URL = "https://batch.rfam.org"


@register_tool("RfamTool")
class RfamTool(BaseTool):
    """
    Rfam Database API tool for RNA family data.

    Provides access to:
    - RNA family information and metadata
    - Secondary structure diagrams
    - Covariance models
    - Sequence alignments (Stockholm, FASTA formats)
    - Phylogenetic trees
    - Sequence searches
    """

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.parameter = tool_config.get("parameter", {})
        self.required = self.parameter.get("required", [])

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the Rfam API tool with given arguments."""
        # Validate required parameters
        for param in self.required:
            if param not in arguments or arguments[param] is None:
                return {
                    "status": "error",
                    "error": f"Missing required parameter: {param}",
                }

        operation = arguments.get("operation")
        if not operation:
            return {"status": "error", "error": "Missing required parameter: operation"}

        # Route to appropriate operation handler
        operation_handlers = {
            "get_family": self._get_family,
            "get_family_accession": self._get_family_accession,
            "get_family_id": self._get_family_id,
            "get_covariance_model": self._get_covariance_model,
            "get_alignment": self._get_alignment,
            "get_tree_data": self._get_tree_data,
            "get_sequence_regions": self._get_sequence_regions,
            "get_structure_mapping": self._get_structure_mapping,
            "search_sequence": self._search_sequence,
        }

        handler = operation_handlers.get(operation)
        if not handler:
            return {
                "status": "error",
                "error": f"Unknown operation: {operation}",
                "available_operations": list(operation_handlers.keys()),
            }

        try:
            return handler(arguments)
        except Exception as e:
            return {
                "status": "error",
                "error": f"Operation failed: {str(e)}",
                "operation": operation,
            }

    def _get_family(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get RNA family information."""
        family_id = arguments.get("family_id")
        format_type = arguments.get("format", "json")

        if not family_id:
            return {
                "status": "error",
                "error": "family_id is required (RF accession or family name)",
            }

        # Build URL with content type
        url = f"{RFAM_BASE_URL}/family/{family_id}"

        headers = {}
        if format_type == "json":
            headers["Accept"] = "application/json"
        elif format_type == "xml":
            headers["Accept"] = "text/xml"

        response = requests.get(url, headers=headers, timeout=30)

        if response.status_code == 200:
            if format_type == "json":
                return {
                    "status": "success",
                    "data": response.json(),
                    "family_id": family_id,
                }
            else:
                return {
                    "status": "success",
                    "data": response.text,
                    "format": format_type,
                    "family_id": family_id,
                }
        elif response.status_code == 404:
            return {
                "status": "error",
                "error": f"Family {family_id} not found",
                "message": "Check family ID/accession is correct",
            }
        else:
            return {
                "status": "error",
                "error": f"API request failed with status {response.status_code}",
                "detail": response.text[:500],
            }

    def _get_family_accession(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Convert family ID to accession."""
        family_id = arguments.get("family_id")

        if not family_id:
            return {"status": "error", "data": {"error": "family_id is required"}}

        url = f"{RFAM_BASE_URL}/family/{family_id}/acc"
        response = requests.get(url, timeout=30)

        if response.status_code == 200:
            result = {
                "accession": response.text.strip(),
                "family_id": family_id,
            }
            return {"status": "success", "data": result}
        else:
            return {
                "status": "error",
                "data": {
                    "error": f"Failed to get accession for {family_id}",
                    "detail": response.text[:500],
                },
            }

    def _get_family_id(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Convert family accession to ID."""
        accession = arguments.get("accession")

        if not accession:
            return {
                "status": "error",
                "data": {"error": "accession is required (e.g., RF00360)"},
            }

        url = f"{RFAM_BASE_URL}/family/{accession}/id"
        response = requests.get(url, timeout=30)

        if response.status_code == 200:
            result = {
                "family_id": response.text.strip(),
                "accession": accession,
            }
            return {"status": "success", "data": result}
        else:
            return {
                "status": "error",
                "data": {
                    "error": f"Failed to get ID for accession {accession}",
                    "detail": response.text[:500],
                },
            }

    def _get_covariance_model(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get covariance model for RNA family."""
        family_id = arguments.get("family_id")

        if not family_id:
            return {"status": "error", "data": {"error": "family_id is required"}}

        url = f"{RFAM_BASE_URL}/family/{family_id}/cm"
        response = requests.get(url, timeout=30)

        if response.status_code == 200:
            result = {
                "covariance_model": response.text,
                "family_id": family_id,
                "format": "Infernal CM format",
            }
            return {"status": "success", "data": result}
        else:
            return {
                "status": "error",
                "data": {
                    "error": f"Failed to get covariance model for {family_id}",
                    "detail": response.text[:500],
                },
            }

    def _get_alignment(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get sequence alignment for RNA family."""
        family_id = arguments.get("family_id")
        format_type = arguments.get("format", "stockholm")
        gzip = arguments.get("gzip", False)

        if not family_id:
            return {"status": "error", "data": {"error": "family_id is required"}}

        # Build URL
        if format_type == "stockholm":
            url = f"{RFAM_BASE_URL}/family/{family_id}/alignment"
        else:
            url = f"{RFAM_BASE_URL}/family/{family_id}/alignment/{format_type}"

        if gzip:
            url += "?gzip=1"

        response = requests.get(url, timeout=30)

        if response.status_code == 200:
            result = {
                "alignment": response.text
                if not gzip
                else response.content.decode("utf-8", errors="ignore"),
                "format": format_type,
                "family_id": family_id,
                "compressed": gzip,
            }
            return {"status": "success", "data": result}
        else:
            return {
                "status": "error",
                "data": {
                    "error": f"Failed to get alignment for {family_id}",
                    "detail": response.text[:500],
                },
            }

    def _get_tree_data(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get phylogenetic tree data in NHX format."""
        family_id = arguments.get("family_id")

        if not family_id:
            return {"status": "error", "data": {"error": "family_id is required"}}

        url = f"{RFAM_BASE_URL}/family/{family_id}/tree/"
        response = requests.get(url, timeout=30)

        if response.status_code == 200:
            result = {
                "tree_data": response.text,
                "format": "NHX (New Hampshire eXtended)",
                "family_id": family_id,
            }
            return {"status": "success", "data": result}
        else:
            return {
                "status": "error",
                "data": {
                    "error": f"Failed to get tree data for {family_id}",
                    "detail": response.text[:500],
                },
            }

    def _get_sequence_regions(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get sequence regions for RNA family."""
        family_id = arguments.get("family_id")
        format_type = arguments.get("format", "text")

        if not family_id:
            return {"status": "error", "error": "family_id is required"}

        url = f"{RFAM_BASE_URL}/family/{family_id}/regions"

        headers = {}
        if format_type == "json":
            headers["Accept"] = "application/json"
        elif format_type == "xml":
            headers["Accept"] = "text/xml"

        response = requests.get(url, headers=headers, timeout=30)

        if response.status_code == 200:
            if format_type == "json":
                result = response.json()
                result["family_id"] = family_id
                return {"status": "success", "data": result}
            else:
                result = {
                    "regions": response.text,
                    "format": format_type,
                    "family_id": family_id,
                }
                return {"status": "success", "data": result}
        elif response.status_code == 403:
            return {
                "status": "error",
                "data": {
                    "error": "Too many regions to list for this family",
                    "message": "This family has a very large number of regions. Use API with pagination or download full data.",
                },
            }
        else:
            return {
                "status": "error",
                "data": {
                    "error": f"Failed to get regions for {family_id}",
                    "detail": response.text[:500],
                },
            }

    def _get_structure_mapping(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get mapping between RNA family and PDB structures."""
        family_id = arguments.get("family_id")
        format_type = arguments.get("format", "json")

        if not family_id:
            return {"status": "error", "error": "family_id is required"}

        url = f"{RFAM_BASE_URL}/family/{family_id}/structures"

        headers = {}
        if format_type == "json":
            headers["Accept"] = "application/json"
        elif format_type == "xml":
            headers["Accept"] = "text/xml"

        response = requests.get(url, headers=headers, timeout=30)

        if response.status_code == 200:
            if format_type == "json":
                return {
                    "status": "success",
                    "data": response.json(),
                    "family_id": family_id,
                }
            else:
                return {
                    "status": "success",
                    "structures": response.text,
                    "format": format_type,
                    "family_id": family_id,
                }
        else:
            return {
                "status": "error",
                "error": f"Failed to get structure mapping for {family_id}",
                "detail": response.text[:500],
            }

    def _search_sequence(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search RNA sequence against Rfam families."""
        sequence = arguments.get("sequence")

        if not sequence:
            return {"status": "error", "error": "sequence is required"}

        # Step 1: Submit search
        try:
            files = {"sequence_file": ("sequence.txt", sequence, "text/plain")}
            headers = {"Accept": "application/json"}

            submit_url = f"{RFAM_BATCH_URL}/submit-job"
            submit_response = requests.post(
                submit_url, files=files, headers=headers, timeout=30
            )

            if submit_response.status_code != 200:
                return {
                    "status": "error",
                    "error": f"Failed to submit search: {submit_response.status_code}",
                    "detail": submit_response.text[:500],
                }

            submit_data = submit_response.json()
            job_id = submit_data.get("jobId")
            result_url = submit_data.get("resultURL")

            if not job_id or not result_url:
                return {
                    "status": "error",
                    "error": "Failed to get job ID from server",
                    "response": submit_data,
                }

            # Step 2: Poll for results
            max_wait = arguments.get("max_wait_seconds", 120)
            poll_interval = 5
            elapsed = 0

            while elapsed < max_wait:
                time.sleep(poll_interval)
                elapsed += poll_interval

                result_response = requests.get(result_url, headers=headers, timeout=30)

                if result_response.status_code == 200:
                    # Search complete
                    result = {
                        "job_id": job_id,
                        "results": result_response.json(),
                        "elapsed_seconds": elapsed,
                    }
                    return {"status": "success", "data": result}
                elif result_response.status_code == 202:
                    # Still running
                    continue
                elif result_response.status_code == 410:
                    return {
                        "status": "error",
                        "error": "Job was deleted",
                        "message": "Job may have had a problem. Contact Rfam help desk.",
                    }
                elif result_response.status_code == 503:
                    return {
                        "status": "error",
                        "error": "Job is on hold",
                        "message": "Contact Rfam help desk for assistance.",
                    }
                else:
                    return {
                        "status": "error",
                        "error": f"Unexpected status code: {result_response.status_code}",
                        "detail": result_response.text[:500],
                    }

            # Timeout
            return {
                "status": "pending",
                "message": f"Search is still running after {elapsed} seconds",
                "job_id": job_id,
                "result_url": result_url,
                "instruction": f"Check {result_url} later for results",
            }

        except Exception as e:
            return {"status": "error", "error": f"Search failed: {str(e)}"}
