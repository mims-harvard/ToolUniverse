"""
DiseaseSh_get_country_stats

Get COVID-19 statistics for a specific country from the Disease.sh API. Returns total and daily c...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def DiseaseSh_get_country_stats(
    country: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get COVID-19 statistics for a specific country from the Disease.sh API. Returns total and daily c...

    Parameters
    ----------
    country : str
        Country name (e.g., 'USA', 'India', 'Brazil'), ISO2 code (e.g., 'US', 'IN'), ...
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
        {"name": "DiseaseSh_get_country_stats", "arguments": {"country": country}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["DiseaseSh_get_country_stats"]
