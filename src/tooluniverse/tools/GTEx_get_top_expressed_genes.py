"""
GTEx_get_top_expressed_genes

Get top expressed genes in a specific tissue sorted by median expression. Returns gene list with ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GTEx_get_top_expressed_genes(
    tissue_site_detail_id: str,
    operation: Optional[str] = None,
    filter_mt_genes: Optional[bool] = True,
    dataset_id: Optional[str] = "gtex_v8",
    page: Optional[int] = 0,
    items_per_page: Optional[int] = 250,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Get top expressed genes in a specific tissue sorted by median expression. Returns gene list with ...

    Parameters
    ----------
    operation : str
        Operation type
    tissue_site_detail_id : str
        Required: Tissue ID (e.g. 'Liver', 'Brain_Cortex'). Use GTEx_get_tissue_sites...
    filter_mt_genes : bool
        Exclude mitochondrial genes from results
    dataset_id : str

    page : int

    items_per_page : int

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
            "operation": operation,
            "tissue_site_detail_id": tissue_site_detail_id,
            "filter_mt_genes": filter_mt_genes,
            "dataset_id": dataset_id,
            "page": page,
            "items_per_page": items_per_page,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "GTEx_get_top_expressed_genes",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["GTEx_get_top_expressed_genes"]
