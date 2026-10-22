"""
PDB_check_alpha_stereochemistry

Check C-alpha orientation in local legacy PDB or public 1UBQ. Reports L/D mirrors, degenerate cen...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PDB_check_alpha_stereochemistry(
    pdb_path: Optional[str] = None,
    pdb_content: Optional[str] = None,
    pdb_id: Optional[str] = None,
    model_index: Optional[int] = None,
    protein_residue_aliases: Optional[dict[str, Any]] = None,
    max_residue_details: Optional[int] = None,
    expected_orientation: Optional[str] = None,
    degenerate_tolerance_A3: Optional[float] = None,
    minimum_normalized_volume: Optional[float] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Check C-alpha orientation in local legacy PDB or public 1UBQ. Reports L/D mirrors, degenerate cen...

    Parameters
    ----------
    pdb_path : str
        Local legacy PDB path; stays local. Exactly one input source.
    pdb_content : str
        Inline legacy PDB coordinates; stays local. Exactly one input source.
    pdb_id : str
        Four-character public RCSB identifier, e.g. 1UBQ; downloads only this public ...
    model_index : int
        Model by file order, default 1. Models are never pooled.
    protein_residue_aliases : dict[str, Any]
        Caller declarations mapping nonstandard protein names to canonical 3-letter a...
    max_residue_details : int
        Bound residue detail lists, default 100. Counts and coordinate sequences stay...
    expected_orientation : str
        Expected C-alpha geometric orientation, default L for natural encoded protein...
    degenerate_tolerance_A3 : float
        Absolute N/CA/C/CB determinant tolerance in A^3 for degenerate centers, defau...
    minimum_normalized_volume : float
        Minimum absolute determinant divided by product of CA-N/CA-C/CA-CB lengths. D...
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
            "pdb_path": pdb_path,
            "pdb_content": pdb_content,
            "pdb_id": pdb_id,
            "model_index": model_index,
            "protein_residue_aliases": protein_residue_aliases,
            "max_residue_details": max_residue_details,
            "expected_orientation": expected_orientation,
            "degenerate_tolerance_A3": degenerate_tolerance_A3,
            "minimum_normalized_volume": minimum_normalized_volume,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "PDB_check_alpha_stereochemistry",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PDB_check_alpha_stereochemistry"]
