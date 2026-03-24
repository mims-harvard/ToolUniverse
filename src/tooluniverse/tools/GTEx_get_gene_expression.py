"""
GTEx_get_gene_expression

Get gene expression data at individual sample level (not aggregated). Returns normalized expressi...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GTEx_get_gene_expression(
    gencode_id: str | list[str],
    operation: Optional[str] = None,
    tissue_site_detail_id: Optional[list[str]] = None,
    attribute_subset: Optional[str] = None,
    dataset_id: Optional[str] = "gtex_v8",
    page: Optional[int] = 0,
    items_per_page: Optional[int] = 250,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Get gene expression data at individual sample level (not aggregated). Returns normalized expressi...

    Parameters
    ----------
    operation : str
        Operation type
    gencode_id : str | list[str]
        Required: Versioned GENCODE ID(s)
    tissue_site_detail_id : list[str]
        Optional: Filter by tissues
    attribute_subset : str
        Optional: Subset by donor sex or age bracket
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
            "gencode_id": gencode_id,
            "tissue_site_detail_id": tissue_site_detail_id,
            "attribute_subset": attribute_subset,
            "dataset_id": dataset_id,
            "page": page,
            "items_per_page": items_per_page,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "GTEx_get_gene_expression",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["GTEx_get_gene_expression"]
