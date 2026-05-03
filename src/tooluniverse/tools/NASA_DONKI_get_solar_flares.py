"""
NASA_DONKI_get_solar_flares

Search NASA DONKI for Solar Flare (FLR) events. Returns flare observations including class (C/M/X...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NASA_DONKI_get_solar_flares(
    startDate: Optional[str | Any] = None,
    endDate: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search NASA DONKI for Solar Flare (FLR) events. Returns flare observations including class (C/M/X...

    Parameters
    ----------
    startDate : str | Any
        Start date in YYYY-MM-DD format (e.g., '2024-01-01'). Defaults to 30 days bef...
    endDate : str | Any
        End date in YYYY-MM-DD format (e.g., '2024-01-31'). Defaults to today.
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
        for k, v in {"startDate": startDate, "endDate": endDate}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "NASA_DONKI_get_solar_flares",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["NASA_DONKI_get_solar_flares"]
