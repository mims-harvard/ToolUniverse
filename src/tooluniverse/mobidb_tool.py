# mobidb_tool.py
"""
MobiDB tool for ToolUniverse.

MobiDB is a comprehensive database of protein disorder and mobility,
integrating curated data from DisProt, predicted disorder from MobiDB-lite,
and structural data from PDB to provide a consensus view of intrinsically
disordered regions, linear interacting peptides (LIPs), and binding modes.

API: https://mobidb.org/api/download
No authentication required.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

MOBIDB_BASE_URL = "https://mobidb.bio.unipd.it/api/download"


@register_tool("MobiDBTool")
class MobiDBTool(BaseTool):
    """
    Tool for querying MobiDB protein disorder database.

    Supports:
    - Get protein disorder predictions, curated regions, PTMs, binding modes
    - Get consensus disorder summary for a protein

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 60)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "get_protein")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the MobiDB API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {"error": f"MobiDB API timed out after {self.timeout}s."}
        except requests.exceptions.ConnectionError:
            return {"error": "Failed to connect to MobiDB API (mobidb.bio.unipd.it)."}
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else "unknown"
            if status == 404:
                return {
                    "error": "Protein not found in MobiDB. Check the UniProt accession."
                }
            return {"error": f"MobiDB API HTTP {status}"}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint."""
        if self.endpoint == "get_protein":
            return self._get_protein(arguments)
        elif self.endpoint == "get_consensus":
            return self._get_consensus(arguments)
        else:
            return {"error": f"Unknown endpoint: {self.endpoint}"}

    def _get_protein(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get comprehensive disorder data for a protein from MobiDB."""
        accession = arguments.get("accession", "")
        if not accession:
            return {
                "error": "accession is required (UniProt ID, e.g., 'P04637' for TP53)."
            }

        url = MOBIDB_BASE_URL
        params = {"acc": accession, "format": "json"}
        response = requests.get(
            url, params=params, allow_redirects=True, timeout=self.timeout
        )
        response.raise_for_status()
        data = response.json()

        # Extract key disorder data
        prediction = data.get("prediction-disorder-mobidb_lite", {})
        curated_disorder = data.get("curated-disorder-disprot", {})
        curated_lip = data.get("curated-lip-disprot", {})

        # Extract PTM info
        ptms = data.get("ptms", {})
        ptm_summary = {}
        if isinstance(ptms, dict):
            ptm_names = ptms.get("names", [])
            ptm_positions = ptms.get("positions", [])
            ptm_summary = {
                "count": len(ptm_positions) if isinstance(ptm_positions, list) else 0,
                "types": ptm_names[:10] if isinstance(ptm_names, list) else [],
            }

        return {
            "data": {
                "accession": data.get("acc"),
                "gene": data.get("gene"),
                "name": data.get("name"),
                "organism": data.get("organism"),
                "length": data.get("length"),
                "sequence": data.get("sequence"),
                "prediction_disorder": {
                    "regions": prediction.get("regions", []),
                    "content_fraction": prediction.get("content_fraction"),
                    "content_count": prediction.get("content_count"),
                },
                "curated_disorder": {
                    "regions": curated_disorder.get("regions", []),
                    "content_count": curated_disorder.get("content_count"),
                },
                "curated_lip": {
                    "regions": curated_lip.get("regions", []),
                    "content_count": curated_lip.get("content_count"),
                },
                "ptm_summary": ptm_summary,
                "localization": data.get("localization", []),
            },
            "metadata": {
                "source": "MobiDB (mobidb.org)",
                "reviewed": data.get("reviewed"),
            },
        }

    def _get_consensus(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get consensus disorder summary for a protein."""
        accession = arguments.get("accession", "")
        if not accession:
            return {
                "error": "accession is required (UniProt ID, e.g., 'P04637' for TP53)."
            }

        url = MOBIDB_BASE_URL
        params = {"acc": accession, "format": "json"}
        response = requests.get(
            url, params=params, allow_redirects=True, timeout=self.timeout
        )
        response.raise_for_status()
        data = response.json()

        # Extract consensus disorder data
        consensus_disorder = data.get("prediction-disorder-mobidb_lite", {})
        curated_merge = data.get("curated-disorder-merge", {})
        phase_sep = data.get("curated-phase_separation-priority", {})

        # Collect all binding mode info
        binding_modes = {}
        for key in data:
            if key.startswith("curated-binding_mode"):
                bm_data = data[key]
                if isinstance(bm_data, dict) and bm_data.get("regions"):
                    binding_modes[key] = {
                        "regions": bm_data.get("regions", []),
                        "content_count": bm_data.get("content_count"),
                    }

        return {
            "data": {
                "accession": data.get("acc"),
                "gene": data.get("gene"),
                "name": data.get("name"),
                "organism": data.get("organism"),
                "length": data.get("length"),
                "predicted_disorder": {
                    "regions": consensus_disorder.get("regions", []),
                    "content_fraction": consensus_disorder.get("content_fraction"),
                },
                "curated_disorder_merged": {
                    "regions": curated_merge.get("regions", []),
                },
                "phase_separation": {
                    "regions": phase_sep.get("regions", []),
                },
                "binding_modes": binding_modes,
            },
            "metadata": {
                "source": "MobiDB (mobidb.org)",
            },
        }
