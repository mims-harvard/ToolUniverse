"""
BMRB_get_entries_by_pdb_id

Find BMRB NMR entries associated with a PDB structure. Returns BMRB entry IDs linked to a given P...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def BMRB_get_entries_by_pdb_id(
    pdb_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Find BMRB NMR entries associated with a PDB structure. Returns BMRB entry IDs linked to a given P...

    Parameters
    ----------
    pdb_id : str
        PDB entry ID (e.g., '1ubq', '1d3z', '2k39')
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
            "name": "BMRB_get_entries_by_pdb_id",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["BMRB_get_entries_by_pdb_id"]
