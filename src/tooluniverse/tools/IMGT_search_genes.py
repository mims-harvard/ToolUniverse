"""
IMGT_search_genes

Search IMGT for immunoglobulin/TCR germline genes. Filter by gene type (IGHV, IGKV, TRAV, etc.) a...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def IMGT_search_genes(
    operation: Optional[str] = None,
    query: Optional[str] = None,
    gene_type: Optional[str] = None,
    species: Optional[str] = "Homo sapiens",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search IMGT for immunoglobulin/TCR germline genes. Filter by gene type (IGHV, IGKV, TRAV, etc.) a...

    Parameters
    ----------
    operation : str

    query : str
        Search query (gene name)
    gene_type : str
        Gene type: IGHV, IGHD, IGHJ, IGKV, IGLV, TRAV, TRBV, etc.
    species : str
        Species name (default: Homo sapiens)
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
            "query": query,
            "gene_type": gene_type,
            "species": species,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "IMGT_search_genes",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["IMGT_search_genes"]
