"""
SCREEN_get_regulatory_elements

Get candidate cis-regulatory elements (cCREs) from SCREEN database for specific genomic regions
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def SCREEN_get_regulatory_elements(
    gene_name: Optional[str] = None,
    query: Optional[str] = None,
    element_type: Optional[str] = "enhancer",
    limit: Optional[int] = 10,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get candidate cis-regulatory elements (cCREs) from SCREEN database for specific genomic regions

    Parameters
    ----------
    gene_name : str
        Gene symbol to search for regulatory elements (e.g., BRCA1, TP53). Alias: 'qu...
    query : str
        Gene symbol to search for regulatory elements (alias for gene_name).
    element_type : str
        Type of regulatory element (promoter, enhancer, insulator)
    limit : int
        Number of results to return
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
            "gene_name": gene_name,
            "query": query,
            "element_type": element_type,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "SCREEN_get_regulatory_elements",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["SCREEN_get_regulatory_elements"]
