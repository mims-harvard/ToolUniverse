"""
MeSH_search_descriptors

Search MeSH (Medical Subject Headings) descriptors by label. MeSH is NLM's controlled vocabulary ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MeSH_search_descriptors(
    query: str,
    match_: Optional[str | Any] = None,
    limit: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search MeSH (Medical Subject Headings) descriptors by label. MeSH is NLM's controlled vocabulary ...

    Parameters
    ----------
    query : str
        Descriptor label to search for. Examples: 'Neoplasms', 'Diabetes Mellitus', '...
    match_ : str | Any
        Match type: 'exact' for exact match, 'contains' for partial match (default), ...
    limit : int | Any
        Maximum number of results (default: 20, max: 50).
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
        for k, v in {"query": query, "match": match_, "limit": limit}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "MeSH_search_descriptors",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MeSH_search_descriptors"]
