"""
JPLHorizons_get_body_data

Get physical and orbital data for a solar system body from the JPL Horizons system. Returns mass,...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def JPLHorizons_get_body_data(
    COMMAND: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get physical and orbital data for a solar system body from the JPL Horizons system. Returns mass,...

    Parameters
    ----------
    COMMAND : str
        JPL Horizons body ID. Planets: '199' (Mercury), '299' (Venus), '399' (Earth),...
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
    _args = {k: v for k, v in {"COMMAND": COMMAND}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "JPLHorizons_get_body_data",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["JPLHorizons_get_body_data"]
