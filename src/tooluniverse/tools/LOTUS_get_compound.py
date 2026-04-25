"""
LOTUS_get_compound

Get detailed information about a specific natural product from LOTUS by its internal compound ID....
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def LOTUS_get_compound(
    compound_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get detailed information about a specific natural product from LOTUS by its internal compound ID....

    Parameters
    ----------
    compound_id : str
        LOTUS internal compound ID (MongoDB ObjectId, e.g., '604b8da112e4996162764b83...
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
    _args = {k: v for k, v in {
        "compound_id": compound_id
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "LOTUS_get_compound",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["LOTUS_get_compound"]
