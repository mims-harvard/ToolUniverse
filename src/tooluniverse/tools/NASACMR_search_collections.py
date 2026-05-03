"""
NASACMR_search_collections

Search NASA's Common Metadata Repository (CMR) for Earth observation datasets and satellite colle...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NASACMR_search_collections(
    keyword: str,
    page_size: Optional[int | Any] = None,
    data_center: Optional[str | Any] = None,
    platform: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search NASA's Common Metadata Repository (CMR) for Earth observation datasets and satellite colle...

    Parameters
    ----------
    keyword : str
        Free-text keyword search. Examples: 'sea surface temperature', 'land cover', ...
    page_size : int | Any
        Number of results to return (default 10, max 2000)
    data_center : str | Any
        Filter by data center short name. Examples: 'NSIDC', 'PODAAC', 'GES_DISC', 'L...
    platform : str | Any
        Filter by satellite/instrument platform. Examples: 'Terra', 'Aqua', 'Landsat-...
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
            "keyword": keyword,
            "page_size": page_size,
            "data_center": data_center,
            "platform": platform,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "NASACMR_search_collections",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["NASACMR_search_collections"]
