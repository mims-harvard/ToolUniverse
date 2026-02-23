"""
SIGN_search_guidelines

Search SIGN (Scottish Intercollegiate Guidelines Network) clinical guidelines by keyword. Fetches...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def SIGN_search_guidelines(
    query: str,
    limit: Optional[int] = 10,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search SIGN (Scottish Intercollegiate Guidelines Network) clinical guidelines by keyword. Fetches...

    Parameters
    ----------
    query : str
        Keyword to search in guideline title or clinical topic (e.g., 'cardiac', 'dia...
    limit : int
        Maximum number of guidelines to return (default: 10)
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
            "name": "SIGN_search_guidelines",
            "arguments": {"query": query, "limit": limit},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["SIGN_search_guidelines"]
