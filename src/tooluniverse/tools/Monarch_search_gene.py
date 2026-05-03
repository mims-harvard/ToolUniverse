"""
Monarch_search_gene

Search Monarch Initiative knowledge graph for a gene by symbol or name. Returns HGNC/NCBIGene CUR...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Monarch_search_gene(
    query: str,
    limit: Optional[int] = 10,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search Monarch Initiative knowledge graph for a gene by symbol or name. Returns HGNC/NCBIGene CUR...

    Parameters
    ----------
    query : str
        Gene symbol or name (e.g., 'TP53', 'BRCA1', 'WDR7')
    limit : int
        Number of results to return (default: 10)
    offset : int
        Number of initial entries to skip.
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
        for k, v in {"query": query, "limit": limit, "offset": offset}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Monarch_search_gene",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Monarch_search_gene"]
