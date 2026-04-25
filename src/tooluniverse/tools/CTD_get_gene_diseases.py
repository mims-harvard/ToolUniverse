"""
CTD_get_gene_diseases

Get curated gene-disease associations from CTD. Given a gene symbol, returns diseases associated ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def CTD_get_gene_diseases(
    input_terms: Optional[str] = None,
    query: Optional[str] = None,
    gene_symbol: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get curated gene-disease associations from CTD. Given a gene symbol, returns diseases associated ...

    Parameters
    ----------
    input_terms : str
        Gene symbol or NCBI Gene ID. Examples: 'TP53', 'BRCA1', 'CYP1A1', '7157' (Gen...
    query : str
        Gene symbol or name to search (alias for input_terms, e.g. TP53)
    gene_symbol : str
        Gene symbol (alias for input_terms, e.g. TP53)
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
            "input_terms": input_terms,
            "query": query,
            "gene_symbol": gene_symbol,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "CTD_get_gene_diseases",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["CTD_get_gene_diseases"]
