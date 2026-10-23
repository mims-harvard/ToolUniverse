"""
Bgee_search_genes

Search for genes in the Bgee comparative gene expression database across 29+ animal species. Sear...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Bgee_search_genes(
    query: str,
    species_id: Optional[str] = None,
    limit: Optional[int] = 20,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search for genes in the Bgee comparative gene expression database across 29+ animal species. Sear...

    Parameters
    ----------
    query : str
        Gene name, symbol, or description to search for. Examples: 'TP53', 'insulin',...
    species_id : str
        Optional NCBI taxonomy ID used by Bgee to restrict the search to one species,...
    limit : int
        Maximum number of gene matches to return in this page.
    offset : int
        Zero-based result offset within Bgee's first 10,000 accessible matches. Use m...
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
    _args = {
        k: v
        for k, v in {
            "query": query,
            "species_id": species_id,
            "limit": limit,
            "offset": offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Bgee_search_genes",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Bgee_search_genes"]
