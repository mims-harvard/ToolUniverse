"""
PDBe_KB_get_ligand_sites

Get ligand binding site residues for a UniProt protein from PDBe-KB. Returns all known ligands th...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PDBe_KB_get_ligand_sites(
    uniprot_accession: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get ligand binding site residues for a UniProt protein from PDBe-KB. Returns all known ligands th...

    Parameters
    ----------
    uniprot_accession : str
        UniProt accession ID for the protein. Examples: 'P04637' (TP53), 'P00533' (EG...
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
        for k, v in {"uniprot_accession": uniprot_accession}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "PDBe_KB_get_ligand_sites",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PDBe_KB_get_ligand_sites"]
