"""
health_disparities_get_svi_info

Get information about CDC Social Vulnerability Index (SVI) data. SVI data is typically available ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def health_disparities_get_svi_info(
    year: Optional[int] = None,
    geography: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get information about CDC Social Vulnerability Index (SVI) data. SVI data is typically available ...

    Parameters
    ----------
    year : int
        Optional year to filter SVI data (e.g., 2020, 2018, 2016). SVI is released ev...
    geography : str
        Geographic level: 'county' for county-level, 'tract' for census tract, 'state...
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
    _args = {
        k: v for k, v in {"year": year, "geography": geography}.items() if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "health_disparities_get_svi_info",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["health_disparities_get_svi_info"]
