# pdbe_sifts_tool.py
"""
PDBe SIFTS Mapping tool for ToolUniverse.

SIFTS (Structure Integration with Function, Taxonomy and Sequences) provides
cross-referencing between PDB structures and UniProt proteins, enabling
structure-based discovery of best available crystal/EM structures for a protein.

API: https://www.ebi.ac.uk/pdbe/api/
No authentication required. Free public access.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

PDBE_API_BASE_URL = "https://www.ebi.ac.uk/pdbe/api"

# Fix-R4B-3: the structure lists were sliced to a hard-coded first 50 with no
# parameter able to reach past it -- P04637 (TP53) has 676 structure-chain
# entries and only the first 50 were obtainable, at any resolution or method.
# `limit`/`offset` make the whole ranked list reachable; DEFAULT_PAGE_SIZE
# preserves the previous default response size for existing callers.
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 500


@register_tool("PDBeSIFTSTool")
class PDBeSIFTSTool(BaseTool):
    """
    PDBe SIFTS Mapping tool for UniProt-PDB cross-referencing.

    Provides ranked best structures for a protein, PDB-to-UniProt chain
    mapping, and comprehensive structure coverage analysis.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "best_structures")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the PDBe SIFTS API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"PDBe SIFTS API timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {"status": "error", "error": "Failed to connect to PDBe SIFTS API"}
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response is not None else None
            if status_code == 404:
                # Fix-R18A-3: a bare "HTTP error: 404" doesn't distinguish
                # a genuinely broken request from PDBe simply having no
                # mapping data of this type for an otherwise-valid entry
                # (confirmed live: PDBeSIFTS_get_scop_mapping 404s for
                # 3k34, which has real PDB/ligand data elsewhere -- SCOP
                # classification just doesn't cover it).
                return {
                    "status": "error",
                    "error": (
                        f"PDBe SIFTS API returned no {self.endpoint} mapping "
                        "for this entry (HTTP 404). This usually means the "
                        "entry exists but has no data of this specific type "
                        "in SIFTS, not that the request itself is invalid."
                    ),
                }
            return {
                "status": "error",
                "error": f"PDBe SIFTS API HTTP error: {status_code}",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error querying PDBe SIFTS API: {str(e)}",
            }

    @staticmethod
    def _page_window(arguments: Dict[str, Any]) -> Dict[str, int]:
        """Resolve the limit/offset window for a truncated result list."""
        raw_limit = arguments.get("limit")
        limit = DEFAULT_PAGE_SIZE if raw_limit in (None, "") else int(raw_limit)
        limit = max(1, min(limit, MAX_PAGE_SIZE))
        offset = max(0, int(arguments.get("offset") or 0))
        return {"limit": limit, "offset": offset}

    @staticmethod
    def _page_note(window: Dict[str, int], total: int, returned: int) -> str:
        """Describe the slice returned, and how to reach the rest of it."""
        if not returned:
            return ""
        first = window["offset"] + 1
        last = window["offset"] + returned
        if last >= total:
            return ""
        return (
            f"Showing {first}-{last} of {total}. Re-run with offset={last} for the "
            f"next page, or raise 'limit' (max {MAX_PAGE_SIZE})."
        )

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint."""
        if self.endpoint == "best_structures":
            return self._get_best_structures(arguments)
        elif self.endpoint == "pdb_to_uniprot":
            return self._get_pdb_to_uniprot(arguments)
        elif self.endpoint == "uniprot_to_pdb":
            return self._get_uniprot_to_pdb(arguments)
        elif self.endpoint == "scop":
            return self._get_scop_mapping(arguments)
        else:
            return {"status": "error", "error": f"Unknown endpoint: {self.endpoint}"}

    def _get_best_structures(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get best PDB structures for a UniProt protein, ranked by coverage and resolution."""
        accession = arguments.get("uniprot_accession", "")
        if not accession:
            return {
                "status": "error",
                "error": "uniprot_accession parameter is required (e.g., P04637)",
            }

        url = f"{PDBE_API_BASE_URL}/mappings/best_structures/{accession}"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        entries = data.get(accession, [])
        window = self._page_window(arguments)

        structures = []
        for e in entries[window["offset"] : window["offset"] + window["limit"]]:
            structures.append(
                {
                    "pdb_id": e.get("pdb_id"),
                    "chain_id": e.get("chain_id"),
                    "uniprot_start": e.get("start"),
                    "uniprot_end": e.get("end"),
                    "resolution": e.get("resolution"),
                    "experimental_method": e.get("experimental_method"),
                    "coverage": e.get("coverage"),
                    "tax_id": e.get("tax_id"),
                }
            )

        result = {
            "status": "success",
            "data": {
                "uniprot_accession": accession,
                "structures": structures,
                "total_structures": len(entries),
                "returned_structures": len(structures),
                "offset": window["offset"],
            },
            "metadata": {
                "source": "PDBe SIFTS - Best Structures",
                "accession": accession,
            },
        }
        note = self._page_note(window, len(entries), len(structures))
        if note:
            result["data"]["note"] = note
        return result

    def _get_pdb_to_uniprot(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Map PDB entry chains to UniProt accessions."""
        pdb_id = arguments.get("pdb_id", "")
        if not pdb_id:
            return {
                "status": "error",
                "error": "pdb_id parameter is required (e.g., 1tup)",
            }

        pdb_id = pdb_id.lower()
        url = f"{PDBE_API_BASE_URL}/mappings/uniprot/{pdb_id}"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        entry_data = data.get(pdb_id, {})
        uniprot_data = entry_data.get("UniProt", {})

        proteins = []
        for acc, info in uniprot_data.items():
            all_mappings = info.get("mappings", [])
            chain_mappings = []
            for m in all_mappings[:20]:
                chain_mappings.append(
                    {
                        "chain_id": m.get("chain_id"),
                        "pdb_start": m.get("start", {}).get("residue_number"),
                        "pdb_end": m.get("end", {}).get("residue_number"),
                        "uniprot_start": m.get("unp_start"),
                        "uniprot_end": m.get("unp_end"),
                    }
                )

            # Fix-R4B-3: this 20-mapping truncation was entirely silent --
            # `total_proteins` counts proteins, not mappings, so a viral or
            # ribosomal entry with dozens of chains per accession looked
            # complete at 20. Report the real count alongside the slice.
            proteins.append(
                {
                    "uniprot_accession": acc,
                    "name": info.get("identifier"),
                    "chain_mappings": chain_mappings,
                    "total_chain_mappings": len(all_mappings),
                    "chain_mappings_truncated": len(all_mappings) > len(chain_mappings),
                }
            )

        return {
            "status": "success",
            "data": {
                "pdb_id": pdb_id,
                "proteins": proteins,
                "total_proteins": len(proteins),
            },
            "metadata": {
                "source": "PDBe SIFTS - PDB to UniProt Mapping",
                "pdb_id": pdb_id,
            },
        }

    def _get_scop_mapping(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get SCOP structural classification mapping for a PDB entry.

        SCOP (Structural Classification of Proteins) hierarchy: class > fold >
        superfamily > family, with per-chain residue-range mappings.
        """
        pdb_id = arguments.get("pdb_id", "")
        if not pdb_id:
            return {
                "status": "error",
                "error": "pdb_id parameter is required (e.g., 1cbs)",
            }

        pdb_id = pdb_id.lower()
        url = f"{PDBE_API_BASE_URL}/mappings/scop/{pdb_id}"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        scop_data = data.get(pdb_id, {}).get("SCOP", {})

        domains = []
        for sunid, info in scop_data.items():
            class_info = info.get("class", {}) or {}
            fold_info = info.get("fold", {}) or {}
            superfamily_info = info.get("superfamily", {}) or {}

            mappings = []
            for m in info.get("mappings", []):
                start = m.get("start", {}) or {}
                end = m.get("end", {}) or {}
                mappings.append(
                    {
                        "chain_id": m.get("chain_id"),
                        "struct_asym_id": m.get("struct_asym_id"),
                        "entity_id": m.get("entity_id"),
                        "scop_id": m.get("scop_id"),
                        "start_residue": start.get("residue_number"),
                        "end_residue": end.get("residue_number"),
                        "start_author_residue": start.get("author_residue_number"),
                        "end_author_residue": end.get("author_residue_number"),
                    }
                )

            domains.append(
                {
                    "scop_sunid": sunid,
                    "sccs": info.get("sccs"),
                    "description": info.get("description"),
                    "identifier": info.get("identifier"),
                    "class": class_info.get("description"),
                    "class_sunid": class_info.get("sunid"),
                    "fold": fold_info.get("description"),
                    "fold_sunid": fold_info.get("sunid"),
                    "superfamily": superfamily_info.get("description"),
                    "superfamily_sunid": superfamily_info.get("sunid"),
                    "mappings": mappings,
                }
            )

        return {
            "status": "success",
            "data": {
                "pdb_id": pdb_id,
                "scop_domains": domains,
                "total_domains": len(domains),
            },
            "metadata": {
                "source": "PDBe SIFTS - SCOP Mapping",
                "pdb_id": pdb_id,
            },
        }

    def _get_uniprot_to_pdb(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get all PDB entries covering a UniProt protein."""
        accession = arguments.get("uniprot_accession", "")
        if not accession:
            return {
                "status": "error",
                "error": "uniprot_accession parameter is required (e.g., P04637)",
            }

        # Use best_structures endpoint which returns all PDB structures
        url = f"{PDBE_API_BASE_URL}/mappings/best_structures/{accession}"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        entries = data.get(accession, [])

        # Group by PDB ID to show unique structures
        pdb_entries = {}
        for e in entries:
            pdb_id = e.get("pdb_id", "")
            if pdb_id not in pdb_entries:
                pdb_entries[pdb_id] = {
                    "pdb_id": pdb_id,
                    "resolution": e.get("resolution"),
                    "experimental_method": e.get("experimental_method"),
                    "chains": [],
                }
            pdb_entries[pdb_id]["chains"].append(
                {
                    "chain_id": e.get("chain_id"),
                    "uniprot_start": e.get("start"),
                    "uniprot_end": e.get("end"),
                    "coverage": e.get("coverage"),
                }
            )

        # Sort by resolution (best first)
        sorted_entries = sorted(
            pdb_entries.values(),
            key=lambda x: x.get("resolution") or 999,
        )

        window = self._page_window(arguments)
        page = sorted_entries[window["offset"] : window["offset"] + window["limit"]]

        result = {
            "status": "success",
            "data": {
                "uniprot_accession": accession,
                "pdb_entries": page,
                "total_pdb_entries": len(pdb_entries),
                "returned_pdb_entries": len(page),
                "offset": window["offset"],
                "total_chain_mappings": len(entries),
            },
            "metadata": {
                "source": "PDBe SIFTS - UniProt to PDB Mapping",
                "accession": accession,
            },
        }
        note = self._page_note(window, len(pdb_entries), len(page))
        if note:
            result["data"]["note"] = note
        return result
