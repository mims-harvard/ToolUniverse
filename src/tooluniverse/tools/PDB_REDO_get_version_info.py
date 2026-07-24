"""
PDB_REDO_get_version_info

Get PDB-REDO re-refinement version and provenance metadata for a PDB entry. This is the versions....
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PDB_REDO_get_version_info(
    pdb_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get PDB-REDO re-refinement version and provenance metadata for a PDB entry. This is the versions....

    Parameters
    ----------
    pdb_id : str
        PDB entry ID in lowercase. Examples: '1cbs', '6lu7', '2hhb'. Not all PDB entr...
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
    _args = {k: v for k, v in {"pdb_id": pdb_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "PDB_REDO_get_version_info",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PDB_REDO_get_version_info"]
