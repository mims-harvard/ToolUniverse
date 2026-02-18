# pdbe_validation_tool.py
"""
PDBe Validation tool for ToolUniverse.

Provides structure quality validation data from PDBe, including
global percentile scores and residue-level outlier information.

API: https://www.ebi.ac.uk/pdbe/api/validation/
No authentication required.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

PDBE_BASE_URL = "https://www.ebi.ac.uk/pdbe/api"


@register_tool("PDBeValidationTool")
class PDBeValidationTool(BaseTool):
    """
    Tool for querying PDBe structure validation data.

    Supports:
    - Global quality percentile scores (Ramachandran, rotamer, clashscore)
    - Residue-level validation outliers

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "quality_scores")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the PDBe Validation API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {"error": f"PDBe API timed out after {self.timeout}s"}
        except requests.exceptions.ConnectionError:
            return {"error": "Failed to connect to PDBe API"}
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else "unknown"
            return {
                "error": f"PDBe API HTTP {status}: structure may not exist or have validation data"
            }
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint."""
        if self.endpoint == "quality_scores":
            return self._get_quality_scores(arguments)
        elif self.endpoint == "outlier_residues":
            return self._get_outlier_residues(arguments)
        else:
            return {"error": f"Unknown endpoint: {self.endpoint}"}

    def _get_quality_scores(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get global quality validation percentile scores."""
        pdb_id = arguments.get("pdb_id", "").lower()
        if not pdb_id:
            return {"error": "pdb_id is required (e.g., '4hhb')."}

        url = f"{PDBE_BASE_URL}/validation/global-percentiles/entry/{pdb_id}"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        entry = data.get(pdb_id, {})
        if not entry:
            return {"error": f"No validation data found for PDB {pdb_id}"}

        quality_metrics = {}
        rama = entry.get("percent-rama-outliers", {})
        if rama:
            quality_metrics["ramachandran_outliers"] = {
                "raw_value": rama.get("rawvalue"),
                "absolute_percentile": rama.get("absolute"),
                "relative_percentile": rama.get("relative"),
            }

        rota = entry.get("percent-rota-outliers", {})
        if rota:
            quality_metrics["rotamer_outliers"] = {
                "raw_value": rota.get("rawvalue"),
                "absolute_percentile": rota.get("absolute"),
                "relative_percentile": rota.get("relative"),
            }

        clash = entry.get("clashscore", {})
        if clash:
            quality_metrics["clashscore"] = {
                "raw_value": clash.get("rawvalue"),
                "absolute_percentile": clash.get("absolute"),
                "relative_percentile": clash.get("relative"),
            }

        return {
            "data": {
                "pdb_id": pdb_id,
                "quality_metrics": quality_metrics,
            },
            "metadata": {
                "source": "PDBe Validation API (ebi.ac.uk/pdbe)",
                "description": "Percentile scores: higher = better quality. Absolute = vs all structures. Relative = vs similar resolution.",
            },
        }

    def _get_outlier_residues(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get residue-level validation outliers."""
        pdb_id = arguments.get("pdb_id", "").lower()
        if not pdb_id:
            return {"error": "pdb_id is required (e.g., '4hhb')."}

        url = f"{PDBE_BASE_URL}/validation/residuewise_outlier_summary/entry/{pdb_id}"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        entry = data.get(pdb_id, {})
        if not entry:
            return {"error": f"No validation outlier data found for PDB {pdb_id}"}

        molecules = []
        total_outliers = 0

        mol_data = entry.get("molecules", [])
        for mol in mol_data:
            entity_id = mol.get("entity_id")
            chains_data = mol.get("chains", [])
            chains = []
            for chain in chains_data:
                chain_id = chain.get("chain_id")
                models = chain.get("models", [])
                outlier_residues = []

                # Models is a list of {model_id, residues} objects
                if isinstance(models, list):
                    for model in models:
                        residues = model.get("residues", [])
                        for res in residues:
                            outlier_types = list(res.get("outlier_types", []))
                            if outlier_types:
                                outlier_residues.append(
                                    {
                                        "residue_number": res.get("residue_number"),
                                        "residue_name": res.get(
                                            "author_residue_number",
                                            res.get("residue_number"),
                                        ),
                                        "outlier_types": outlier_types,
                                    }
                                )
                                total_outliers += 1
                elif isinstance(models, dict):
                    # Fallback for dict format
                    for model_id, residues in models.items():
                        for res in residues:
                            outlier_types = list(res.get("outlier_types", []))
                            if outlier_types:
                                outlier_residues.append(
                                    {
                                        "residue_number": res.get("residue_number"),
                                        "residue_name": res.get(
                                            "author_residue_number",
                                            res.get("residue_number"),
                                        ),
                                        "outlier_types": outlier_types,
                                    }
                                )
                                total_outliers += 1

                chains.append(
                    {
                        "chain_id": chain_id,
                        "outlier_residues": outlier_residues,
                    }
                )

            molecules.append(
                {
                    "entity_id": entity_id,
                    "chains": chains,
                }
            )

        return {
            "data": {
                "pdb_id": pdb_id,
                "molecules": molecules,
            },
            "metadata": {
                "source": "PDBe Validation API (ebi.ac.uk/pdbe)",
                "total_outlier_residues": total_outliers,
            },
        }
