"""
PDB_REDO_get_structure_quality

Get re-refined structure quality metrics from PDB-REDO for a given PDB entry. PDB-REDO is a datab...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PDB_REDO_get_structure_quality(
    pdb_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get re-refined structure quality metrics from PDB-REDO for a given PDB entry. PDB-REDO is a datab...

    Parameters
    ----------
    pdb_id : str
        PDB entry ID in lowercase. Examples: '1cbs' (cellular retinoic acid binding p...
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
        {"name": "PDB_REDO_get_structure_quality", "arguments": {"pdb_id": pdb_id}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PDB_REDO_get_structure_quality"]
