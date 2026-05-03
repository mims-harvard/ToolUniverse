"""
DGIdb_get_gene_druggability

Get druggability information for genes. Returns gene categories indicating if a gene is druggable...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def DGIdb_get_gene_druggability(
    genes: Optional[list[str]] = None,
    gene_name: Optional[str] = None,
    gene: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get druggability information for genes. Returns gene categories indicating if a gene is druggable...

    Parameters
    ----------
    genes : list[str]
        List of gene symbols to check druggability. Aliases: gene_name, gene.
    gene_name : str
        Alias for genes. Single gene symbol (e.g., 'EGFR').
    gene : str
        Alias for genes. Single gene symbol (e.g., 'EGFR').
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
        for k, v in {"genes": genes, "gene_name": gene_name, "gene": gene}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "DGIdb_get_gene_druggability",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["DGIdb_get_gene_druggability"]
