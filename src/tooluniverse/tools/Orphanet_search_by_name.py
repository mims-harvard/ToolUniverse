"""
Orphanet_search_by_name

Search for rare diseases by exact or partial name match in Orphanet. More precise than keyword se...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Orphanet_search_by_name(
    operation: Optional[str] = None,
    name: Optional[str] = None,
    exact: Optional[bool] = False,
    lang: Optional[str] = "en",
    limit: Optional[int] = None,
    query: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search for rare diseases by exact or partial name match in Orphanet. More precise than keyword se...

    Parameters
    ----------
    operation : str
        Operation type (fixed: search_by_name)
    name : str
        Disease name to search (e.g., 'Marfan syndrome')
    exact : bool
        If true, match exact name only. Default: false
    lang : str
        Language code (default: en)
    limit : int
        Maximum number of results to return (default: 20, max: 200)
    query : str
        Alias for name. Disease name to search for in Orphanet.
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
        k: v
        for k, v in {
            "operation": operation,
            "name": name,
            "exact": exact,
            "lang": lang,
            "limit": limit,
            "query": query,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Orphanet_search_by_name",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Orphanet_search_by_name"]
