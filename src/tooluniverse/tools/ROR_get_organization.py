"""
ROR_get_organization

Get detailed metadata for a specific research organization by its ROR ID. Returns comprehensive i...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ROR_get_organization(
    ror_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get detailed metadata for a specific research organization by its ROR ID. Returns comprehensive i...

    Parameters
    ----------
    ror_id : str
        ROR identifier. Can be the short ID (e.g., '042nb2s44') or full URL (e.g., 'h...
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
        {"name": "ROR_get_organization", "arguments": {"ror_id": ror_id}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ROR_get_organization"]
