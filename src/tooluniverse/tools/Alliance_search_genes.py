"""
Alliance_search_genes

Search for genes across all model organisms in the Alliance of Genome Resources. Searches by gene...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Alliance_search_genes(
    query: str,
    limit: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search for genes across all model organisms in the Alliance of Genome Resources. Searches by gene...

    Parameters
    ----------
    query : str
        Gene name, symbol, or keyword to search for. Examples: 'insulin', 'tumor prot...
    limit : int
        Maximum number of results to return (1-50). Default: 10.
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
            "name": "Alliance_search_genes",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Alliance_search_genes"]
