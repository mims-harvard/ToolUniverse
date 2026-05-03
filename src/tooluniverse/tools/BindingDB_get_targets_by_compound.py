"""
BindingDB_get_targets_by_compound

Find protein targets for a compound by SMILES structure. Returns proteins with binding affinity d...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def BindingDB_get_targets_by_compound(
    smiles: str,
    similarity_cutoff: Optional[float] = 0.85,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Find protein targets for a compound by SMILES structure. Returns proteins with binding affinity d...

    Parameters
    ----------
    smiles : str
        SMILES structure of compound
    similarity_cutoff : float
        Similarity threshold 0-1 (default: 0.85)
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    list[Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {"smiles": smiles, "similarity_cutoff": similarity_cutoff}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "BindingDB_get_targets_by_compound",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["BindingDB_get_targets_by_compound"]
