"""
BiGG_search

Search BiGG database for models, reactions, metabolites, or genes. Returns matching entries with ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def BiGG_search(
    operation: str,
    query: str,
    search_type: Optional[str] = "reactions",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search BiGG database for models, reactions, metabolites, or genes. Returns matching entries with ...

    Parameters
    ----------
    operation : str
        Operation type
    query : str
        Required: Search term (e.g., 'glucose', 'gapA', 'E. coli')
    search_type : str
        What to search for
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
            "query": query,
            "search_type": search_type,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "BiGG_search",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["BiGG_search"]
