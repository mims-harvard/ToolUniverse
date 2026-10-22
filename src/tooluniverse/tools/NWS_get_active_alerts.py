"""
NWS_get_active_alerts

Get active National Weather Service alerts with exact local offset pagination. NWS does not recog...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NWS_get_active_alerts(
    area: Optional[str] = None,
    severity: Optional[str] = None,
    limit: Optional[int] = 50,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get active National Weather Service alerts with exact local offset pagination. NWS does not recog...

    Parameters
    ----------
    area : str
        US state/territory abbreviation to filter by (e.g., 'CA', 'TX', 'NY'). If not...
    severity : str
        Filter by severity: Extreme, Severe, Moderate, Minor, Unknown
    limit : int
        Alerts per local page (default 50, max 500). Not sent to NWS.
    offset : int
        Zero-based offset within the complete filtered active-alert set. Continue wit...
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
            "area": area,
            "severity": severity,
            "limit": limit,
            "offset": offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "NWS_get_active_alerts",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["NWS_get_active_alerts"]
