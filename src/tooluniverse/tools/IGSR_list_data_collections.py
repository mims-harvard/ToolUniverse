"""
IGSR_list_data_collections

List available data collections from the International Genome Sample Resource (IGSR). Data collec...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def IGSR_list_data_collections(
    operation: Optional[str] = "list_data_collections",
    limit: Optional[int] = 50,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    List available data collections from the International Genome Sample Resource (IGSR). Data collec...

    Parameters
    ----------
    operation : str
        Operation type (fixed: list_data_collections).
    limit : int
        Maximum number of results to return.
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
        for k, v in {"operation": operation, "limit": limit}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "IGSR_list_data_collections",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["IGSR_list_data_collections"]
