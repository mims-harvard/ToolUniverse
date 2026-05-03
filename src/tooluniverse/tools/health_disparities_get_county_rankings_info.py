"""
health_disparities_get_county_rankings_info

Get information about County Health Rankings data. County Health Rankings provides county-level h...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def health_disparities_get_county_rankings_info(
    year: Optional[int] = None,
    state: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get information about County Health Rankings data. County Health Rankings provides county-level h...

    Parameters
    ----------
    year : int
        Optional year for County Health Rankings data
    state : str
        Optional state abbreviation (e.g., 'CA', 'NY') to filter by state
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    dict[str, Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {k: v for k, v in {"year": year, "state": state}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "health_disparities_get_county_rankings_info",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["health_disparities_get_county_rankings_info"]
