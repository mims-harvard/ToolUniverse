"""
Orphanet_get_gene_diseases

Get rare diseases associated with a gene from Orphanet. Search by gene name keyword (e.g., 'fibri...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Orphanet_get_gene_diseases(
    operation: str,
    gene_name: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get rare diseases associated with a gene from Orphanet. Search by gene name keyword (e.g., 'fibri...

    Parameters
    ----------
    operation : str
        Operation type (fixed: get_gene_diseases)
    gene_name : str
        Gene name keyword to search (e.g., 'fibrillin', 'huntingtin', 'collagen', 'dy...
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

    return get_shared_client().run_one_function(
        {
            "name": "Orphanet_get_gene_diseases",
            "arguments": {"operation": operation, "gene_name": gene_name},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Orphanet_get_gene_diseases"]
