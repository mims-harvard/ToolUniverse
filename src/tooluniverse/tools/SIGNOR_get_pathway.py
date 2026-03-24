"""
SIGNOR_get_pathway

Get all signaling interactions in a specific SIGNOR curated pathway. Returns the network of causa...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def SIGNOR_get_pathway(
    pathway_id: str,
    limit: Optional[int] = 100,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Get all signaling interactions in a specific SIGNOR curated pathway. Returns the network of causa...

    Parameters
    ----------
    pathway_id : str
        SIGNOR pathway identifier (e.g., 'SIGNOR-AD' for Alzheimer, 'SIGNOR-AML' for ...
    limit : int
        Maximum number of interactions to return.
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
        for k, v in {"pathway_id": pathway_id, "limit": limit}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "SIGNOR_get_pathway",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["SIGNOR_get_pathway"]
