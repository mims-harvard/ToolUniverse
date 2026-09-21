"""
Planteome_search_terms

Search Planteome (a Global Core Biodata Resource) for plant ontology terms by keyword, across the...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Planteome_search_terms(
    query: str,
    limit: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search Planteome (a Global Core Biodata Resource) for plant ontology terms by keyword, across the...

    Parameters
    ----------
    query : str
        Keyword or phrase, e.g. 'pollen development'.
    limit : int
        Max terms to return, 1-100. Default 20.
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
            "name": "Planteome_search_terms",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Planteome_search_terms"]
