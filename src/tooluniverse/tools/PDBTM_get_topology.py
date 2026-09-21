"""
PDBTM_get_topology

Retrieve structure-derived transmembrane classification for one PDB entry from PDBTM: per-chain t...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PDBTM_get_topology(
    pdb_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Retrieve structure-derived transmembrane classification for one PDB entry from PDBTM: per-chain t...

    Parameters
    ----------
    pdb_id : str
        4-character PDB identifier, e.g. '2por', '1prc'.
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
            "name": "PDBTM_get_topology",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PDBTM_get_topology"]
