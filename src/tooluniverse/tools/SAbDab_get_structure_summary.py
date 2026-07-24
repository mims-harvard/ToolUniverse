"""
SAbDab_get_structure_summary

Get per-structure curated antibody annotations from SAbDab for a PDB ID. Returns the SAbDab summa...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def SAbDab_get_structure_summary(
    operation: Optional[str] = None,
    pdb_id: Optional[str] = None,
    pdb_code: Optional[str] = None,
    pdb: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get per-structure curated antibody annotations from SAbDab for a PDB ID. Returns the SAbDab summa...

    Parameters
    ----------
    operation : str

    pdb_id : str
        4-character PDB ID of an antibody structure (e.g., '7d6i', '3hfm'). Aliases: ...
    pdb_code : str
        Alias for pdb_id.
    pdb : str
        Alias for pdb_id.
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
            "operation": operation,
            "pdb_id": pdb_id,
            "pdb_code": pdb_code,
            "pdb": pdb,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "SAbDab_get_structure_summary",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["SAbDab_get_structure_summary"]
