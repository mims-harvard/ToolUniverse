"""
GTEx_get_multi_tissue_eqtls

Get multi-tissue eQTL meta-analysis results (Metasoft). Returns m-values (posterior probability o...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GTEx_get_multi_tissue_eqtls(
    gencode_id: str,
    operation: Optional[str] = None,
    variant_id: Optional[str] = None,
    dataset_id: Optional[str] = "gtex_v8",
    page: Optional[int] = 0,
    items_per_page: Optional[int] = 250,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Get multi-tissue eQTL meta-analysis results (Metasoft). Returns m-values (posterior probability o...

    Parameters
    ----------
    operation : str
        Operation type
    gencode_id : str
        Required: Versioned GENCODE ID
    variant_id : str
        Optional: GTEx variant ID to filter specific variant
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
            "variant_id": variant_id,
            "dataset_id": dataset_id,
            "page": page,
            "items_per_page": items_per_page,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "GTEx_get_multi_tissue_eqtls",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["GTEx_get_multi_tissue_eqtls"]
