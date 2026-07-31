"""
EPA_search_tri_facilities

Search EPA Toxics Release Inventory (TRI) facilities by US state (and optional city) via the EPA ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EPA_search_tri_facilities(
    state: str,
    city: Optional[str] = None,
    limit: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search EPA Toxics Release Inventory (TRI) facilities by US state (and optional city) via the EPA ...

    Parameters
    ----------
    state : str
        2-letter US state code, e.g. 'CA', 'TX'.
    city : str
        Optional city name filter, e.g. 'Los Angeles'.
    limit : int
        Max facilities (default 10, max 100).
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
        for k, v in {"state": state, "city": city, "limit": limit}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "EPA_search_tri_facilities",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["EPA_search_tri_facilities"]
