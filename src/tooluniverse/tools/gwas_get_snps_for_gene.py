"""
gwas_get_snps_for_gene

Get all GWAS Catalog SNPs mapped to a specific gene by gene name (e.g., 'BRCA1', 'TP53'). Returns...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def gwas_get_snps_for_gene(
    gene_symbol: str,
    size: Optional[int] = None,
    page: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get all GWAS Catalog SNPs mapped to a specific gene by gene name (e.g., 'BRCA1', 'TP53'). Returns...

    Parameters
    ----------
    size : int
        Number of results to return per page
    page : int
        Page number for pagination
    gene_symbol : str
        Gene name or symbol (e.g., 'BRCA1', 'TP53', 'GBA')
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
        for k, v in {"size": size, "page": page, "gene_symbol": gene_symbol}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "gwas_get_snps_for_gene",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["gwas_get_snps_for_gene"]
