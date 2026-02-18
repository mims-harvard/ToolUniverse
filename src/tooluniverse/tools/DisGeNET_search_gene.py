"""
DisGeNET_search_gene

Search DisGeNET for diseases associated with a gene. DisGeNET is the largest public database of g...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def DisGeNET_search_gene(
    operation: str,
    gene: str,
    limit: Optional[int] = 10,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search DisGeNET for diseases associated with a gene. DisGeNET is the largest public database of g...

    Parameters
    ----------
    operation : str
        Operation type (fixed: search_gene)
    gene : str
        Gene symbol (e.g., BRCA1, TP53, EGFR)
    limit : int
        Maximum associations to return (default: 10)
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
            "name": "DisGeNET_search_gene",
            "arguments": {"operation": operation, "gene": gene, "limit": limit},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["DisGeNET_search_gene"]
