"""
NWS_get_forecast

Get the 7-day weather forecast for a National Weather Service grid point. You need the gridId, gr...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NWS_get_forecast(
    gridId: str,
    gridX: int,
    gridY: int,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get the 7-day weather forecast for a National Weather Service grid point. You need the gridId, gr...

    Parameters
    ----------
    gridId : str
        NWS grid office identifier (e.g., 'LWX' for Washington DC area)
    gridX : int
        Grid X coordinate from point metadata
    gridY : int
        Grid Y coordinate from point metadata
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
        for k, v in {"gridId": gridId, "gridX": gridX, "gridY": gridY}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "NWS_get_forecast",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["NWS_get_forecast"]
