"""
GTEx_calculate_eqtl

Calculate custom eQTL for any gene-variant pair in any tissue. Dynamically calculates gene-varian...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GTEx_calculate_eqtl(
    gencode_id: str,
    variant_id: str,
    tissue_site_detail_id: str,
    operation: Optional[str] = None,
    dataset_id: Optional[str] = "gtex_v8",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Calculate custom eQTL for any gene-variant pair in any tissue. Dynamically calculates gene-varian...

    Parameters
    ----------
    operation : str
        Operation type
    gencode_id : str
        Required: Versioned GENCODE ID (e.g. ENSG00000141510.18)
    variant_id : str
        Required: GTEx variant ID
    tissue_site_detail_id : str
        Required: Tissue ID (e.g. 'Whole_Blood')
    dataset_id : str

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
            "gencode_id": gencode_id,
            "variant_id": variant_id,
            "tissue_site_detail_id": tissue_site_detail_id,
            "dataset_id": dataset_id,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "GTEx_calculate_eqtl",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["GTEx_calculate_eqtl"]
