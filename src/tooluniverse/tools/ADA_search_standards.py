"""
ADA_search_standards

Search ADA (American Diabetes Association) guidelines and publications by topic using PubMed. Sea...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ADA_search_standards(
    query: str,
    limit: Optional[int] = 5,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search ADA (American Diabetes Association) guidelines and publications by topic using PubMed. Sea...

    Parameters
    ----------
    query : str
        Search topic (e.g., 'type 2 diabetes insulin therapy', 'gestational diabetes'...
    limit : int
        Maximum number of results to return (default: 5)
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
        {"name": "ADA_search_standards", "arguments": {"query": query, "limit": limit}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ADA_search_standards"]
