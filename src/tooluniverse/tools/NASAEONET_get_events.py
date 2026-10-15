"""
NASAEONET_get_events

Get natural event data from NASA Earth Observatory Natural Event Tracker (EONET). EONET tracks on...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NASAEONET_get_events(
    status: Optional[str] = None,
    category: Optional[str] = None,
    limit: Optional[int] = None,
    days: Optional[int] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    bbox: Optional[str] = None,
    source: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get natural event data from NASA Earth Observatory Natural Event Tracker (EONET). EONET tracks on...

    Parameters
    ----------
    status : str
        Event status: 'open' (ongoing events) or 'closed' (past events). Default: both
    category : str
        Filter by event category. Values: 'wildfires', 'severeStorms', 'volcanoes', '...
    limit : int
        Maximum number of events to return (default 10, max 1000)
    days : int
        Return events in the last N days. Example: 7 for last week. Ignored if start/...
    start : str
        Filter events starting from this date (YYYY-MM-DD). Example: '2024-01-01'
    end : str
        Filter events up to this date (YYYY-MM-DD). Example: '2024-12-31'
    bbox : str
        Bounding box filter: 'minLon,minLat,maxLon,maxLat'. Example: '-120,30,-100,50...
    source : str
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

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "status": status,
            "category": category,
            "limit": limit,
            "days": days,
            "start": start,
            "end": end,
            "bbox": bbox,
            "source": source,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "NASAEONET_get_events",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["NASAEONET_get_events"]
