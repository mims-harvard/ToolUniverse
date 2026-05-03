"""
GO_search_terms

Searches for Gene Ontology (GO) terms by a keyword using the GOlr search engine. Returns GO terms...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GO_search_terms(
    query: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Searches for Gene Ontology (GO) terms by a keyword using the GOlr search engine. Returns GO terms...

    Parameters
    ----------
    query : str
        The keyword to search for, e.g., 'apoptosis' or 'kinase activity'.
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
    _args = {k: v for k, v in {"query": query}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "GO_search_terms",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["GO_search_terms"]
