"""
DiseaseSh_get_historical

Get historical COVID-19 time series data for a country or globally from Disease.sh. Returns daily...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def DiseaseSh_get_historical(
    country: Optional[str | Any] = None,
    lastdays: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get historical COVID-19 time series data for a country or globally from Disease.sh. Returns daily...

    Parameters
    ----------
    country : str | Any
        Country name or 'all' for global data. Examples: 'USA', 'India', 'all'. If om...
    lastdays : str | Any
        Number of days of historical data to return. Use a number (e.g., '30') or 'al...
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
            "name": "DiseaseSh_get_historical",
            "arguments": {"country": country, "lastdays": lastdays},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["DiseaseSh_get_historical"]
