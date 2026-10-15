"""
BOLDSystems_search_by_bin

Search BOLD (Barcode of Life Data System) for all DNA barcode records sharing a BIN (Barcode Inde...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def BOLDSystems_search_by_bin(
    bin_id: str,
    limit: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search BOLD (Barcode of Life Data System) for all DNA barcode records sharing a BIN (Barcode Inde...

    Parameters
    ----------
    bin_id : str
        BOLD BIN identifier, e.g. 'BOLD:AAD6819' (the 'BOLD:' prefix is added automat...
    limit : int
        Max records to return, 1-200. Default 30.
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
        k: v for k, v in {"bin_id": bin_id, "limit": limit}.items() if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "BOLDSystems_search_by_bin",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["BOLDSystems_search_by_bin"]
