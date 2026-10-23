"""
IMPC_get_gene_phenotype_hits

Get detailed IMPC statistical phenotype results for a gene with exact Solr offset pagination. Fil...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def IMPC_get_gene_phenotype_hits(
    gene_symbol: Optional[str] = None,
    mgi_id: Optional[str] = None,
    significant_only: Optional[bool] = True,
    limit: Optional[int] = 100,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get detailed IMPC statistical phenotype results for a gene with exact Solr offset pagination. Fil...

    Parameters
    ----------
    gene_symbol : str
        Mouse gene symbol (e.g., 'Trp53', 'Brca1')
    mgi_id : str
        MGI accession ID (e.g., 'MGI:98834')
    significant_only : bool
        Return only significant results (default: true)
    limit : int
        Maximum results (default: 100)
    offset : int
        Zero-based statistical-result offset. Continue with data.next_offset.
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
            "gene_symbol": gene_symbol,
            "mgi_id": mgi_id,
            "significant_only": significant_only,
            "limit": limit,
            "offset": offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "IMPC_get_gene_phenotype_hits",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["IMPC_get_gene_phenotype_hits"]
