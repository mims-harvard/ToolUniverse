# mddb_tool.py
"""
MDDB (Molecular Dynamics Database) tool for ToolUniverse.

MDDB indexes over 15,000 molecular dynamics simulation trajectories
(MoDEL, BioExcel, DESRES-ANTON releases, and community depositions): force
field, ensemble, temperature, simulated time, frame count, and trajectory
file size, searchable by protein name or PDB identifier. ToolUniverse can
run its own MD-adjacent predictions but had no way to find or characterize
an existing published trajectory.

The search endpoint returns HTTP 500 (bare "Internal Server Error" text,
no structured body) both when a query genuinely matches nothing and,
presumably, for unrelated transient failures — the two are not
distinguishable from the response alone, so both are reported as "no
matching projects" with that ambiguity stated rather than guessed at.

API: https://mdposit.mddbr.eu/api/rest/v1
No authentication required.
"""

from typing import Any, Dict

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

MDDB_BASE_URL = "https://mdposit.mddbr.eu/api/rest/v1"


@register_tool("MDDBTool")
class MDDBTool(BaseTool):
    """
    Tool for searching the MDDB molecular dynamics trajectory database.

    Supports searching projects by protein name or PDB id, and fetching
    one project's simulation metadata (force field, ensemble, temperature,
    length, frame count).

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 45)
        self.operation = tool_config.get("fields", {}).get(
            "operation", "search_projects"
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the MDDB lookup."""
        try:
            if self.operation == "search_projects":
                return self._search_projects(arguments)
            if self.operation == "get_project":
                return self._get_project(arguments)
            return {
                "status": "error",
                "error": f"Unknown operation: {self.operation}",
            }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"MDDB request timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to MDDB. Check network.",
            }
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code if e.response is not None else "unknown"
            return {"status": "error", "error": f"MDDB returned HTTP {code}"}
        except ValueError:
            return {"status": "error", "error": "MDDB returned a non-JSON response"}
        except Exception as e:
            return {"status": "error", "error": f"Error querying MDDB: {str(e)}"}

    def _search_projects(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search MD trajectory projects by protein name or PDB id."""
        query = (arguments.get("query") or "").strip()
        if not query:
            return {
                "status": "error",
                "error": "query is required, e.g. a protein name or PDB id "
                "such as '6M71'.",
            }

        limit = arguments.get("limit")
        if not isinstance(limit, int) or limit <= 0:
            limit = 25
        limit = min(limit, 100)

        response = requests.get(
            f"{MDDB_BASE_URL}/projects",
            params={"search": query, "limit": limit},
            timeout=self.timeout,
        )
        if response.status_code == 500:
            # MDDB returns a bare 500 both for genuinely zero-match queries
            # and, presumably, unrelated transient failures; the response
            # body gives no way to tell the two apart.
            return {
                "status": "error",
                "error": f"No MDDB projects matching '{query}' (or a "
                "transient server error -- MDDB returns HTTP 500 for both).",
            }
        response.raise_for_status()
        payload = response.json()
        projects = payload.get("projects") or []

        if not projects:
            return {
                "status": "error",
                "error": f"No MDDB projects matching '{query}'.",
            }

        rows = []
        for project in projects:
            metadata = project.get("metadata") or {}
            rows.append(
                {
                    "accession": project.get("accession"),
                    "name": metadata.get("NAME"),
                    "pdb_ids": metadata.get("PDBIDS") or [],
                    "description": metadata.get("DESCRIPTION"),
                    "force_field": metadata.get("FF"),
                    "program": metadata.get("PROGRAM"),
                }
            )

        return {
            "status": "success",
            "data": rows,
            "metadata": {
                "query": query,
                "total_matching": payload.get("filteredCount"),
                "returned": len(rows),
                "note": "accession is what get_project expects for full "
                "simulation parameters.",
                "source": "MDDB (Molecular Dynamics Database)",
            },
        }

    def _get_project(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch one MD project's simulation parameters and trajectory stats."""
        accession = (arguments.get("accession") or "").strip()
        if not accession:
            return {
                "status": "error",
                "error": "accession is required, e.g. 'MD-A001UA'. Use "
                "search_projects to find one.",
            }

        response = requests.get(
            f"{MDDB_BASE_URL}/projects/{accession}", timeout=self.timeout
        )
        if response.status_code == 404:
            return {
                "status": "error",
                "error": f"No MDDB project with accession '{accession}'.",
            }
        response.raise_for_status()
        payload = response.json()
        metadata = payload.get("metadata") or {}

        return {
            "status": "success",
            "data": {
                "accession": payload.get("accession"),
                "name": metadata.get("NAME"),
                "pdb_ids": metadata.get("PDBIDS") or [],
                "description": metadata.get("DESCRIPTION"),
                "force_field": metadata.get("FF"),
                "temperature_k": metadata.get("TEMP"),
                "ensemble": metadata.get("ENSEMBLE"),
                "program": metadata.get("PROGRAM"),
                "chains": payload.get("chains") or [],
                "md_replica_count": payload.get("mdcount"),
                "total_simulated_time_ps": payload.get("totalTime"),
                "total_frames": payload.get("totalFrames"),
                "total_size_bytes": payload.get("totalSize"),
            },
            "metadata": {
                "accession": accession,
                "note": "total_simulated_time_ps is summed across all MD "
                "replicas listed under md_replica_count.",
                "source": "MDDB (Molecular Dynamics Database)",
            },
        }
