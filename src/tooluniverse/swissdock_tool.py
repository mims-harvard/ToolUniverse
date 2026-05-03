"""SwissDock Tool - Molecular docking using AsyncPollingTool base class.

Converted to use AsyncPollingTool for cleaner code and automatic polling management.
API Documentation: https://www.swissdock.ch/command-line.php
"""

import uuid
from urllib.parse import urlencode
import requests
from typing import Any, Dict, Optional, TYPE_CHECKING
from .async_base import AsyncPollingTool
from .tool_registry import register_tool

if TYPE_CHECKING:
    from .task_progress import TaskProgress

SWISSDOCK_BASE_URL = "https://swissdock.ch:8443"


@register_tool("SwissDockTool")
class SwissDockTool(AsyncPollingTool):
    """
    Tool for molecular docking using SwissDock REST API with AsyncPollingTool base class.

    SwissDock performs protein-ligand docking using:
    - Attracting Cavities 2.0 (default) - cavity-based docking
    - AutoDock Vina - blind or targeted docking

    Now uses AsyncPollingTool for automatic polling, progress reporting, and timeout management.
    """

    # Default configuration
    poll_interval = 5  # seconds
    max_duration = 600  # 10 minutes

    def __init__(self, tool_config: Dict[str, Any]):
        """Initialize SwissDock tool with configuration."""
        # Extract config
        self.name = tool_config.get("name", "SwissDock_Tool")
        self.description = tool_config.get("description", "SwissDock molecular docking")
        self.parameter = tool_config.get("parameter", {})

        # Initialize AsyncPollingTool
        super().__init__()

        # SwissDock-specific config
        self.timeout = tool_config.get("timeout", 60)
        self.operation = tool_config.get("fields", {}).get("operation", "dock_ligand")
        self._tool_config = tool_config

    # ========================================================================
    # Helper Methods (API-specific logic)
    # ========================================================================

    def _check_server_status(self) -> bool:
        """Check if SwissDock server is operational (synchronous)."""
        try:
            response = requests.get(f"{SWISSDOCK_BASE_URL}/", timeout=10.0)
            return response.status_code == 200 and "Hello World!" in response.text
        except Exception:
            return False

    def _generate_session_id(self) -> str:
        """Generate a unique session ID for the docking job."""
        return str(uuid.uuid4())

    def _prepare_ligand(self, session_id: str, ligand_smiles: str):
        """Prepare ligand from SMILES (raises on error)."""
        url = f"{SWISSDOCK_BASE_URL}/preplig"
        params = {"mySMILES": ligand_smiles}

        response = requests.get(url, params=params, timeout=self.timeout)
        if response.status_code != 200:
            # Feature-25A-02: add format guidance so users know what to fix
            raise RuntimeError(
                f"Ligand preparation failed: HTTP {response.status_code}. "
                "Ensure ligand_smiles is a valid SMILES string "
                "(e.g., 'CC(=O)Oc1ccccc1C(=O)O' for aspirin). "
                "Common issues: unsupported atoms, invalid ring notation, "
                "or special characters. Use canonical SMILES from PubChem or ChEMBL."
            )

    def _prepare_target(self, session_id: str, pdb_id: str):
        """Prepare target protein from PDB ID (raises on error)."""
        url = f"{SWISSDOCK_BASE_URL}/preptarget"
        params = {"sessionNumber": session_id}
        data = {"pdbid": pdb_id}

        response = requests.post(url, params=params, data=data, timeout=self.timeout)
        if response.status_code != 200:
            raise RuntimeError(
                f"Target preparation failed: HTTP {response.status_code}"
            )

    def _set_docking_parameters(
        self,
        session_id: str,
        exhaustiveness: int = 8,
        box_center: Optional[str] = None,
        box_size: Optional[str] = None,
        docking_engine: str = "attracting_cavities",
    ):
        """Set docking parameters (raises on error)."""
        url = f"{SWISSDOCK_BASE_URL}/setparameters"
        params = {"sessionNumber": session_id, "exhaust": exhaustiveness}

        # Add optional parameters
        if box_center:
            params["boxCenter"] = box_center
        if box_size:
            params["boxSize"] = box_size
        if docking_engine.lower() == "vina":
            params["Vina"] = "true"

        response = requests.get(url, params=params, timeout=self.timeout)
        if response.status_code != 200:
            raise RuntimeError(f"Parameter setting failed: HTTP {response.status_code}")

    def _start_docking(self, session_id: str):
        """Start the docking job (raises on error)."""
        url = f"{SWISSDOCK_BASE_URL}/startdock"
        params = {"sessionNumber": session_id}

        response = requests.get(url, params=params, timeout=self.timeout)
        if response.status_code != 200:
            raise RuntimeError(f"Docking start failed: HTTP {response.status_code}")

    # Maps keywords found in status text to canonical status values.
    _STATUS_KEYWORD_MAP = [
        (("COMPLETE", "FINISHED", "DONE"), "FINISHED"),
        (("RUNNING", "PROGRESS"), "RUNNING"),
        (("ERROR", "FAIL"), "ERROR"),
    ]

    def _check_status_api(self, session_id: str) -> Dict[str, Any]:
        """Check docking job status (returns status dict)."""
        url = f"{SWISSDOCK_BASE_URL}/checkstatus"
        params = {"sessionNumber": session_id}

        try:
            response = requests.get(url, params=params, timeout=self.timeout)

            if response.status_code == 404:
                return {"status": "NOT_FOUND"}
            if response.status_code != 200:
                return {"status": "ERROR", "error": f"HTTP {response.status_code}"}

            status_text = response.text.strip().upper()

            for keywords, canonical_status in self._STATUS_KEYWORD_MAP:
                if any(kw in status_text for kw in keywords):
                    return {"status": canonical_status}

            # Assume still running if status text is unrecognized
            return {"status": "RUNNING"}

        except Exception as e:
            return {"status": "ERROR", "error": str(e)}

    def _retrieve_results(self, session_id: str) -> Dict[str, Any]:
        """Retrieve docking results (raises on error)."""
        url = f"{SWISSDOCK_BASE_URL}/retrievesession"
        params = {"sessionNumber": session_id}

        response = requests.get(url, params=params, timeout=60.0)

        if response.status_code == 404:
            raise RuntimeError("Session not found. Results may have expired.")
        elif response.status_code != 200:
            raise RuntimeError(f"Result retrieval failed: HTTP {response.status_code}")

        return {
            "session_id": session_id,
            "download_url": url + "?" + urlencode(params),
            "result_size_bytes": len(response.content),
            "content_type": response.headers.get("Content-Type"),
            "message": "Docking completed successfully. Use download_url to retrieve result files.",
        }

    # ========================================================================
    # AsyncPollingTool Required Methods
    # ========================================================================

    def submit_job(self, arguments: Dict[str, Any]) -> str:
        """
        Submit docking job through multi-step workflow.

        This handles the complete SwissDock workflow:
        1. Check server status
        2. Prepare ligand from SMILES
        3. Prepare target protein
        4. Set docking parameters
        5. Start docking job

        Returns session_id for polling.
        """
        # Check server
        if not self._check_server_status():
            raise RuntimeError(
                "SwissDock server is not responding. Please try again later."
            )

        # Validate required parameters
        ligand_smiles = arguments.get("ligand_smiles")
        pdb_id = arguments.get("pdb_id")

        if not ligand_smiles:
            raise ValueError(
                "ligand_smiles parameter is required. "
                "Provide a valid SMILES string, e.g. 'CC(=O)Oc1ccccc1C(=O)O' for aspirin."
            )
        if not pdb_id:
            raise ValueError("pdb_id parameter is required")

        # Feature-25A-02: basic SMILES sanity check before making the network call
        _smiles = str(ligand_smiles).strip()
        if not _smiles or not any(c.isalpha() for c in _smiles):
            raise ValueError(
                f"ligand_smiles '{_smiles}' does not look like a valid SMILES string. "
                "A SMILES must contain at least one atom symbol (letter). "
                "Example: 'CC(=O)Oc1ccccc1C(=O)O' (aspirin). "
                "Get valid SMILES from PubChem (https://pubchem.ncbi.nlm.nih.gov) "
                "or ChEMBL (https://www.ebi.ac.uk/chembl/)."
            )

        # Validate PDB ID format
        if not isinstance(pdb_id, str) or len(pdb_id) != 4:
            raise ValueError("pdb_id must be a 4-character PDB code (e.g., '1ATP')")

        # Extract optional parameters
        exhaustiveness = arguments.get("exhaustiveness", 8)
        box_center = arguments.get("box_center")
        box_size = arguments.get("box_size")
        docking_engine = arguments.get("docking_engine", "attracting_cavities")

        # Convert box formats if needed
        if box_center and "," in box_center:
            box_center = box_center.replace(",", "_")
        if box_size and "," in box_size:
            box_size = box_size.replace(",", "_")

        # Generate session ID
        session_id = self._generate_session_id()

        # Execute multi-step workflow (each method raises on error)
        self._prepare_ligand(session_id, ligand_smiles)
        self._prepare_target(session_id, pdb_id)
        self._set_docking_parameters(
            session_id, exhaustiveness, box_center, box_size, docking_engine
        )
        self._start_docking(session_id)

        return session_id

    def check_status(self, job_id: str) -> Dict[str, Any]:
        """
        Check SwissDock job status and retrieve results if complete.

        Args:
            job_id: Session ID from submit_job()

        Returns:
            Dict with keys:
                - done (bool): True if complete
                - result (any): Results if done
                - progress (int): Progress percentage
                - error (str): Error message if failed
        """
        status_result = self._check_status_api(job_id)
        job_status = status_result["status"]

        if job_status == "FINISHED":
            try:
                results = self._retrieve_results(job_id)
                return {"done": True, "result": results, "progress": 100}
            except Exception as e:
                return {"done": False, "error": f"Failed to retrieve results: {e}"}

        if job_status == "ERROR":
            error_msg = status_result.get("error", "Unknown error")
            return {"done": False, "error": f"Docking job failed: {error_msg}"}

        if job_status == "NOT_FOUND":
            return {"done": False, "error": "Docking session not found"}

        # RUNNING or unknown status
        return {"done": False, "progress": 50}

    def format_result(self, result: Any) -> Dict[str, Any]:
        """Format SwissDock results into standard response format."""
        return {
            "status": "success",
            "data": result,
            "metadata": {
                "tool": self.name,
                "docking_engine": "SwissDock",
            },
        }

    # ========================================================================
    # Override run() for operation routing
    # ========================================================================

    _OPERATION_HANDLERS = {
        "check_job_status": "_check_job_status_operation",
        "retrieve_results": "_retrieve_results_operation",
    }

    async def run(
        self, arguments: Dict[str, Any], progress: Optional["TaskProgress"] = None
    ) -> Dict[str, Any]:
        """
        Execute the SwissDock API call.

        Routes to appropriate operation handler based on tool configuration.
        """
        if self.operation == "dock_ligand":
            return await super().run(arguments, progress)

        handler_name = self._OPERATION_HANDLERS.get(self.operation)
        if handler_name:
            return await getattr(self, handler_name)(arguments)

        return {"status": "error", "error": f"Unknown operation: {self.operation}"}

    async def _check_job_status_operation(
        self, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check the status of a docking job by session ID (instant operation)."""
        session_id = arguments.get("session_id")

        if not session_id:
            return {"status": "error", "error": "session_id parameter is required"}

        status_result = self._check_status_api(session_id)
        job_status = status_result["status"]

        return {
            "status": "success",
            "data": {
                "session_id": session_id,
                "job_status": job_status,
                "is_finished": job_status == "FINISHED",
                "has_error": job_status in ["ERROR", "NOT_FOUND"],
                "error": status_result.get("error"),
            },
        }

    async def _retrieve_results_operation(
        self, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Retrieve results for a completed docking job (instant operation)."""
        session_id = arguments.get("session_id")

        if not session_id:
            return {"status": "error", "error": "session_id parameter is required"}

        # Check status first
        status_result = self._check_status_api(session_id)
        job_status = status_result["status"]

        if job_status != "FINISHED":
            return {
                "status": "success",
                "data": {
                    "session_id": session_id,
                    "job_status": job_status,
                    "message": f"Job is not finished yet. Status: {job_status}",
                },
            }

        # Retrieve results
        try:
            results = self._retrieve_results(session_id)
            return {"data": results}
        except Exception as e:
            return {"status": "error", "error": f"Failed to retrieve results: {e}"}
