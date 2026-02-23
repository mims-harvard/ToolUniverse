"""
OpenFDA_search_device_enforcement

Search the FDA medical device enforcement (recall) database via openFDA. Contains medical device ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OpenFDA_search_device_enforcement(
    search: Optional[str | Any] = None,
    limit: Optional[int | Any] = None,
    count: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search the FDA medical device enforcement (recall) database via openFDA. Contains medical device ...

    Parameters
    ----------
    search : str | Any
        Lucene query for device recalls (e.g., 'classification:"Class I"', 'status:On...
    limit : int | Any
        Maximum number of results (default 5, max 100)
    count : str | Any
        Field to count by (e.g., 'classification', 'status', 'recalling_firm.exact')
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
            "name": "OpenFDA_search_device_enforcement",
            "arguments": {"search": search, "limit": limit, "count": count},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OpenFDA_search_device_enforcement"]
