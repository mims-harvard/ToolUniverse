"""
gwas_search_snps

Search the GWAS Catalog for single nucleotide polymorphisms (SNPs) by rs ID (e.g., 'rs7903146') o...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def gwas_search_snps(
    rs_id: Optional[str] = None,
    mapped_gene: Optional[str] = None,
    size: Optional[int] = None,
    page: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search the GWAS Catalog for single nucleotide polymorphisms (SNPs) by rs ID (e.g., 'rs7903146') o...

    Parameters
    ----------
    rs_id : str
        dbSNP rs identifier
    mapped_gene : str
        Gene name or symbol
    size : int
        Number of results to return
    page : int
        Page number for pagination
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
            "rs_id": rs_id,
            "mapped_gene": mapped_gene,
            "size": size,
            "page": page,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "gwas_search_snps",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["gwas_search_snps"]
