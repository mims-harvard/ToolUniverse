"""
OSF_search_preprints

Search OSF (Open Science Framework) Preprints for research preprints and working papers. OSF Prep...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OSF_search_preprints(
    query: str,
    max_results: Optional[int] = 10,
    provider: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Search OSF (Open Science Framework) Preprints for research preprints and working papers. OSF Prep...

    Parameters
    ----------
    query : str
        Search query for OSF preprints. Use keywords to search across titles and abst...
    max_results : int
        Maximum number of results to return. Default is 10, maximum is 100.
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
    list[Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "query": query,
            "max_results": max_results,
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
