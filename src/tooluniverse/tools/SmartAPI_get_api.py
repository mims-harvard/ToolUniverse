"""
SmartAPI_get_api

Retrieve one SmartAPI registry entry's full metadata: base URL(s), tags, contact, terms of servic...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def SmartAPI_get_api(
    api_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Retrieve one SmartAPI registry entry's full metadata: base URL(s), tags, contact, terms of servic...

    Parameters
    ----------
    api_id : str
        SmartAPI registry id (32-char hash) or slug, e.g. 'myvariant'.
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
    _args = {k: v for k, v in {"api_id": api_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "SmartAPI_get_api",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["SmartAPI_get_api"]
