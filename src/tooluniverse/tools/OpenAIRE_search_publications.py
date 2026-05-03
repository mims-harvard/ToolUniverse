"""
OpenAIRE_search_publications

Search OpenAIRE Explore for research products including publications, datasets, and software. Ope...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OpenAIRE_search_publications(
    query: str,
    max_results: int,
    type_: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search OpenAIRE Explore for research products including publications, datasets, and software. Ope...

    Parameters
    ----------
    query : str
        Search query for OpenAIRE research products. Use keywords to search across ti...
    max_results : int
        Maximum number of results to return. Default is 10, maximum is 100.
    type_ : str
        Type of research product to search: 'publications', 'datasets', or 'software'...
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
        for k, v in {"query": query, "max_results": max_results, "type": type_}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "OpenAIRE_search_publications",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OpenAIRE_search_publications"]
