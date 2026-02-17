# pdbe_kb_tool.py
"""
PDBe-KB (PDBe Knowledge Base) Graph API tool for ToolUniverse.

PDBe-KB is an aggregated knowledge base that integrates structural data from
PDB with functional annotations from 30+ partner resources (UniProt, CATH,
SCOP, Pfam, etc.). The Graph API provides access to ligand binding sites,
protein-protein interaction interfaces, structural summaries, and more.

API: https://www.ebi.ac.uk/pdbe/graph-api/
No authentication required.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

PDBE_KB_BASE_URL = "https://www.ebi.ac.uk/pdbe/graph-api"


@register_tool("PDBe_KB_Tool")
class PDBe_KB_Tool(BaseTool):
    """
    Tool for querying PDBe-KB (Knowledge Base) Graph API.

    PDBe-KB aggregates structural biology knowledge including:
    - Ligand binding sites mapped to UniProt positions
    - Protein-protein interaction interfaces
    - Structural coverage statistics
    - Superposition clusters and best chain coverage

    Data is indexed by UniProt accession and provides residue-level
    annotations using UniProt numbering.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "summary_stats")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the PDBe-KB Graph API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {"error": f"PDBe-KB API timed out after {self.timeout}s"}
        except requests.exceptions.ConnectionError:
            return {"error": "Failed to connect to PDBe-KB API"}
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                acc = arguments.get("uniprot_accession", "unknown")
                return {"error": f"No PDBe-KB data found for {acc}"}
            return {"error": f"PDBe-KB API HTTP error: {e.response.status_code}"}
        except Exception as e:
            return {"error": f"Unexpected error querying PDBe-KB: {str(e)}"}

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate PDBe-KB endpoint."""
        if self.endpoint == "summary_stats":
            return self._get_summary_stats(arguments)
        elif self.endpoint == "ligand_sites":
            return self._get_ligand_sites(arguments)
        elif self.endpoint == "interface_residues":
            return self._get_interface_residues(arguments)
        elif self.endpoint == "superposition":
            return self._get_superposition(arguments)
        else:
            return {"error": f"Unknown endpoint: {self.endpoint}"}

    def _get_summary_stats(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get aggregated structural summary statistics for a protein."""
        acc = arguments.get("uniprot_accession", "")
        if not acc:
            return {"error": "uniprot_accession parameter is required"}

        url = f"{PDBE_KB_BASE_URL}/uniprot/summary_stats/{acc}"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        if acc not in data:
            return {"error": f"No summary data for {acc}"}

        stats = data[acc]
        return {
            "data": {
                "uniprot_accession": acc,
                "pdbs": stats.get("pdbs"),
                "ligands": stats.get("ligands"),
                "interaction_partners": stats.get("interaction_partners"),
                "annotations": stats.get("annotations"),
                "similar_proteins": stats.get("similar_proteins"),
            },
            "metadata": {
                "source": "PDBe-KB (PDBe Knowledge Base) Graph API",
            },
        }

    def _get_ligand_sites(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get ligand binding site residues for a protein."""
        acc = arguments.get("uniprot_accession", "")
        if not acc:
            return {"error": "uniprot_accession parameter is required"}

        url = f"{PDBE_KB_BASE_URL}/uniprot/ligand_sites/{acc}"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        if acc not in data:
            return {"error": f"No ligand binding data for {acc}"}

        protein_data = data[acc]
        ligands = []
        max_ligands = 50  # Limit output size

        for entry in protein_data.get("data", [])[:max_ligands]:
            binding_residues = []
            for res in entry.get("residues", [])[:20]:
                binding_residues.append(
                    {
                        "start": res.get("startIndex"),
                        "end": res.get("endIndex"),
                        "pdb_entries": res.get("allPDBEntries", [])[:10],
                    }
                )

            additional = entry.get("additionalData", {})
            ligands.append(
                {
                    "name": entry.get("name"),
                    "accession": entry.get("accession"),
                    "binding_residues": binding_residues,
                    "is_cofactor": bool(additional.get("coFactorId")),
                    "is_solvent": additional.get("isSolvent", False),
                    "chembl_id": additional.get("chemblId") or None,
                    "drugbank_id": additional.get("drugBankId") or None,
                }
            )

        return {
            "data": {
                "uniprot_accession": acc,
                "protein_length": protein_data.get("length"),
                "ligands": ligands,
                "total_ligands": len(protein_data.get("data", [])),
            },
            "metadata": {
                "source": "PDBe-KB (PDBe Knowledge Base) Graph API",
            },
        }

    def _get_interface_residues(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get protein-protein interaction interface residues."""
        acc = arguments.get("uniprot_accession", "")
        if not acc:
            return {"error": "uniprot_accession parameter is required"}

        url = f"{PDBE_KB_BASE_URL}/uniprot/interface_residues/{acc}"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        if acc not in data:
            return {"error": f"No interface data for {acc}"}

        protein_data = data[acc]
        partners = []
        max_partners = 30

        for entry in protein_data.get("data", [])[:max_partners]:
            interface_residues = []
            for res in entry.get("residues", [])[:30]:
                interface_residues.append(
                    {
                        "start": res.get("startIndex"),
                        "end": res.get("endIndex"),
                        "pdb_entries": res.get("allPDBEntries", [])[:10],
                    }
                )

            partners.append(
                {
                    "partner_name": entry.get("name"),
                    "partner_accession": entry.get("accession"),
                    "interface_residues": interface_residues,
                }
            )

        return {
            "data": {
                "uniprot_accession": acc,
                "protein_length": protein_data.get("length"),
                "interaction_partners": partners,
                "total_partners": len(protein_data.get("data", [])),
            },
            "metadata": {
                "source": "PDBe-KB (PDBe Knowledge Base) Graph API",
            },
        }

    def _get_superposition(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get structural superposition clusters for a protein.

        Returns clusters of structurally superposed PDB chains grouped by
        protein segments. Each cluster contains a representative structure
        and aligned member structures.
        """
        acc = arguments.get("uniprot_accession", "")
        if not acc:
            return {
                "error": "uniprot_accession parameter is required (e.g., 'P04637' for TP53, 'P00533' for EGFR)."
            }

        url = f"{PDBE_KB_BASE_URL}/uniprot/superposition/{acc}"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        if acc not in data:
            return {"error": f"No superposition data for {acc}"}

        segments_data = data[acc]
        segments = []

        for seg in segments_data[:10]:
            clusters = seg.get("clusters", [])
            cluster_results = []

            for cluster in clusters[:10]:
                members = []
                representative = None
                for member in cluster[:20]:
                    entry = {
                        "pdb_id": member.get("pdb_id"),
                        "auth_asym_id": member.get("auth_asym_id"),
                        "struct_asym_id": member.get("struct_asym_id"),
                        "entity_id": member.get("entity_id"),
                        "is_representative": member.get("is_representative", False),
                    }
                    if entry["is_representative"]:
                        representative = entry
                    members.append(entry)

                cluster_results.append(
                    {
                        "representative": representative,
                        "total_members": len(cluster),
                        "members": members,
                    }
                )

            segments.append(
                {
                    "segment_start": seg.get("segment_start"),
                    "segment_end": seg.get("segment_end"),
                    "num_clusters": len(clusters),
                    "clusters": cluster_results,
                }
            )

        return {
            "data": {
                "uniprot_accession": acc,
                "segments": segments,
                "total_segments": len(segments_data),
            },
            "metadata": {
                "source": "PDBe-KB (PDBe Knowledge Base) Graph API",
            },
        }
