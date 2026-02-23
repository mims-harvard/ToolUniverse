"""
NWS_get_active_alerts

Get active weather alerts from the National Weather Service. Can be filtered by US state/territor...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NWS_get_active_alerts(
    area: Optional[str | Any] = None,
    severity: Optional[str | Any] = None,
    limit: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get active weather alerts from the National Weather Service. Can be filtered by US state/territor...

    Parameters
    ----------
    area : str | Any
        US state/territory abbreviation to filter by (e.g., 'CA', 'TX', 'NY'). If not...
    severity : str | Any
        Filter by severity: Extreme, Severe, Moderate, Minor, Unknown
    limit : int | Any
        Maximum number of alerts to return (default: 50)
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
            "name": "NWS_get_active_alerts",
            "arguments": {"area": area, "severity": severity, "limit": limit},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["NWS_get_active_alerts"]
