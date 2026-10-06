"""
PDB_inspect_structure

Inspect legacy PDB from local text/path or public ID (1UBQ). Reports chains, coordinate sequences...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PDB_inspect_structure(
    pdb_path: Optional[str] = None,
    pdb_content: Optional[str] = None,
    pdb_id: Optional[str] = None,
    model_index: Optional[int] = None,
    expected_chain_lengths: Optional[dict[str, Any]] = None,
    glycan_residue_names: Optional[list[str]] = None,
    protein_residue_aliases: Optional[dict[str, Any]] = None,
    max_residue_details: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Inspect legacy PDB from local text/path or public ID (1UBQ). Reports chains, coordinate sequences...

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
    expected_chain_lengths : dict[str, Any]
        Expected exact protein-chain lengths, e.g. {"A":76}; mismatch is reported.
    glycan_residue_names : list[str]
        Additional caller-declared glycan residue names, including GLYCAM labels. Cou...
    protein_residue_aliases : dict[str, Any]
        Caller declarations mapping nonstandard protein names to canonical 3-letter a...
    max_residue_details : int
        Bound residue detail lists, default 100. Counts and coordinate sequences stay...
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
            "expected_chain_lengths": expected_chain_lengths,
            "glycan_residue_names": glycan_residue_names,
            "protein_residue_aliases": protein_residue_aliases,
            "max_residue_details": max_residue_details,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "PDB_inspect_structure",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PDB_inspect_structure"]
