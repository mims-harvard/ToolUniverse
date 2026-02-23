"""
NASAEONET_get_events

Get natural event data from NASA Earth Observatory Natural Event Tracker (EONET). EONET tracks on...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NASAEONET_get_events(
    status: Optional[str | Any] = None,
    category: Optional[str | Any] = None,
    limit: Optional[int | Any] = None,
    days: Optional[int | Any] = None,
    start: Optional[str | Any] = None,
    end: Optional[str | Any] = None,
    bbox: Optional[str | Any] = None,
    source: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get natural event data from NASA Earth Observatory Natural Event Tracker (EONET). EONET tracks on...

    Parameters
    ----------
    status : str | Any
        Event status: 'open' (ongoing events) or 'closed' (past events). Default: both
    category : str | Any
        Filter by event category. Values: 'wildfires', 'severeStorms', 'volcanoes', '...
    limit : int | Any
        Maximum number of events to return (default 10, max 1000)
    days : int | Any
        Return events in the last N days. Example: 7 for last week. Ignored if start/...
    start : str | Any
        Filter events starting from this date (YYYY-MM-DD). Example: '2024-01-01'
    end : str | Any
        Filter events up to this date (YYYY-MM-DD). Example: '2024-12-31'
    bbox : str | Any
        Bounding box filter: 'minLon,minLat,maxLon,maxLat'. Example: '-120,30,-100,50...
    source : str | Any
        Filter by data source. Examples: 'GDACS', 'InciWeb', 'IRWIN'
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
            "name": "NASAEONET_get_events",
            "arguments": {
                "status": status,
                "category": category,
                "limit": limit,
                "days": days,
                "start": start,
                "end": end,
                "bbox": bbox,
                "source": source,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["NASAEONET_get_events"]
