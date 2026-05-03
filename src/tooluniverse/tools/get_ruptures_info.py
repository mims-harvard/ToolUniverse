"""
get_ruptures_info

Get comprehensive information about ruptures – change point detection library
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def get_ruptures_info(
    info_type: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get comprehensive information about ruptures – change point detection library

    Parameters
    ----------
    info_type : str
        Type of information to retrieve about ruptures
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    dict[str, Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {k: v for k, v in {"info_type": info_type}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "get_ruptures_info",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["get_ruptures_info"]
