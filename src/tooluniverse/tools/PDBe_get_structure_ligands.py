"""
PDBe_get_structure_ligands

Get ligands (drug-like molecules, cofactors, ions) bound in a PDB structure. Ligands and annotati...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PDBe_get_structure_ligands(
    pdb_id: str,
    ligand_offset: Optional[int] = 0,
    ligand_limit: Optional[int] = 50,
    annotation_offset: Optional[int] = 0,
    annotation_limit: Optional[int] = 5,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get ligands (drug-like molecules, cofactors, ions) bound in a PDB structure. Ligands and annotati...

    Parameters
    ----------
    pdb_id : str
        PDB entry ID (4-character code). Examples: '4hhb' (hemoglobin), '3ert' (estro...
    ligand_offset : int
        Zero-based ligand offset.
    ligand_limit : int
        Ligands returned per page (default 50, maximum 500).
    annotation_offset : int
        Zero-based annotation offset applied within every returned ligand.
    annotation_limit : int
        Annotations returned per ligand (default 5, maximum 500).
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
            "pdb_id": pdb_id,
            "ligand_offset": ligand_offset,
            "ligand_limit": ligand_limit,
            "annotation_offset": annotation_offset,
            "annotation_limit": annotation_limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "PDBe_get_structure_ligands",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PDBe_get_structure_ligands"]
