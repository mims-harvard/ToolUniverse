"""
PDBe_get_structure_ligands

Get all ligands (drug-like molecules, cofactors, ions) bound in a PDB crystal structure. Returns ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PDBe_get_structure_ligands(
    pdb_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get all ligands (drug-like molecules, cofactors, ions) bound in a PDB crystal structure. Returns ...

    Parameters
    ----------
    pdb_id : str
        PDB entry ID (4-character code). Examples: '4hhb' (hemoglobin), '3ert' (estro...
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

    return get_shared_client().run_one_function(
        {"name": "PDBe_get_structure_ligands", "arguments": {"pdb_id": pdb_id}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PDBe_get_structure_ligands"]
