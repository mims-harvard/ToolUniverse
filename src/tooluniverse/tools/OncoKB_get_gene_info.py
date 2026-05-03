"""
OncoKB_get_gene_info

Get gene-level oncogenic information from OncoKB. Returns whether gene is an oncogene, tumor supp...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OncoKB_get_gene_info(
    operation: Optional[str] = None,
    gene: Optional[str] = None,
    gene_symbol: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get gene-level oncogenic information from OncoKB. Returns whether gene is an oncogene, tumor supp...

    Parameters
    ----------
    operation : str
        Operation type (fixed: get_gene_info)
    gene : str
        Gene symbol (e.g., BRAF, TP53, ROS1). Without ONCOKB_API_TOKEN only BRAF, TP5...
    gene_symbol : str
        Gene symbol alias — alternative to gene parameter
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
            "gene": gene,
            "gene_symbol": gene_symbol,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "OncoKB_get_gene_info",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OncoKB_get_gene_info"]
