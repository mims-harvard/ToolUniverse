"""
OSF_search_preprints

Search one field (title by default, or description) in OSF Preprints across OSF, PsyArXiv, SocArX...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OSF_search_preprints(
    query: str,
    max_results: Optional[int] = 10,
    page: Optional[int] = 1,
    search_field: Optional[str] = "title",
    provider: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search one field (title by default, or description) in OSF Preprints across OSF, PsyArXiv, SocArX...

    Parameters
    ----------
    query : str
        Search query for OSF preprints. Use keywords to search across titles and abst...
    max_results : int
        Maximum number of results to return. Default is 10, maximum is 100.
    page : int
        One-based result page. OSF uses the bare page parameter; continue with metada...
    search_field : str
        Field to search. OSF exposes separate title and description filters rather th...
    provider : str
        Optional preprint provider filter (e.g., 'osf', 'psyarxiv', 'socarxiv'). If n...
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
            "query": query,
            "max_results": max_results,
            "page": page,
            "search_field": search_field,
            "provider": provider,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "OSF_search_preprints",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OSF_search_preprints"]
