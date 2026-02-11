"""ProteinsPlus API tool using AsyncPollingTool base class.

Converted to use AsyncPollingTool for cleaner code and automatic polling management.
Maintains all original functionality while reducing boilerplate.
"""
import asyncio
import requests
from typing import Any, Dict, Optional, TYPE_CHECKING
from .async_base import AsyncPollingTool
from .tool_registry import register_tool

if TYPE_CHECKING:
    from .task_progress import TaskProgress

PROTEINSPLUS_BASE_URL = "https://proteins.plus/api"


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
                    "bindingSitePredictionGranularity": arguments.get("druggability", "1"),
                    "ligand": arguments.get("ligand", ""),
                    "chain": arguments.get("chain", ""),
                    "ligandBias": "1" if arguments.get("ligand_bias", False) else "0",
                }
            }

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
    # AsyncPollingTool Required Methods
    # ========================================================================

    def submit_job(self, arguments: Dict[str, Any]) -> str:
        """Submit job to ProteinsPlus API and return job location URL.

        This method handles job submission for async tools. For sync tools,
        it's not called (handled by run() override).
        """
        # Validate required parameters
        missing = [k for k in self.required if k not in arguments]
        if missing:
            raise ValueError(f"Missing required parameter(s): {', '.join(missing)}")

        # Build URL
        url = PROTEINSPLUS_BASE_URL + self.endpoint
        for key, value in arguments.items():
            placeholder = f"{{{key}}}"
            if placeholder in url:
                url = url.replace(placeholder, str(value))

        # Transform parameters
        request_data = self._transform_params(arguments)

        # Submit job (synchronous HTTP call)
        response = requests.post(
            url,
            json=request_data,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "ToolUniverse/ProteinsPlus",
            },
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
                headers={
                    "Accept": "application/json",
                    "User-Agent": "ToolUniverse/ProteinsPlus",
                },
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
            return await super().run(arguments, progress)

        # For sync tools, execute directly
        return await self._run_sync_request(arguments, progress)

    async def _run_sync_request(
        self, arguments: Dict[str, Any], progress: Optional["TaskProgress"]
    ) -> Dict[str, Any]:
        """Execute a synchronous (non-polling) request."""
        if progress:
            await progress.set_message("Executing synchronous request")

        # Validate parameters
        missing = [k for k in self.required if k not in arguments]
        if missing:
            return {
                "error": f"Missing required parameter(s): {', '.join(missing)}",
                "query": arguments,
            }

        # Build URL
        url = PROTEINSPLUS_BASE_URL + self.endpoint
        for key, value in arguments.items():
            placeholder = f"{{{key}}}"
            if placeholder in url:
                url = url.replace(placeholder, str(value))

        # Transform parameters
        request_data = self._transform_params(arguments)

        # Execute request (sync)
        try:
            if self.method == "POST":
                response = requests.post(
                    url,
                    json=request_data,
                    headers={
                        "Accept": "application/json",
                        "Content-Type": "application/json",
                        "User-Agent": "ToolUniverse/ProteinsPlus",
                    },
                    timeout=60.0,
                )
            else:
                response = requests.get(
                    url,
                    params=request_data,
                    headers={
                        "Accept": "application/json",
                        "User-Agent": "ToolUniverse/ProteinsPlus",
                    },
                    timeout=60.0,
                )

            if response.status_code == 404:
                return {"error": "Endpoint not found", "detail": response.text, "query": arguments}
            if response.status_code == 400:
                return {"error": "Bad request", "detail": response.text, "query": arguments}
            if response.status_code not in (200, 201):
                return {
                    "error": f"API returned {response.status_code}",
                    "detail": response.text,
                    "query": arguments,
                }

            data = response.json()
            return {
                "data": data,
                "metadata": {
                    "source": "ProteinsPlus",
                    "endpoint": self.endpoint,
                    "query": arguments,
                    "execution_type": "sync",
                },
            }

        except requests.Timeout:
            return {"error": "Request timeout", "detail": "Request timed out after 60 seconds"}
        except Exception as e:
            return {"error": "Request failed", "detail": str(e)}
