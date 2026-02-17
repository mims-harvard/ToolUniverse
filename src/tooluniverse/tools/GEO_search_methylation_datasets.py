"""
GEO_search_methylation_datasets

Search NCBI GEO for DNA methylation array datasets, including Illumina 450K, EPIC (850K), and oth...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GEO_search_methylation_datasets(
    query: str,
    organism: Optional[str] = "Homo sapiens",
    limit: Optional[int] = 20,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search NCBI GEO for DNA methylation array datasets, including Illumina 450K, EPIC (850K), and oth...

    Parameters
    ----------
    query : str
        Search terms for methylation datasets (e.g., 'breast cancer methylation', 'br...
    organism : str
        Organism filter (e.g., 'Homo sapiens', 'Mus musculus').
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

    return get_shared_client().run_one_function(
        {
            "name": "GEO_search_methylation_datasets",
            "arguments": {"query": query, "organism": organism, "limit": limit},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["GEO_search_methylation_datasets"]
