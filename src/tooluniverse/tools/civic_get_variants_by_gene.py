"""
civic_get_variants_by_gene

Get all variants associated with a specific gene in CIViC database. Returns variant information i...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def civic_get_variants_by_gene(
    gene_id: Optional[int] = None,
    gene_name: Optional[str] = None,
    gene_symbol: Optional[str] = None,
    gene: Optional[str] = None,
    limit: Optional[int] = 500,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get all variants associated with a specific gene in CIViC database. Returns variant information i...

    Parameters
    ----------
    gene_id : int
        CIViC gene ID (e.g., 19 for EGFR, 12 for BRAF). Find gene IDs using civic_sea...
    gene_name : str
        Gene symbol (e.g., 'EGFR', 'BRAF', 'TP53'). Will be looked up automatically. ...
    gene_symbol : str
        Alias for gene_name. Standard gene symbol (e.g., 'KRAS', 'BRCA1', 'EGFR').
    gene : str
        Alias for gene_name. Gene symbol (e.g., 'EGFR', 'KRAS').
    limit : int
        Maximum number of variants to return (default: 500, uses cursor pagination to...
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
            "gene_id": gene_id,
            "gene_name": gene_name,
            "gene_symbol": gene_symbol,
            "gene": gene,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "civic_get_variants_by_gene",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["civic_get_variants_by_gene"]
