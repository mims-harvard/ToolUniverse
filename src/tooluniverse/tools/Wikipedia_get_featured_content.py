"""
Wikipedia_get_featured_content

Get Wikipedia's featured content for a specific date including the featured article of the day, m...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Wikipedia_get_featured_content(
    year: int,
    month: int,
    day: int,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get Wikipedia's featured content for a specific date including the featured article of the day, m...

    Parameters
    ----------
    year : int
        Year. Examples: 2023, 2024
    month : int
        Month number (1-12). Examples: 1, 6, 12
    day : int
        Day of month (1-31). Examples: 1, 15, 25
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
            "name": "Wikipedia_get_featured_content",
            "arguments": {"year": year, "month": month, "day": day},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Wikipedia_get_featured_content"]
