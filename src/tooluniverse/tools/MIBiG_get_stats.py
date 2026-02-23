"""
MIBiG_get_stats

Get summary statistics from the MIBiG biosynthetic gene cluster repository. Returns total BGC cou...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MIBiG_get_stats(
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get summary statistics from the MIBiG biosynthetic gene cluster repository. Returns total BGC cou...

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
        {"name": "MIBiG_get_stats", "arguments": {}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MIBiG_get_stats"]
