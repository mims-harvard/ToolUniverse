# interproscan_tool.py
"""
InterProScan API tool for ToolUniverse.

InterProScan is EMBL-EBI's tool for scanning protein sequences against
the InterPro database to identify functional domains, families, and sites.

Unlike the InterPro lookup tools (which query pre-computed annotations),
InterProScan runs actual sequence analysis for novel/uncharacterized proteins.

API Documentation: https://www.ebi.ac.uk/Tools/services/rest/iprscan5/
"""

import requests
import time
from typing import Dict, Any, Optional
from .base_tool import BaseTool
from .tool_registry import register_tool

# Base URL for InterProScan REST API
INTERPROSCAN_BASE_URL = "https://www.ebi.ac.uk/Tools/services/rest/iprscan5"


@register_tool("InterProScanTool")
class InterProScanTool(BaseTool):
    """
    Tool for running InterProScan sequence analysis via EBI REST API.

    Provides protein domain/family prediction by scanning sequences against:
    - Pfam
    - PRINTS
    - ProSite
    - SMART
    - Gene3D
    - TIGRFAM
    - SUPERFAMILY
    - CDD
    - PANTHER

    Job-based API: Submit sequence, poll for results.
    Max 100 sequences per request. Results available for 7 days.
    """

    # Polling configuration
    MAX_POLL_ATTEMPTS = 60  # ~2 minutes with 2s interval
    POLL_INTERVAL = 2  # seconds

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        self.operation = tool_config.get("fields", {}).get("operation", "scan_sequence")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the InterProScan API call."""
        operation = self.operation

        if operation == "scan_sequence":
            return self._scan_sequence(arguments)
        elif operation == "get_job_status":
            return self._get_job_status(arguments)
        elif operation == "get_job_results":
            return self._get_job_results(arguments)
        else:
            return {"status": "error", "error": f"Unknown operation: {operation}"}

    def _scan_sequence(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Submit a protein sequence for InterProScan analysis.

        Submits the job and polls for results (up to 2 minutes).
        For longer jobs, use get_job_status and get_job_results.
        """
        sequence = arguments.get("sequence")
        email = arguments.get("email", "tooluniverse@example.com")
        title = arguments.get("title", "InterProScan job")
        go_terms = arguments.get("go_terms", True)
        pathways = arguments.get("pathways", True)

        if not sequence:
            return {"status": "error", "error": "sequence parameter is required"}

        # Validate sequence (basic check)
        clean_seq = sequence.replace(" ", "").replace("\n", "").upper()
        if not all(c in "ACDEFGHIKLMNPQRSTVWXY*" for c in clean_seq):
            return {
                "status": "error",
                "error": "Invalid protein sequence. Use single-letter amino acid codes.",
            }

        try:
            # Submit job
            submit_url = f"{INTERPROSCAN_BASE_URL}/run"
            data = {
                "email": email,
                "title": title,
                "sequence": clean_seq,
                "goterms": str(go_terms).lower(),
                "pathways": str(pathways).lower(),
            }

            response = requests.post(submit_url, data=data, timeout=self.timeout)

            if response.status_code != 200:
                return {
                    "status": "error",
                    "error": f"Job submission failed: {response.status_code} - {response.text}",
                }

            job_id = response.text.strip()

            # Poll for results
            for attempt in range(self.MAX_POLL_ATTEMPTS):
                status_url = f"{INTERPROSCAN_BASE_URL}/status/{job_id}"
                status_response = requests.get(status_url, timeout=self.timeout)
                status = status_response.text.strip()

                if status == "FINISHED":
                    # Get results
                    return self._fetch_results(job_id)
                elif status == "FAILURE":
                    return {
                        "status": "error",
                        "error": "InterProScan job failed",
                        "job_id": job_id,
                    }
                elif status == "ERROR":
                    return {
                        "status": "error",
                        "error": "InterProScan encountered an error",
                        "job_id": job_id,
                    }
                elif status in ["RUNNING", "PENDING", "QUEUED"]:
                    time.sleep(self.POLL_INTERVAL)
                else:
                    # Unknown status
                    time.sleep(self.POLL_INTERVAL)

            # Timeout - return job_id for later retrieval
            return {
                "status": "success",
                "data": {
                    "job_id": job_id,
                    "status": "RUNNING",
                    "message": "Job is still running. Use get_job_results with this job_id to retrieve results later.",
                },
            }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"InterProScan API timeout after {self.timeout}s",
            }
        except requests.exceptions.RequestException as e:
            return {
                "status": "error",
                "error": f"InterProScan API request failed: {str(e)}",
            }
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    def _fetch_results(self, job_id: str) -> Dict[str, Any]:
        """Fetch and parse InterProScan results."""
        try:
            # Get JSON results
            results_url = f"{INTERPROSCAN_BASE_URL}/result/{job_id}/json"
            response = requests.get(results_url, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()

            # Parse results
            results = data.get("results", [])
            domains = []
            go_annotations = []
            pathways = []

            for result in results:
                matches = result.get("matches", [])
                for match in matches:
                    signature = match.get("signature", {})
                    entry = signature.get("entry", {})

                    domain_info = {
                        "accession": signature.get("accession"),
                        "name": signature.get("name"),
                        "description": signature.get("description"),
                        "database": signature.get("signatureLibraryRelease", {}).get(
                            "library"
                        ),
                        "interpro_accession": entry.get("accession") if entry else None,
                        "interpro_name": entry.get("name") if entry else None,
                        "interpro_type": entry.get("type") if entry else None,
                        "locations": [],
                    }

                    # Parse match locations
                    for location in match.get("locations", []):
                        domain_info["locations"].append(
                            {
                                "start": location.get("start"),
                                "end": location.get("end"),
                                "score": location.get("score"),
                                "evalue": location.get("evalue"),
                            }
                        )

                    domains.append(domain_info)

                    # Extract GO terms if present
                    if entry:
                        for go_term in entry.get("goXRefs", []):
                            go_annotations.append(
                                {
                                    "id": go_term.get("id"),
                                    "name": go_term.get("name"),
                                    "category": go_term.get("category"),
                                }
                            )

                        # Extract pathway info
                        for pathway in entry.get("pathwayXRefs", []):
                            pathways.append(
                                {
                                    "database": pathway.get("databaseName"),
                                    "id": pathway.get("id"),
                                    "name": pathway.get("name"),
                                }
                            )

            return {
                "status": "success",
                "data": {
                    "job_id": job_id,
                    "domains": domains,
                    "domain_count": len(domains),
                    "go_annotations": list(
                        {go["id"]: go for go in go_annotations}.values()
                    ),  # Dedupe
                    "pathways": list({p["id"]: p for p in pathways}.values()),  # Dedupe
                    "sequence_length": results[0].get("sequenceLength")
                    if results
                    else None,
                },
            }
        except Exception as e:
            return {"status": "error", "error": f"Failed to fetch results: {str(e)}"}

    def _get_job_status(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check the status of an InterProScan job.

        Status values: RUNNING, FINISHED, FAILURE, ERROR, NOT_FOUND
        """
        job_id = arguments.get("job_id")

        if not job_id:
            return {"status": "error", "error": "job_id parameter is required"}

        try:
            status_url = f"{INTERPROSCAN_BASE_URL}/status/{job_id}"
            response = requests.get(status_url, timeout=self.timeout)
            job_status = response.text.strip()

            return {
                "status": "success",
                "data": {
                    "job_id": job_id,
                    "job_status": job_status,
                    "is_finished": job_status == "FINISHED",
                    "has_error": job_status in ["FAILURE", "ERROR", "NOT_FOUND"],
                },
            }
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Failed to get job status: {str(e)}"}

    def _get_job_results(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get results for a completed InterProScan job.

        Job results are available for 7 days after completion.
        """
        job_id = arguments.get("job_id")

        if not job_id:
            return {"status": "error", "error": "job_id parameter is required"}

        try:
            # Check status first
            status_url = f"{INTERPROSCAN_BASE_URL}/status/{job_id}"
            response = requests.get(status_url, timeout=self.timeout)
            job_status = response.text.strip()

            if job_status != "FINISHED":
                return {
                    "status": "success",
                    "data": {
                        "job_id": job_id,
                        "job_status": job_status,
                        "message": f"Job is not finished yet. Status: {job_status}",
                    },
                }

            return self._fetch_results(job_id)
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Failed to get job results: {str(e)}"}
