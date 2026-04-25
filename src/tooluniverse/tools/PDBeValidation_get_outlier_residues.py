"""
PDBeValidation_get_outlier_residues

Get residue-level validation outliers for a PDB structure from PDBe. Identifies specific residues...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PDBeValidation_get_outlier_residues(
    pdb_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get residue-level validation outliers for a PDB structure from PDBe. Identifies specific residues...

    Parameters
    ----------
    pdb_id : str
        PDB identifier (4-character code). Case-insensitive. Examples: '4hhb', '1tup'...
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
    _args = {k: v for k, v in {
        "pdb_id": pdb_id
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "PDBeValidation_get_outlier_residues",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["PDBeValidation_get_outlier_residues"]
