"""
OMIM_get_gene_map

Get OMIM gene-disease mapping information. Returns genes mapped to chromosomal locations with ass...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OMIM_get_gene_map(
    operation: str,
    mim_number: Optional[str] = None,
    chromosome: Optional[str] = None,
    limit: Optional[int] = 50,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get OMIM gene-disease mapping information. Returns genes mapped to chromosomal locations with ass...

    Parameters
    ----------
    operation : str
        Operation type (fixed: get_gene_map)
    mim_number : str
        OMIM MIM number for specific gene (optional if chromosome provided)
    chromosome : str
        Chromosome number (1-22, X, Y) to get all genes (optional if mim_number provi...
    limit : int
        Maximum results for chromosome query (default: 50, max: 100)
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
            "name": "OMIM_get_gene_map",
            "arguments": {
                "operation": operation,
                "mim_number": mim_number,
                "chromosome": chromosome,
                "limit": limit,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OMIM_get_gene_map"]
