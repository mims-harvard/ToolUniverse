"""ProteinsPlus API tool using AsyncPollingTool base class.

Converted to use AsyncPollingTool for cleaner code and automatic polling management.
Maintains all original functionality while reducing boilerplate.
"""

import asyncio
import requests
import time
from urllib.parse import urlparse
from typing import Any, Dict, Optional, TYPE_CHECKING
from .async_base import AsyncPollingTool
from .tool_registry import register_tool

if TYPE_CHECKING:
    from .task_progress import TaskProgress

PROTEINSPLUS_BASE_URL = "https://proteins.plus/api"

_JSON_HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "User-Agent": "ToolUniverse/ProteinsPlus",
}

_STATUS_HEADERS = {
    "Accept": "application/json",
    "User-Agent": "ToolUniverse/ProteinsPlus",
}


@register_tool("ProteinsPlusRESTTool")
class ProteinsPlusRESTTool(AsyncPollingTool):
    """ProteinsPlus API tool for protein-ligand docking and binding site analysis.

    Now uses AsyncPollingTool base class for automatic polling, progress reporting,
    and timeout management. Original functionality preserved.
    """

    # Configuration parameters for ProteinsPlus endpoints
    _SIENA_OPTIONAL_KEYS = {
        "fragment_length": "fragment_length",
        "flexibility_sensitivity": "flexibility_sensitivity",
        "site_radius": "siteRadius",
        "minimal_site_identity": "minimalSiteIdentity",
        "minimal_site_coverage": "minimalSiteCoverage",
        "maximum_mutations": "maximum_mutations",
    }

    def __init__(self, tool_config):
        """Initialize ProteinsPlus tool with configuration."""
        # Extract config before calling super().__init__()
        fields = tool_config.get("fields", {})
        parameter = tool_config.get("parameter", {})

        # Set AsyncPollingTool attributes
        self.name = tool_config.get("name", "ProteinsPlus_Tool")
        self.description = tool_config.get("description", "ProteinsPlus API tool")
        self.parameter = parameter
        self.poll_interval = fields.get("poll_interval", 15)
        self.max_duration = fields.get("max_wait_time", 1800)

        # Initialize AsyncPollingTool (generates return_schema)
        super().__init__()

        # ProteinsPlus-specific config
        self.endpoint = fields.get("endpoint", "")
        self.method = fields.get("method", "POST").upper()
        self.required = parameter.get("required", [])
        self.is_async = fields.get("is_async", False)

        # Store full config for compatibility
        self._tool_config = tool_config

    def _transform_params(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Transform user-facing arguments into the nested format ProteinsPlus expects."""
        endpoint = self.endpoint

        if endpoint == "/dogsite_rest":
            if "pdb_content" in arguments:
                return {"pdb_content": arguments["pdb_content"]}
            return {
                "dogsite": {
                    "pdbCode": arguments.get("pdb_id", ""),
                    "analysisDetail": "1",
                    "bindingSitePredictionGranularity": "1",
                    "ligand": "",
                    "chain": arguments.get("chain", ""),
                }
            }

        if endpoint == "/dogsite3_rest":
            return {
                "dogsite3": {
                    "pdbCode": arguments.get("pdb_id", ""),
                    "analysisDetail": arguments.get("analysis_detail", "1"),
                    "bindingSitePredictionGranularity": arguments.get(
                        "druggability", "1"
                    ),
                    "ligand": arguments.get("ligand", ""),
                    "chain": arguments.get("chain", ""),
                    "ligandBias": "1" if arguments.get("ligand_bias", False) else "0",
                }
            }

        if endpoint == "/protoss_rest":
            # Custom structures must first be uploaded to /pdb_files_rest.
            # ProtoSS accepts only pdbCode, including a returned upload ID.
            return {"protoss": {"pdbCode": arguments.get("pdb_id", "")}}

        if endpoint == "/poseview_rest":
            return {
                "poseview": {
                    "pdbCode": arguments.get("pdb_id", ""),
                    "ligand": arguments.get("ligand", ""),
                }
            }

        if endpoint == "/siena_rest":
            siena_params = {
                "pdbCode": arguments.get("pdb_id", ""),
                "mode": arguments.get("mode", "screening"),
                "ligand": arguments.get("ligand", ""),
                "pocket": arguments.get("pocket", ""),
            }
            for arg_key, api_key in self._SIENA_OPTIONAL_KEYS.items():
                if arg_key in arguments:
                    siena_params[api_key] = arguments[arg_key]
            return {"siena": siena_params}

        if endpoint == "/structurechecker_rest":
            return {
                "structurechecker": {
                    "pdbCode": arguments.get("pdb_id", ""),
                    "setting": arguments.get("setting", "combined"),
                }
            }

        return {k: v for k, v in arguments.items() if v is not None}

    # ========================================================================
    # Shared helpers
    # ========================================================================

    def _build_api_url(self, arguments: Dict[str, Any]) -> str:
        """Build API URL by substituting argument placeholders in the endpoint."""
        url = PROTEINSPLUS_BASE_URL + self.endpoint
        for key, value in arguments.items():
            placeholder = f"{{{key}}}"
            if placeholder in url:
                url = url.replace(placeholder, str(value))
        return url

    def _validate_required(self, arguments: Dict[str, Any]) -> None:
        """Raise ValueError if any required parameters are missing."""
        missing = [k for k in self.required if k not in arguments]
        if missing:
            raise ValueError(f"Missing required parameter(s): {', '.join(missing)}")

    def _prepare_protoss(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        sources = [
            key for key in ("pdb_id", "pdb_content") if arguments.get(key) is not None
        ]
        if len(sources) != 1:
            raise ValueError("Provide exactly one of pdb_id or pdb_content")
        source = sources[0]
        value = arguments[source]
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{source} must be a nonempty string")
        if arguments.get("ligand_content"):
            raise ValueError(
                "Separate ligand_content is unsupported by ProtoSS REST; include ligands in the PDB"
            )
        if source == "pdb_id":
            return arguments
        if len(value.encode("utf-8")) > 5 * 1024 * 1024:
            raise ValueError("pdb_content exceeds the 5 MiB upload limit")
        if not any(
            line.startswith(("ATOM  ", "HETATM")) for line in value.splitlines()
        ):
            raise ValueError("pdb_content must contain PDB ATOM or HETATM records")
        upload_id = self._upload_pdb(value)
        # Work on a copy; never overwrite the caller's structure or cache an ID
        # on this shared tool instance across calls.
        return {"pdb_id": upload_id}

    def _upload_pdb(self, content: str) -> str:
        """Use the documented multipart upload and wait for its loaded ID."""
        duration = min(120, self.max_duration)
        deadline = time.monotonic() + duration
        response = requests.post(
            PROTEINSPLUS_BASE_URL + "/pdb_files_rest",
            files={
                "pdb_file[pathvar]": (
                    "input.pdb",
                    content.encode("utf-8"),
                    "chemical/x-pdb",
                )
            },
            headers=_STATUS_HEADERS,
            timeout=min(60.0, duration),
        )
        if response.status_code not in (200, 202):
            raise RuntimeError(f"PDB upload returned HTTP {response.status_code}")
        data = response.json()
        if response.status_code == 200:
            upload_id = data.get("id")
            if not isinstance(upload_id, str) or not upload_id:
                raise RuntimeError("Loaded PDB upload response has no id")
            return upload_id
        location = data.get("location")
        if not isinstance(location, str):
            raise RuntimeError("PDB upload response has no polling location")
        parsed = urlparse(location)
        if (
            parsed.scheme != "https"
            or parsed.netloc != "proteins.plus"
            or not parsed.path.startswith("/api/pdb_files_rest/")
        ):
            raise RuntimeError("Unexpected PDB upload polling location")
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(
                    f"PDB upload did not finish within {duration} seconds"
                )
            response = requests.get(
                location, headers=_STATUS_HEADERS, timeout=min(30.0, remaining)
            )
            if response.status_code == 200:
                data = response.json()
                upload_id = data.get("id")
                if not isinstance(upload_id, str) or not upload_id:
                    raise RuntimeError("Loaded PDB upload response has no id")
                return upload_id
            if response.status_code != 202:
                raise RuntimeError(
                    f"PDB upload status returned HTTP {response.status_code}"
                )
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(
                    f"PDB upload did not finish within {duration} seconds"
                )
            time.sleep(min(2, remaining))

    # ========================================================================
    # AsyncPollingTool Required Methods
    # ========================================================================

    def submit_job(self, arguments: Dict[str, Any]) -> str:
        """Submit job to ProteinsPlus API and return job location URL.

        This method handles job submission for async tools. For sync tools,
        it's not called (handled by run() override).
        """
        self._validate_required(arguments)
        if self.endpoint == "/protoss_rest":
            arguments = self._prepare_protoss(arguments)
        url = self._build_api_url(arguments)
        request_data = self._transform_params(arguments)

        response = requests.post(
            url,
            json=request_data,
            headers=_JSON_HEADERS,
            timeout=60.0,
        )

        if response.status_code == 404:
            raise RuntimeError(f"Endpoint not found: {url}")
        if response.status_code == 400:
            raise RuntimeError(f"Bad request: {response.text}")
        if response.status_code not in (200, 201, 202):
            raise RuntimeError(f"API returned {response.status_code}: {response.text}")

        # Parse response
        try:
            job_data = response.json()
        except Exception as e:
            raise RuntimeError(f"Failed to parse response: {e}")

        # Extract job location URL
        status_url = job_data.get("location")
        if not status_url:
            # Try extracting job_id
            job_id = job_data.get("job_id") or job_data.get("id")
            if job_id:
                status_url = f"{PROTEINSPLUS_BASE_URL}/jobs/{job_id}/status"
            else:
                # Check if job completed immediately
                if job_data.get("status") in ("completed", "success"):
                    # Store for retrieval in check_status
                    self._immediate_result = job_data.get("results", job_data)
                    return "COMPLETED_IMMEDIATELY"
                raise RuntimeError("No job location or ID in response")

        return status_url

    def check_status(self, job_id: str) -> Dict[str, Any]:
        """Check ProteinsPlus job status and return result if complete.

        Args:
            job_id: Job location URL from submit_job()

        Returns:
            Dict with keys:
                - done (bool): True if complete
                - result (any): Results if done
                - progress (int): Progress percentage (0-100)
                - error (str): Error message if failed
        """
        # Handle immediate completion case
        if job_id == "COMPLETED_IMMEDIATELY":
            result = getattr(self, "_immediate_result", {})
            return {"done": True, "result": result, "progress": 100}

        # Check status via HTTP
        try:
            response = requests.get(
                job_id,
                headers=_STATUS_HEADERS,
                timeout=30.0,
            )
        except Exception as e:
            return {"done": False, "error": f"Status check failed: {e}"}

        # Handle HTTP 202 (still processing)
        if response.status_code == 202:
            return {"done": False, "progress": 30}

        # Handle HTTP errors
        if response.status_code not in (200, 201):
            return {
                "done": False,
                "error": f"Status check returned {response.status_code}: {response.text}",
            }

        # Parse response
        try:
            status_data = response.json()
        except Exception as e:
            return {"done": False, "error": f"Failed to parse status: {e}"}

        # Check internal status_code field (ProteinsPlus-specific)
        if status_data.get("status_code") == 202:
            return {"done": False, "progress": 60}

        # Check status field
        status = status_data.get("status", "").lower()
        if status in ("failed", "error"):
            error_msg = status_data.get("error", "Job failed")
            return {"done": False, "error": error_msg}

        # Job complete - extract results
        results = status_data.get("results", status_data)
        return {"done": True, "result": results, "progress": 100}

    def format_result(self, result: Any) -> Dict[str, Any]:
        """Format ProteinsPlus results into standard response format."""
        return {
            "status": "success",
            "data": result,
            "metadata": {
                "source": "ProteinsPlus",
                "endpoint": self.endpoint,
                "execution_type": "async",
            },
        }

    # ========================================================================
    # Override run() for sync/async branching
    # ========================================================================

    async def run(
        self, arguments: Dict[str, Any], progress: Optional["TaskProgress"] = None
    ) -> Dict[str, Any]:
        """Execute the tool with provided arguments.

        Overrides AsyncPollingTool.run() to support both sync and async tools.
        """
        if progress:
            await progress.set_message("Starting ProteinsPlus job")

        # For async tools, use AsyncPollingTool's run()
        if self.is_async:
            if self.endpoint == "/protoss_rest":
                try:
                    # Upload polling can take up to two minutes; keep that
                    # synchronous HTTP work off the caller's event loop.
                    arguments = await asyncio.to_thread(
                        self._prepare_protoss, arguments
                    )
                except Exception as exc:
                    return self.handle_error(exc)
            return await super().run(arguments, progress)

        # For sync tools, execute directly
        return await self._run_sync_request(arguments, progress)

    async def _run_sync_request(
        self, arguments: Dict[str, Any], progress: Optional["TaskProgress"]
    ) -> Dict[str, Any]:
        """Execute a synchronous (non-polling) request."""
        if progress:
            await progress.set_message("Executing synchronous request")

        missing = [k for k in self.required if k not in arguments]
        if missing:
            return {
                "status": "error",
                "error": f"Missing required parameter(s): {', '.join(missing)}",
                "query": arguments,
            }

        url = self._build_api_url(arguments)
        request_data = self._transform_params(arguments)

        try:
            if self.method == "POST":
                response = requests.post(
                    url,
                    json=request_data,
                    headers=_JSON_HEADERS,
                    timeout=60.0,
                )
            else:
                response = requests.get(
                    url,
                    params=request_data,
                    headers=_STATUS_HEADERS,
                    timeout=60.0,
                )

            if response.status_code == 404:
                return {
                    "status": "error",
                    "error": "Endpoint not found",
                    "detail": response.text,
                    "query": arguments,
                }
            if response.status_code == 400:
                return {
                    "status": "error",
                    "error": "Bad request",
                    "detail": response.text,
                    "query": arguments,
                }
            if response.status_code not in (200, 201):
                return {
                    "status": "error",
                    "error": f"API returned {response.status_code}",
                    "detail": response.text,
                    "query": arguments,
                }

            data = response.json()
            return {
                "status": "success",
                "data": data,
                "metadata": {
                    "source": "ProteinsPlus",
                    "endpoint": self.endpoint,
                    "query": arguments,
                    "execution_type": "sync",
                },
            }

        except requests.Timeout:
            return {
                "status": "error",
                "error": "Request timeout",
                "detail": "Request timed out after 60 seconds",
            }
        except Exception as e:
            return {"status": "error", "error": "Request failed", "detail": str(e)}
