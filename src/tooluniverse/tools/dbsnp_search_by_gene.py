"""
dbsnp_search_by_gene

Search for variants in a specific gene. Returns variants associated with the gene symbol.
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def dbsnp_search_by_gene(
    gene_symbol: str,
    limit: Optional[int] = 20,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search for variants in a specific gene. Returns variants associated with the gene symbol.

    Parameters
    ----------
    gene_symbol : str
        Gene symbol (e.g., 'BRCA1', 'TP53', 'APOE')
    limit : int
        Maximum number of results to return
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
        for k, v in {"gene_symbol": gene_symbol, "limit": limit}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "dbsnp_search_by_gene",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["dbsnp_search_by_gene"]
