"""
NASA_DONKI_get_interplanetary_shocks

Search NASA DONKI for Interplanetary Shock (IPS) events detected at Earth or in the solar wind. I...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NASA_DONKI_get_interplanetary_shocks(
    startDate: Optional[str | Any] = None,
    endDate: Optional[str | Any] = None,
    location: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search NASA DONKI for Interplanetary Shock (IPS) events detected at Earth or in the solar wind. I...

    Parameters
    ----------
    startDate : str | Any
        Start date in YYYY-MM-DD format (e.g., '2024-01-01'). Defaults to 30 days bef...
    endDate : str | Any
        End date in YYYY-MM-DD format (e.g., '2024-03-31'). Defaults to today.
    location : str | Any
        Shock detection location. Options: 'Earth', 'STEREO A', 'STEREO B', 'MESSENGE...
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
            "startDate": startDate,
            "endDate": endDate,
            "location": location,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "NASA_DONKI_get_interplanetary_shocks",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["NASA_DONKI_get_interplanetary_shocks"]
