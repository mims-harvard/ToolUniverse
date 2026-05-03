"""
GenCC_search_gene

Get gene-disease validity classifications for a gene from GenCC (Gene Curation Coalition). Return...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GenCC_search_gene(
    gene_symbol: str,
    operation: Optional[str] = None,
    classification: Optional[str] = "",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get gene-disease validity classifications for a gene from GenCC (Gene Curation Coalition). Return...

    Parameters
    ----------
    operation : str
        Operation type (fixed: search_gene)
    gene_symbol : str
        HGNC gene symbol (e.g., BRCA2, TP53, FBN1, CFTR)
    classification : str
        Optional filter by classification level (e.g., Definitive, Strong, Moderate, ...
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
            "gene_symbol": gene_symbol,
            "classification": classification,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "GenCC_search_gene",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["GenCC_search_gene"]
