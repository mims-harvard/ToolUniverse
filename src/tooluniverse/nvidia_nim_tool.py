"""
NVIDIA NIM Healthcare API Tool.

This module provides a unified interface to NVIDIA's cloud-hosted healthcare AI APIs,
including protein structure prediction, molecular docking, protein design, genomics,
and medical imaging tools.

All APIs require a NVIDIA API key set as the NVIDIA_API_KEY environment variable.
Get your key at: https://build.nvidia.com

Rate limit: 40 requests per minute (enforced internally).
"""

import os
import time
import requests
from typing import Dict, Any, Optional, List
from .base_tool import BaseTool
from .tool_registry import register_tool


# Rate limiting configuration
_last_request_time = 0.0
_MIN_REQUEST_INTERVAL = 1.5  # 40 RPM = 1.5 seconds between requests


def _enforce_rate_limit():
    """Enforce rate limiting (40 RPM = 1.5s between requests)."""
    global _last_request_time
    current_time = time.time()
    elapsed = current_time - _last_request_time
    if elapsed < _MIN_REQUEST_INTERVAL:
        time.sleep(_MIN_REQUEST_INTERVAL - elapsed)
    _last_request_time = time.time()


@register_tool("NvidiaNIMTool")
class NvidiaNIMTool(BaseTool):
    """
    NVIDIA NIM Healthcare API tool.

    Provides unified access to 16 NVIDIA cloud-hosted healthcare AI APIs:

    Structure Prediction:
    - AlphaFold2, AlphaFold2-Multimer, ESMFold, OpenFold2, OpenFold3, Boltz2

    Protein Design:
    - ProteinMPNN, RFdiffusion

    Molecular Tools:
    - DiffDock, GenMol, MolMIM

    Genomics:
    - Evo2-40B, MSA-Search, ESM2-650M

    Medical Imaging:
    - MAISI, Vista3D

    Configuration fields:
    - endpoint: API endpoint path (relative to base URL)
    - base_url: Override base URL (default: https://health.api.nvidia.com/v1/biology)
    - async_expected: Whether 202 async response is expected
    - poll_seconds: NVCF-POLL-SECONDS header value (default 300)
    - response_type: Expected response type (json, pdb, mfasta, zip)
    - timeout: Request timeout in seconds (default 600)
    """

    DEFAULT_BASE_URL = "https://health.api.nvidia.com/v1/biology"
    STATUS_URL = "https://integrate.api.nvidia.com/v1/status"
    ASSETS_URL = "https://api.nvcf.nvidia.com/v2/nvcf/assets"
    DEFAULT_TIMEOUT = 600
    DEFAULT_POLL_SECONDS = 300
    MAX_POLL_ATTEMPTS = 120  # 10 minutes with 5s intervals
    POLL_INTERVAL = 5

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        fields = tool_config.get("fields", {})

        self.endpoint = fields.get("endpoint", "")
        self.base_url = fields.get("base_url", self.DEFAULT_BASE_URL)
        self.async_expected = fields.get("async_expected", False)
        self.poll_seconds = fields.get("poll_seconds", self.DEFAULT_POLL_SECONDS)
        self.response_type = fields.get("response_type", "json")
        self.timeout = fields.get("timeout", self.DEFAULT_TIMEOUT)

        # Get API key from environment
        self.api_key = os.environ.get("NVIDIA_API_KEY")

    def _get_headers(self) -> Dict[str, str]:
        """Build request headers with authentication."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        # Add NVCF-POLL-SECONDS for async operations
        if self.async_expected:
            headers["NVCF-POLL-SECONDS"] = str(self.poll_seconds)

        return headers

    def _build_url(self) -> str:
        """Build the full API URL."""
        # Handle endpoints that include full path
        if self.endpoint.startswith("http"):
            return self.endpoint

        # Ensure proper URL construction
        base = self.base_url.rstrip("/")
        endpoint = self.endpoint.lstrip("/")
        return f"{base}/{endpoint}"

    def _poll_for_result(self, req_id: str, headers: Dict[str, str]) -> Dict[str, Any]:
        """
        Poll the status endpoint for async operation results.

        Args:
            req_id: The nvcf-reqid from the 202 response
            headers: Request headers including auth

        Returns:
            Final response from the API
        """
        poll_url = f"{self.STATUS_URL}/{req_id}"

        for attempt in range(self.MAX_POLL_ATTEMPTS):
            try:
                _enforce_rate_limit()
                response = requests.get(poll_url, headers=headers, timeout=self.timeout)

                if response.status_code != 202:
                    # Operation complete
                    return self._parse_response(response)

                # Still processing, wait and retry
                time.sleep(self.POLL_INTERVAL)

            except requests.exceptions.RequestException as e:
                return {
                    "status": "error",
                    "error": "Poll request failed",
                    "detail": str(e),
                    "request_id": req_id,
                }

        return {
            "status": "error",
            "error": "Polling timeout",
            "detail": f"Operation did not complete within {self.MAX_POLL_ATTEMPTS * self.POLL_INTERVAL} seconds",
            "request_id": req_id,
        }

    def _parse_response(self, response: requests.Response) -> Dict[str, Any]:
        """Parse API response based on response type and status."""
        if response.status_code == 401:
            return {
                "status": "error",
                "error": "Authentication failed",
                "detail": "Invalid or missing NVIDIA_API_KEY. Get your key at https://build.nvidia.com",
                "status_code": 401,
            }

        if response.status_code == 429:
            return {
                "status": "error",
                "error": "Rate limit exceeded",
                "detail": "NVIDIA NIM API rate limit (40 RPM) exceeded. Please wait and retry.",
                "status_code": 429,
            }

        if response.status_code == 404:
            return {
                "status": "error",
                "error": "Endpoint not found",
                "detail": response.text,
                "status_code": 404,
            }

        if response.status_code >= 500:
            return {
                "status": "error",
                "error": "Server error",
                "detail": response.text,
                "status_code": response.status_code,
            }

        if response.status_code not in [200, 201]:
            return {
                "status": "error",
                "error": f"API returned status {response.status_code}",
                "detail": response.text[:1000] if response.text else "No details",
                "status_code": response.status_code,
            }

        # Handle different response types
        content_type = response.headers.get("Content-Type", "")

        if "application/zip" in content_type:
            # Return binary content info for ZIP files (medical imaging)
            return {
                "status": "success",
                "content_type": "application/zip",
                "content_length": len(response.content),
                "data": f"<ZIP file, {len(response.content)} bytes>",
                "note": "Use response.content to access the raw ZIP data",
                "_raw_content": response.content,
            }

        if "application/octet-stream" in content_type or self.response_type == "binary":
            # Return binary content info (e.g., npz files for embeddings)
            return {
                "status": "success",
                "content_type": content_type or "application/octet-stream",
                "content_length": len(response.content),
                "data": f"<Binary data, {len(response.content)} bytes>",
                "note": "Use _raw_content to access the raw binary data",
                "_raw_content": response.content,
            }

        if self.response_type == "pdb" or "text/plain" in content_type:
            # PDB structure text
            return {
                "status": "success",
                "structure": response.text,
                "format": "pdb",
            }

        if self.response_type == "mfasta":
            # Multi-FASTA format
            try:
                data = response.json()
                return {
                    "status": "success",
                    "data": data,
                    "format": "mfasta",
                }
            except ValueError:
                return {
                    "status": "success",
                    "sequences": response.text,
                    "format": "mfasta",
                }

        # Default: JSON response
        try:
            data = response.json()
            return {
                "status": "success",
                "data": data,
            }
        except ValueError as e:
            return {
                "status": "error",
                "error": "Failed to parse JSON response",
                "detail": str(e),
                "raw_response": response.text[:500] if response.text else None,
            }

    def _validate_api_key(self) -> Optional[Dict[str, Any]]:
        """Validate API key is present."""
        if not self.api_key:
            return {
                "status": "error",
                "error": "Missing API key",
                "detail": (
                    "NVIDIA_API_KEY environment variable not set. "
                    "Get your API key at https://build.nvidia.com and set it:\n"
                    "export NVIDIA_API_KEY=nvapi-..."
                ),
            }
        return None

    def _upload_asset(
        self, content: str, description: str = "diffdock-file"
    ) -> Dict[str, Any]:
        """
        Upload a file to NVIDIA's asset storage for tools that require staged inputs (e.g., DiffDock).

        This implements the NVCF asset upload pattern:
        1. POST to assets API to get an upload URL and asset ID
        2. PUT the file content to the upload URL
        3. Return the asset ID to be used in the main API request

        Args:
            content: File content to upload (string)
            description: Description for the asset

        Returns:
            Dictionary with 'asset_id' on success, or error details on failure
        """
        if not self.api_key:
            return {
                "status": "error",
                "error": "Missing API key",
                "detail": "NVIDIA_API_KEY required for asset upload",
            }

        # Step 1: Request upload URL
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        payload = {
            "contentType": "text/plain",
            "description": description,
        }

        try:
            _enforce_rate_limit()
            response = requests.post(
                self.ASSETS_URL, headers=headers, json=payload, timeout=30
            )
            response.raise_for_status()

            result = response.json()
            upload_url = result.get("uploadUrl")
            asset_id = result.get("assetId")

            if not upload_url or not asset_id:
                return {
                    "status": "error",
                    "error": "Failed to get upload URL",
                    "detail": f"Response: {result}",
                }

            # Step 2: Upload content to S3
            s3_headers = {
                "x-amz-meta-nvcf-asset-description": description,
                "Content-Type": "text/plain",
            }

            _enforce_rate_limit()
            upload_response = requests.put(
                upload_url, data=content, headers=s3_headers, timeout=300
            )
            upload_response.raise_for_status()

            return {
                "status": "success",
                "asset_id": asset_id,
            }

        except requests.exceptions.RequestException as e:
            return {
                "status": "error",
                "error": "Asset upload failed",
                "detail": str(e),
            }

    def _handle_diffdock_staged(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle DiffDock's staged asset upload workflow.

        When is_staged=True, protein and ligand should be raw content that needs
        to be uploaded as assets. The asset IDs are then used in the actual request.

        Args:
            arguments: Original arguments with protein and ligand content

        Returns:
            Modified arguments with asset IDs, or error dict on failure
        """
        protein_content = arguments.get("protein", "")
        ligand_content = arguments.get("ligand", "")

        # Upload protein
        protein_result = self._upload_asset(protein_content, "protein-pdb")
        if protein_result.get("status") == "error":
            return protein_result
        protein_asset_id = protein_result["asset_id"]

        # Upload ligand
        ligand_result = self._upload_asset(ligand_content, "ligand-sdf")
        if ligand_result.get("status") == "error":
            return ligand_result
        ligand_asset_id = ligand_result["asset_id"]

        # Return asset IDs and update arguments
        return {
            "status": "success",
            "protein_asset_id": protein_asset_id,
            "ligand_asset_id": ligand_asset_id,
            "asset_references": f"{protein_asset_id},{ligand_asset_id}",
        }

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the NVIDIA NIM API call.

        Args:
            arguments: Dictionary of API-specific parameters

        Returns:
            Dictionary containing:
            - status: "success" or error information
            - data: API response data
            - Additional fields based on response type
        """
        # Validate API key
        key_error = self._validate_api_key()
        if key_error:
            return key_error

        # Validate required parameters
        missing = [
            k
            for k in self.get_required_parameters()
            if k not in arguments or arguments[k] is None
        ]
        if missing:
            return {
                "status": "error",
                "error": "Missing required parameters",
                "detail": f"Required: {', '.join(missing)}",
                "provided": list(arguments.keys()),
            }

        # Build URL and headers
        url = self._build_url()
        headers = self._get_headers()

        # Handle DiffDock staged asset upload workflow
        asset_references = None
        request_arguments = arguments.copy()

        is_diffdock = "diffdock" in self.endpoint.lower()
        is_staged = arguments.get("is_staged", False)

        if is_diffdock and is_staged:
            # Upload assets and get asset IDs
            staged_result = self._handle_diffdock_staged(arguments)
            if staged_result.get("status") == "error":
                return staged_result

            # Update arguments with asset IDs
            request_arguments["protein"] = staged_result["protein_asset_id"]
            request_arguments["ligand"] = staged_result["ligand_asset_id"]
            request_arguments["is_staged"] = True
            asset_references = staged_result["asset_references"]

            # Add asset references header
            headers["NVCF-INPUT-ASSET-REFERENCES"] = asset_references

        # Enforce rate limiting
        _enforce_rate_limit()

        try:
            # Make the API request
            response = requests.post(
                url, headers=headers, json=request_arguments, timeout=self.timeout
            )

            # Handle async response (202 Accepted)
            if response.status_code == 202:
                req_id = response.headers.get("nvcf-reqid")
                if not req_id:
                    return {
                        "status": "error",
                        "error": "Async operation started but no request ID returned",
                        "detail": "Missing nvcf-reqid header",
                    }

                # For DiffDock with staged assets, ensure headers are preserved for polling
                if asset_references:
                    headers["NVCF-INPUT-ASSET-REFERENCES"] = asset_references

                # Poll for result
                return self._poll_for_result(req_id, headers)

            # Handle synchronous response
            return self._parse_response(response)

        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": "Request timeout",
                "detail": f"Request timed out after {self.timeout} seconds",
            }
        except requests.exceptions.ConnectionError as e:
            return {
                "status": "error",
                "error": "Connection error",
                "detail": str(e),
            }
        except requests.exceptions.RequestException as e:
            return {
                "status": "error",
                "error": "Request failed",
                "detail": str(e),
            }
