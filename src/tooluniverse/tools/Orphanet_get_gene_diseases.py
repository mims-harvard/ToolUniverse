"""
Orphanet_get_gene_diseases

Get rare diseases associated with a gene from Orphanet. Accepts gene symbols (e.g., 'FBN1', 'BRCA...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Orphanet_get_gene_diseases(
    operation: Optional[str] = None,
    gene_name: Optional[str] = None,
    gene_symbol: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get rare diseases associated with a gene from Orphanet. Accepts gene symbols (e.g., 'FBN1', 'BRCA...

    Parameters
    ----------
    operation : str
        Operation type (fixed: get_gene_diseases)
    gene_name : str
        Gene symbol or name keyword (e.g., 'FBN1', 'BRCA1', 'huntingtin'). Use gene_s...
    gene_symbol : str | Any
        Alternative to gene_name: standard HGNC gene symbol (e.g., 'GBA1', 'FBN1'). N...
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
            "gene_name": gene_name,
            "gene_symbol": gene_symbol,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Orphanet_get_gene_diseases",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Orphanet_get_gene_diseases"]
