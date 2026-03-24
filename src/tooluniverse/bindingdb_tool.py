"""
BindingDB Tool - Query protein-ligand binding affinity data.

BindingDB contains 3.2M data points for 1.4M compounds and 11.4K targets.
Provides binding affinities (Ki, IC50, Kd) for drug discovery research.
"""

from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool
import requests


@register_tool("BindingDBTool")
class BindingDBTool(BaseTool):
    """Tool for querying BindingDB binding affinity database."""

    BASE_URL = "https://www.bindingdb.org/rest"

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.parameter = tool_config.get("parameter", {})
        self.required = self.parameter.get("required", [])
        self.operation = tool_config.get("fields", {}).get(
            "operation", "get_ligands_by_uniprot"
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate operation handler."""
        operation = self.operation

        if operation == "get_ligands_by_uniprot":
            return self._get_ligands_by_uniprot(arguments)
        elif operation == "get_ligands_by_uniprots":
            return self._get_ligands_by_uniprots(arguments)
        elif operation == "get_ligands_by_pdb":
            return self._get_ligands_by_pdb(arguments)
        elif operation == "get_targets_by_compound":
            return self._get_targets_by_compound(arguments)
        else:
            return {"status": "error", "error": f"Unknown operation: {operation}"}

    def _get_ligands_by_uniprot(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get binding data for a single UniProt protein."""
        uniprot = arguments.get("uniprot_id") or arguments.get("uniprot")
        if not uniprot:
            return {
                "status": "error",
                "error": "Missing required parameter: uniprot_id",
            }

        cutoff = arguments.get("affinity_cutoff", 10000)  # nM

        try:
            response = requests.get(
                f"{self.BASE_URL}/getLigandsByUniprot",
                params={
                    "uniprot": f"{uniprot};{cutoff}",
                    "response": "application/json",
                },
                timeout=60,
            )
            response.raise_for_status()

            data = response.json()

            # Extract affinities from response
            affinities = data.get("getLindsByUniprotResponse", {}).get(
                "bdb.affinities", []
            )

            if not affinities:
                return {
                    "status": "success",
                    "data": [],
                    "count": 0,
                    "message": f"No binding data found for UniProt {uniprot} with affinity cutoff {cutoff} nM",
                }

            return {
                "status": "success",
                "data": affinities,
                "count": len(affinities),
                "uniprot": uniprot,
                "affinity_cutoff_nM": cutoff,
            }

        except requests.exceptions.Timeout:
            return {"status": "error", "error": "Request timed out after 60s"}
        except requests.exceptions.HTTPError as e:
            return {"status": "error", "error": f"HTTP error: {e.response.status_code}"}
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Error: {str(e)}"}

    def _get_ligands_by_uniprots(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get binding data for multiple UniProt proteins."""
        uniprots = arguments.get("uniprot_ids") or arguments.get("uniprots")
        if not uniprots:
            return {
                "status": "error",
                "error": "Missing required parameter: uniprot_ids",
            }

        # Accept both string and list
        if isinstance(uniprots, list):
            uniprots = ",".join(uniprots)

        cutoff = arguments.get("affinity_cutoff", 10000)  # nM

        try:
            response = requests.get(
                f"{self.BASE_URL}/getLigandsByUniprots",
                params={
                    "uniprot": uniprots,
                    "cutoff": cutoff,
                    "response": "application/json",
                },
                timeout=60,
            )
            response.raise_for_status()

            data = response.json()

            # Extract affinities from response
            affinities = data.get("getLindsByUniprotsResponse", {}).get(
                "affinities", []
            )

            if not affinities:
                return {
                    "status": "success",
                    "data": [],
                    "count": 0,
                    "message": f"No binding data found for UniProts {uniprots}",
                }

            return {
                "status": "success",
                "data": affinities,
                "count": len(affinities),
                "uniprots": uniprots,
                "affinity_cutoff_nM": cutoff,
            }

        except requests.exceptions.Timeout:
            return {"status": "error", "error": "Request timed out after 60s"}
        except requests.exceptions.HTTPError as e:
            return {"status": "error", "error": f"HTTP error: {e.response.status_code}"}
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Error: {str(e)}"}

    def _get_ligands_by_pdb(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get binding data for proteins by PDB ID."""
        pdb_ids = arguments.get("pdb_ids")
        if not pdb_ids:
            return {"status": "error", "error": "Missing required parameter: pdb_ids"}

        # Accept both string and list
        if isinstance(pdb_ids, list):
            pdb_ids = ",".join(pdb_ids)

        cutoff = arguments.get("affinity_cutoff", 10000)  # nM
        identity = arguments.get("sequence_identity", 100)  # percent

        try:
            response = requests.get(
                f"{self.BASE_URL}/getLigandsByPDBs",
                params={
                    "pdb": pdb_ids,
                    "cutoff": cutoff,
                    "identity": identity,
                    "response": "application/json",
                },
                timeout=60,
            )
            response.raise_for_status()

            data = response.json()

            # Extract affinities from response
            affinities = data.get("getLindsByPDBsResponse", {}).get("affinities", [])

            if not affinities:
                return {
                    "status": "success",
                    "data": [],
                    "count": 0,
                    "message": f"No binding data found for PDB IDs {pdb_ids}",
                }

            return {
                "status": "success",
                "data": affinities,
                "count": len(affinities),
                "pdb_ids": pdb_ids,
                "affinity_cutoff_nM": cutoff,
                "sequence_identity": identity,
            }

        except requests.exceptions.Timeout:
            return {"status": "error", "error": "Request timed out after 60s"}
        except requests.exceptions.HTTPError as e:
            return {"status": "error", "error": f"HTTP error: {e.response.status_code}"}
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Error: {str(e)}"}

    def _get_targets_by_compound(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get binding targets for a compound by SMILES."""
        smiles = arguments.get("smiles")
        if not smiles:
            return {"status": "error", "error": "Missing required parameter: smiles"}

        similarity_cutoff = arguments.get("similarity_cutoff", 0.85)

        try:
            response = requests.get(
                f"{self.BASE_URL}/getTargetByCompound",
                params={
                    "smiles": smiles,
                    "cutoff": similarity_cutoff,
                    "response": "application/json",
                },
                timeout=60,
            )
            response.raise_for_status()

            data = response.json()

            # Extract targets from response
            targets = data.get("getLindsByUniprotResponse", {}).get(
                "bdb.affinities", []
            )

            if not targets:
                return {
                    "status": "success",
                    "data": [],
                    "count": 0,
                    "message": f"No targets found for compound with similarity cutoff {similarity_cutoff}",
                }

            return {
                "status": "success",
                "data": targets,
                "count": len(targets),
                "smiles": smiles,
                "similarity_cutoff": similarity_cutoff,
            }

        except requests.exceptions.Timeout:
            return {"status": "error", "error": "Request timed out after 60s"}
        except requests.exceptions.HTTPError as e:
            return {"status": "error", "error": f"HTTP error: {e.response.status_code}"}
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Error: {str(e)}"}
