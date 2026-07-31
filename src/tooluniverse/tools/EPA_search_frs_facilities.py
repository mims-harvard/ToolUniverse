"""
EPA_search_frs_facilities

Search the EPA Facility Registry Service (FRS) — EPA's integrated registry of regulated facility ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EPA_search_frs_facilities(
    state: str,
    city: Optional[str] = None,
    limit: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search the EPA Facility Registry Service (FRS) — EPA's integrated registry of regulated facility ...

    Parameters
    ----------
    state : str
        2-letter US state code, e.g. 'MA', 'CA'.
    city : str
        Optional city name filter.
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
            "name": "EPA_search_frs_facilities",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["EPA_search_frs_facilities"]
