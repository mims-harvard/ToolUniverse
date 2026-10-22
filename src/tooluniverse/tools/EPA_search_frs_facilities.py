"""
EPA_search_frs_facilities

Search EPA Facility Registry Service sites by US state and optional city. Results use native Envi...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EPA_search_frs_facilities(
    state: str,
    city: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search EPA Facility Registry Service sites by US state and optional city. Results use native Envi...

    Parameters
    ----------
    state : str
        2-letter US state code, e.g. 'MA', 'CA'.
    city : str
        Optional city name filter.
    limit : int
        Max facilities per page (default 10, max 100).
    offset : int
        Zero-based row offset; continue with metadata.next_offset.
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
        for k, v in {
            "state": state,
            "city": city,
            "limit": limit,
            "offset": offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "EPA_search_frs_facilities",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["EPA_search_frs_facilities"]
