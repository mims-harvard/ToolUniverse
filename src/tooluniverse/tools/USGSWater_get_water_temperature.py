"""
USGSWater_get_water_temperature

Get recent water temperature readings from USGS monitoring stations, in degrees Celsius, with sit...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def USGSWater_get_water_temperature(
    sites: str,
    period: Optional[str] = None,
    max_values: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Get recent water temperature readings from USGS monitoring stations, in degrees Celsius, with sit...

    Parameters
    ----------
    sites : str
        USGS site number(s), comma-separated, up to 25 (e.g. '01646500' for the Potom...
    period : str
        How far back from now, as an ISO 8601 duration (e.g. 'PT2H' for 2 hours, 'P1D...
    max_values : int
        Max values per site, newest kept, 1-10000 (shared across a site's sensors whe...
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    list[Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {"sites": sites, "period": period, "max_values": max_values}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "USGSWater_get_water_temperature",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["USGSWater_get_water_temperature"]
