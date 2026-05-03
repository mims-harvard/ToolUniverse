"""
PDC_get_gene_protein

Get protein information and proteomics study coverage for a gene from the NCI Proteomics Data Com...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PDC_get_gene_protein(
    operation: str,
    gene_name: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get protein information and proteomics study coverage for a gene from the NCI Proteomics Data Com...

    Parameters
    ----------
    operation : str
        Operation type
    gene_name : str
        Gene symbol to look up (e.g., 'TP53', 'EGFR', 'BRCA1', 'MYC')
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
        for k, v in {"operation": operation, "gene_name": gene_name}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "PDC_get_gene_protein",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PDC_get_gene_protein"]
