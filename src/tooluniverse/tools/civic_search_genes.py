"""
civic_search_genes

Search for genes in CIViC (Clinical Interpretation of Variants in Cancer) database. CIViC is a co...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def civic_search_genes(
    limit: Optional[int] = 10,
    name: Optional[str] = None,
    query: Optional[str] = None,
    gene_name: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search for genes in CIViC (Clinical Interpretation of Variants in Cancer) database. CIViC is a co...

    Parameters
    ----------
    limit : int
        Maximum number of genes to return (default: 10, recommended max: 100)
    name : str
        Gene symbol to search for (e.g., "EGFR", "BRAF", "BRCA1"). Alias: use 'query'...
    query : str
        Gene symbol to search for (e.g., "FLT3", "KRAS", "TP53"). Alias for 'name'.
    gene_name : str
        Gene symbol to search for. Alias for 'name'.
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
            "limit": limit,
            "name": name,
            "query": query,
            "gene_name": gene_name,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "civic_search_genes",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["civic_search_genes"]
