"""
NeuroVault_get_collection

Get detailed metadata for a specific NeuroVault neuroimaging collection by its ID. Returns study ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NeuroVault_get_collection(
    collection_id: int,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get detailed metadata for a specific NeuroVault neuroimaging collection by its ID. Returns study ...

    Parameters
    ----------
    collection_id : int
        NeuroVault collection ID number. Examples: 457 (Human Connectome Project), 19...
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
        {
            "name": "NeuroVault_get_collection",
            "arguments": {"collection_id": collection_id},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["NeuroVault_get_collection"]
