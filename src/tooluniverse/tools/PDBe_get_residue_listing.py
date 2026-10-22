"""
PDBe_get_residue_listing

Get per-residue information for a PDB structure, optionally filtered by chain. Molecules, chains ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PDBe_get_residue_listing(
    pdb_id: str,
    chain_id: Optional[str] = None,
    molecule_offset: Optional[int] = 0,
    molecule_limit: Optional[int] = 10,
    chain_offset: Optional[int] = 0,
    chain_limit: Optional[int] = 5,
    residue_offset: Optional[int] = 0,
    residue_limit: Optional[int] = 30,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get per-residue information for a PDB structure, optionally filtered by chain. Molecules, chains ...

    Parameters
    ----------
    pdb_id : str
        PDB entry ID (4-character code). Examples: '4hhb', '3ert', '1tup', '6lu7'. Ca...
    chain_id : str
        Optional chain ID to filter (e.g., 'A', 'B'). If not provided, all chains are...
    molecule_offset : int
        Zero-based molecule offset.
    molecule_limit : int
        Molecules returned per page (default 10, maximum 500).
    chain_offset : int
        Zero-based chain offset applied within every returned molecule.
    chain_limit : int
        Chains returned per molecule (default 5, maximum 500).
    residue_offset : int
        Zero-based residue offset applied within every returned chain.
    residue_limit : int
        Residues returned per chain (default 30, maximum 5000).
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
            "chain_id": chain_id,
            "molecule_offset": molecule_offset,
            "molecule_limit": molecule_limit,
            "chain_offset": chain_offset,
            "chain_limit": chain_limit,
            "residue_offset": residue_offset,
            "residue_limit": residue_limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "PDBe_get_residue_listing",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PDBe_get_residue_listing"]
