"""
USGSWater_get_streamflow

Get real-time streamflow (discharge) data from USGS water monitoring stations. Returns instantane...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def USGSWater_get_streamflow(
    sites: str,
    period: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get real-time streamflow (discharge) data from USGS water monitoring stations. Returns instantane...

    Parameters
    ----------
    sites : str
        USGS site number(s), comma-separated (e.g., '01646500' for Potomac River near...
    period : str | Any
        Time period for data in ISO 8601 duration format (e.g., 'PT2H' for 2 hours, '...
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
            "name": "USGSWater_get_streamflow",
            "arguments": {"sites": sites, "period": period},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["USGSWater_get_streamflow"]
