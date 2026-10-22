"""
PDBe_KB_get_interface_residues

Get protein-protein interaction interface residues for a UniProt protein from PDBe-KB. Results ar...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PDBe_KB_get_interface_residues(
    uniprot_accession: str,
    max_partners: Optional[int] = 60,
    partner_offset: Optional[int] = 0,
    residue_offset: Optional[int] = 0,
    residue_limit: Optional[int] = 30,
    pdb_entry_offset: Optional[int] = 0,
    pdb_entry_limit: Optional[int] = 10,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get protein-protein interaction interface residues for a UniProt protein from PDBe-KB. Results ar...

    Parameters
    ----------
    uniprot_accession : str
        UniProt accession ID for the protein. Examples: 'P04637' (TP53), 'P00533' (EG...
    max_partners : int
        Number of interaction partners to return from partner_offset (default 60).
    partner_offset : int
        Zero-based interaction-partner offset.
    residue_offset : int
        Zero-based interface-residue offset applied within every returned partner.
    residue_limit : int
        Interface residues returned per partner (default 30, maximum 500).
    pdb_entry_offset : int
        Zero-based PDB-entry offset applied within every returned residue.
    pdb_entry_limit : int
        PDB entries returned per residue (default 10, maximum 500).
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    Any
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "uniprot_accession": uniprot_accession,
            "max_partners": max_partners,
            "partner_offset": partner_offset,
            "residue_offset": residue_offset,
            "residue_limit": residue_limit,
            "pdb_entry_offset": pdb_entry_offset,
            "pdb_entry_limit": pdb_entry_limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "PDBe_KB_get_interface_residues",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PDBe_KB_get_interface_residues"]
