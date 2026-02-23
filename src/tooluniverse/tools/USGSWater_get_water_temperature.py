"""
USGSWater_get_water_temperature

Get real-time water temperature data from USGS monitoring stations. Returns water temperature in ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def USGSWater_get_water_temperature(
    sites: str,
    period: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get real-time water temperature data from USGS monitoring stations. Returns water temperature in ...

    Parameters
    ----------
    sites : str
        USGS site number(s), comma-separated
    period : str | Any
        Time period in ISO 8601 format (e.g., 'PT2H', 'P1D', 'P7D'). Default: 'P1D'
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
            "name": "USGSWater_get_water_temperature",
            "arguments": {"sites": sites, "period": period},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["USGSWater_get_water_temperature"]
