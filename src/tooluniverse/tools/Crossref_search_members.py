"""
Crossref_search_members

Search Crossref members (publishers / depositing organizations) by name. Returns each member's nu...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Crossref_search_members(
    query: str,
    limit: Optional[int] = 20,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search Crossref members (publishers / depositing organizations) by name. Returns each member's nu...

    Parameters
    ----------
    query : str
        Publisher / member name to search (e.g., 'plos', 'elsevier', 'springer', 'wil...
    limit : int
        Maximum number of members to return. Max 100 per request.
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
    _args = {k: v for k, v in {"query": query, "limit": limit}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "Crossref_search_members",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Crossref_search_members"]
