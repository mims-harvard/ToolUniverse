"""
CxGDisc_get_collection

Get detailed information about a specific CellxGene Discovery collection, including all datasets ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def CxGDisc_get_collection(
    collection_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get detailed information about a specific CellxGene Discovery collection, including all datasets ...

    Parameters
    ----------
    collection_id : str
        Collection UUID from CellxGene Discovery (e.g., '48259aa8-f168-4bf5-b797-af8e...
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
            "name": "CxGDisc_get_collection",
            "arguments": {"collection_id": collection_id},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["CxGDisc_get_collection"]
