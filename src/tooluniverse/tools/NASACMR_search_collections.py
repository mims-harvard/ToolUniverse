"""
NASACMR_search_collections

Search NASA CMR for Earth-observation collections. Results use exact one-based CMR pagination: st...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NASACMR_search_collections(
    keyword: str,
    page_size: Optional[int] = 10,
    page: Optional[int] = 1,
    data_center: Optional[str] = None,
    platform: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search NASA CMR for Earth-observation collections. Results use exact one-based CMR pagination: st...

    Parameters
    ----------
    keyword : str
        Free-text keyword search. Examples: 'sea surface temperature', 'land cover', ...
    page_size : int
        Collections per page (default 10, max 2000)
    page : int
        One-based CMR page number. Continue with metadata.next_page.
    data_center : str
        Filter by data center short name. Examples: 'NSIDC', 'PODAAC', 'GES_DISC', 'L...
    platform : str
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
            "page": page,
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
