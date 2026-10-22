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
            return {
                "status": "error",
                "error": f"PDBe-KB API timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {"status": "error", "error": "Failed to connect to PDBe-KB API"}
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                acc = arguments.get("uniprot_accession", "unknown")
                return {"status": "error", "error": f"No PDBe-KB data found for {acc}"}
            return {
                "status": "error",
                "error": f"PDBe-KB API HTTP error: {e.response.status_code}",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error querying PDBe-KB: {str(e)}",
            }

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
            return {"status": "error", "error": f"Unknown endpoint: {self.endpoint}"}

    def _get_summary_stats(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get aggregated structural summary statistics for a protein."""
        acc = arguments.get("uniprot_accession", "")
        if not acc:
            return {
                "status": "error",
                "error": "uniprot_accession parameter is required",
            }

        url = f"{PDBE_KB_BASE_URL}/uniprot/summary_stats/{acc}"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        if acc not in data:
            return {"status": "error", "error": f"No summary data for {acc}"}

        stats = data[acc]
        return {
            "status": "success",
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
            return {
                "status": "error",
                "error": "uniprot_accession parameter is required",
            }

        url = f"{PDBE_KB_BASE_URL}/uniprot/ligand_sites/{acc}"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        if acc not in data:
            return {"status": "error", "error": f"No ligand binding data for {acc}"}

        protein_data = data[acc]
        ligands = []
        all_ligand_entries = protein_data.get("data", [])
        ligand_offset = max(int(arguments.get("ligand_offset") or 0), 0)
        max_ligands = arguments.get("max_ligands")
        # Check for None explicitly, then require a positive page size so the
        # advertised next offset always advances.
        max_ligands = 100 if max_ligands is None else max(1, int(max_ligands))
        residue_offset = max(int(arguments.get("residue_offset") or 0), 0)
        residue_limit = min(max(int(arguments.get("residue_limit") or 20), 1), 500)
        pdb_entry_offset = max(int(arguments.get("pdb_entry_offset") or 0), 0)
        pdb_entry_limit = min(
            max(int(arguments.get("pdb_entry_limit") or 10), 1), 500
        )

        ligand_page = all_ligand_entries[
            ligand_offset : ligand_offset + max_ligands
        ]
        for entry in ligand_page:
            all_residues = entry.get("residues", [])
            residue_page = all_residues[
                residue_offset : residue_offset + residue_limit
            ]
            binding_residues = []
            for res in residue_page:
                all_pdb_entries = res.get("allPDBEntries", [])
                pdb_entry_page = all_pdb_entries[
                    pdb_entry_offset : pdb_entry_offset + pdb_entry_limit
                ]
                pdb_entries_truncated = (
                    pdb_entry_offset + len(pdb_entry_page) < len(all_pdb_entries)
                )
                binding_residues.append(
                    {
                        "start": res.get("startIndex"),
                        "end": res.get("endIndex"),
                        "pdb_entries": pdb_entry_page,
                        "pdb_entries_total": len(all_pdb_entries),
                        "pdb_entries_returned": len(pdb_entry_page),
                        "pdb_entries_truncated": pdb_entries_truncated,
                        "next_pdb_entry_offset": (
                            pdb_entry_offset + len(pdb_entry_page)
                            if pdb_entries_truncated
                            else None
                        ),
                    }
                )

            additional = entry.get("additionalData", {})
            residues_truncated = residue_offset + len(residue_page) < len(all_residues)
            ligands.append(
                {
                    "name": entry.get("name"),
                    "accession": entry.get("accession"),
                    "binding_residues": binding_residues,
                    "binding_residues_total": len(all_residues),
                    "binding_residues_returned": len(residue_page),
                    "binding_residues_truncated": residues_truncated,
                    "next_residue_offset": (
                        residue_offset + len(residue_page)
                        if residues_truncated
                        else None
                    ),
                    "is_cofactor": bool(additional.get("coFactorId")),
                    "is_solvent": additional.get("isSolvent", False),
                    "chembl_id": additional.get("chemblId") or None,
                    "drugbank_id": additional.get("drugBankId") or None,
                }
            )

        result_data = {
            "uniprot_accession": acc,
            "protein_length": protein_data.get("length"),
            "ligands": ligands,
            "total_ligands": len(all_ligand_entries),
            "ligand_offset": ligand_offset,
            "ligands_returned": len(ligands),
        }
        ligands_truncated = ligand_offset + len(ligand_page) < len(all_ligand_entries)
        result_data["truncated"] = ligands_truncated
        result_data["next_ligand_offset"] = (
            ligand_offset + len(ligand_page) if ligands_truncated else None
        )
        if ligands_truncated:
            result_data["truncated"] = True
            result_data["truncation_note"] = (
                f"Returning {len(ligands)} ligands from offset {ligand_offset} of "
                f"{len(all_ligand_entries)} total. Continue with "
                f"ligand_offset={ligand_offset + len(ligand_page)}. "
                "The API does not guarantee ordering by clinical relevance, so "
                "page through every ligand when looking for a specific compound."
            )

        return {
            "status": "success",
            "data": result_data,
            "metadata": {
                "source": "PDBe-KB (PDBe Knowledge Base) Graph API",
            },
        }

    def _get_interface_residues(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get protein-protein interaction interface residues."""
        acc = arguments.get("uniprot_accession", "")
        if not acc:
            return {
                "status": "error",
                "error": "uniprot_accession parameter is required",
            }

        url = f"{PDBE_KB_BASE_URL}/uniprot/interface_residues/{acc}"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        if acc not in data:
            return {"status": "error", "error": f"No interface data for {acc}"}

        protein_data = data[acc]
        partners = []
        all_partner_entries = protein_data.get("data", [])
        partner_offset = max(int(arguments.get("partner_offset") or 0), 0)
        max_partners = arguments.get("max_partners")
        # Check for None explicitly, then require a positive page size so the
        # advertised next offset always advances.
        max_partners = 60 if max_partners is None else max(1, int(max_partners))
        residue_offset = max(int(arguments.get("residue_offset") or 0), 0)
        residue_limit = min(max(int(arguments.get("residue_limit") or 30), 1), 500)
        pdb_entry_offset = max(int(arguments.get("pdb_entry_offset") or 0), 0)
        pdb_entry_limit = min(
            max(int(arguments.get("pdb_entry_limit") or 10), 1), 500
        )

        partner_page = all_partner_entries[
            partner_offset : partner_offset + max_partners
        ]
        for entry in partner_page:
            all_residues = entry.get("residues", [])
            residue_page = all_residues[
                residue_offset : residue_offset + residue_limit
            ]
            interface_residues = []
            for res in residue_page:
                all_pdb_entries = res.get("allPDBEntries", [])
                pdb_entry_page = all_pdb_entries[
                    pdb_entry_offset : pdb_entry_offset + pdb_entry_limit
                ]
                pdb_entries_truncated = (
                    pdb_entry_offset + len(pdb_entry_page) < len(all_pdb_entries)
                )
                interface_residues.append(
                    {
                        "start": res.get("startIndex"),
                        "end": res.get("endIndex"),
                        "pdb_entries": pdb_entry_page,
                        "pdb_entries_total": len(all_pdb_entries),
                        "pdb_entries_returned": len(pdb_entry_page),
                        "pdb_entries_truncated": pdb_entries_truncated,
                        "next_pdb_entry_offset": (
                            pdb_entry_offset + len(pdb_entry_page)
                            if pdb_entries_truncated
                            else None
                        ),
                    }
                )

            residues_truncated = residue_offset + len(residue_page) < len(all_residues)
            partners.append(
                {
                    "partner_name": entry.get("name"),
                    "partner_accession": entry.get("accession"),
                    "interface_residues": interface_residues,
                    "interface_residues_total": len(all_residues),
                    "interface_residues_returned": len(residue_page),
                    "interface_residues_truncated": residues_truncated,
                    "next_residue_offset": (
                        residue_offset + len(residue_page)
                        if residues_truncated
                        else None
                    ),
                }
            )

        result_data = {
            "uniprot_accession": acc,
            "protein_length": protein_data.get("length"),
            "interaction_partners": partners,
            "total_partners": len(all_partner_entries),
            "partner_offset": partner_offset,
            "partners_returned": len(partners),
        }
        partners_truncated = partner_offset + len(partner_page) < len(
            all_partner_entries
        )
        result_data["truncated"] = partners_truncated
        result_data["next_partner_offset"] = (
            partner_offset + len(partner_page) if partners_truncated else None
        )
        if partners_truncated:
            result_data["truncated"] = True
            result_data["truncation_note"] = (
                f"Returning {len(partners)} interaction partners from offset "
                f"{partner_offset} of {len(all_partner_entries)} total. Continue "
                f"with partner_offset={partner_offset + len(partner_page)}."
            )

        return {
            "status": "success",
            "data": result_data,
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
                "status": "error",
                "error": "uniprot_accession parameter is required (e.g., 'P04637' for TP53, 'P00533' for EGFR).",
            }

        url = f"{PDBE_KB_BASE_URL}/uniprot/superposition/{acc}"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        if acc not in data:
            return {"status": "error", "error": f"No superposition data for {acc}"}

        segments_data = data[acc]
        segments = []
        segment_offset = max(int(arguments.get("segment_offset") or 0), 0)
        segment_limit = min(max(int(arguments.get("segment_limit") or 10), 1), 100)
        cluster_offset = max(int(arguments.get("cluster_offset") or 0), 0)
        cluster_limit = min(max(int(arguments.get("cluster_limit") or 10), 1), 100)
        member_offset = max(int(arguments.get("member_offset") or 0), 0)
        member_limit = min(max(int(arguments.get("member_limit") or 20), 1), 500)

        segment_page = segments_data[
            segment_offset : segment_offset + segment_limit
        ]
        for seg in segment_page:
            all_clusters = seg.get("clusters", [])
            cluster_page = all_clusters[
                cluster_offset : cluster_offset + cluster_limit
            ]
            cluster_results = []

            for cluster in cluster_page:
                members = []
                representative_member = next(
                    (m for m in cluster if m.get("is_representative", False)), None
                )
                representative = (
                    {
                        "pdb_id": representative_member.get("pdb_id"),
                        "auth_asym_id": representative_member.get("auth_asym_id"),
                        "struct_asym_id": representative_member.get("struct_asym_id"),
                        "entity_id": representative_member.get("entity_id"),
                        "is_representative": True,
                    }
                    if representative_member is not None
                    else None
                )
                member_page = cluster[member_offset : member_offset + member_limit]
                for member in member_page:
                    entry = {
                        "pdb_id": member.get("pdb_id"),
                        "auth_asym_id": member.get("auth_asym_id"),
                        "struct_asym_id": member.get("struct_asym_id"),
                        "entity_id": member.get("entity_id"),
                        "is_representative": member.get("is_representative", False),
                    }
                    members.append(entry)

                members_truncated = member_offset + len(member_page) < len(cluster)
                cluster_results.append(
                    {
                        "representative": representative,
                        "total_members": len(cluster),
                        "member_offset": member_offset,
                        "members_returned": len(member_page),
                        "members_truncated": members_truncated,
                        "next_member_offset": (
                            member_offset + len(member_page)
                            if members_truncated
                            else None
                        ),
                        "members": members,
                    }
                )

            clusters_truncated = (
                cluster_offset + len(cluster_page) < len(all_clusters)
            )
            segments.append(
                {
                    "segment_start": seg.get("segment_start"),
                    "segment_end": seg.get("segment_end"),
                    "num_clusters": len(all_clusters),
                    "cluster_offset": cluster_offset,
                    "clusters_returned": len(cluster_page),
                    "clusters_truncated": clusters_truncated,
                    "next_cluster_offset": (
                        cluster_offset + len(cluster_page)
                        if clusters_truncated
                        else None
                    ),
                    "clusters": cluster_results,
                }
            )

        segments_truncated = segment_offset + len(segment_page) < len(segments_data)

        return {
            "status": "success",
            "data": {
                "uniprot_accession": acc,
                "segments": segments,
                "total_segments": len(segments_data),
                "segment_offset": segment_offset,
                "segments_returned": len(segment_page),
                "segments_truncated": segments_truncated,
                "next_segment_offset": (
                    segment_offset + len(segment_page)
                    if segments_truncated
                    else None
                ),
            },
            "metadata": {
                "source": "PDBe-KB (PDBe Knowledge Base) Graph API",
            },
        }
