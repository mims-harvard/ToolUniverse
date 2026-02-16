"""
UniProtRef_search_keywords

Search the UniProt keyword controlled vocabulary. Keywords are standardized terms used to annotat...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def UniProtRef_search_keywords(
    query: str,
    size: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search the UniProt keyword controlled vocabulary. Keywords are standardized terms used to annotat...

    Parameters
    ----------
    query : str
        Search query for keywords. Examples: 'kinase', 'apoptosis', 'membrane', 'phos...
    size : int
        Maximum number of results to return (default: 10, max: 25).
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
            "name": "UniProtRef_search_keywords",
            "arguments": {"query": query, "size": size},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["UniProtRef_search_keywords"]
