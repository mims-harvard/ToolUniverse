"""
CTIS_search_trials

Search EU CTIS with strict, recoverable one-based pagination. Returns exact total_records plus ha...
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
    Search EU CTIS with strict, recoverable one-based pagination. Returns exact total_records plus ha...

    Parameters
    ----------
    query : str
        Free-text search, e.g. 'breast cancer', 'pembrolizumab', 'cystic fibrosis'.
    limit : int
        Results per page, 1-100. Defaults to 10; invalid values are rejected rather t...
    page : int
        One-based CTIS page number. Defaults to 1; use metadata.next_page while metad...
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
