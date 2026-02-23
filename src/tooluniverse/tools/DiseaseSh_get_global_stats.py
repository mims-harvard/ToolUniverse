"""
DiseaseSh_get_global_stats

Get global COVID-19 statistics from the Disease.sh API. Returns worldwide totals for confirmed ca...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def DiseaseSh_get_global_stats(
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get global COVID-19 statistics from the Disease.sh API. Returns worldwide totals for confirmed ca...

    Parameters
    ----------
    No parameters
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
        {"name": "DiseaseSh_get_global_stats", "arguments": {}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["DiseaseSh_get_global_stats"]
