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

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {k: v for k, v in {
        "sites": sites,
                "period": period
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "USGSWater_get_streamflow",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["USGSWater_get_streamflow"]
