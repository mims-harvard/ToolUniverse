"""
CTIS_search_trials

Search the EU Clinical Trials Information System (CTIS) — the European clinical-trials register u...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def CTIS_search_trials(
    query: str,
    limit: Optional[int] = None,
    page: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search the EU Clinical Trials Information System (CTIS) — the European clinical-trials register u...

    Parameters
    ----------
    query : str
        Free-text search, e.g. 'breast cancer', 'pembrolizumab', 'cystic fibrosis'.
    limit : int
        Results per page (default 10, max 100).
    page : int
        Page number (default 1).
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
        for k, v in {"query": query, "limit": limit, "page": page}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "CTIS_search_trials",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["CTIS_search_trials"]
