"""
EWASAtlas_search_by_gene

Find the CpG probes annotated to a gene in EWAS Atlas and the curated epigenome-wide association ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EWASAtlas_search_by_gene(
    gene_symbol: str,
    limit: Optional[int] = None,
    max_associations_per_probe: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Find the CpG probes annotated to a gene in EWAS Atlas and the curated epigenome-wide association ...

    Parameters
    ----------
    gene_symbol : str
        HGNC gene symbol, e.g. 'AHRR' or 'F2RL3'.
    limit : int
        Max probes to return, 1-500. Default 50.
    max_associations_per_probe : int
        Max associations listed under each probe, 1-200. Default 10 (association_coun...
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    list[Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "gene_symbol": gene_symbol,
            "limit": limit,
            "max_associations_per_probe": max_associations_per_probe,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "EWASAtlas_search_by_gene",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["EWASAtlas_search_by_gene"]
