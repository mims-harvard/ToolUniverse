"""
GEO_search_chipseq_datasets

Search NCBI GEO for ChIP-seq (Chromatin Immunoprecipitation followed by sequencing) datasets. ChI...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GEO_search_chipseq_datasets(
    query: str,
    organism: Optional[str] = 'Homo sapiens',
    limit: Optional[int] = 20,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search NCBI GEO for ChIP-seq (Chromatin Immunoprecipitation followed by sequencing) datasets. ChI...

    Parameters
    ----------
    query : str
        Search terms for ChIP-seq datasets (e.g., 'H3K27ac liver', 'CTCF cancer', 'p5...
    organism : str
        Organism filter.
    limit : int
        Maximum number of dataset IDs to return.
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    Any
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {k: v for k, v in {
        "query": query,
                "organism": organism,
                "limit": limit
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "GEO_search_chipseq_datasets",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["GEO_search_chipseq_datasets"]
