"""
COSMIC_search_mutations

Search COSMIC database for somatic mutations in cancer. COSMIC is the world's largest expert-cura...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def COSMIC_search_mutations(
    operation: Optional[str] = None,
    terms: Optional[str] = None,
    query: Optional[str] = None,
    max_results: Optional[int] = 20,
    genome_build: Optional[int] = 37,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search COSMIC database for somatic mutations in cancer. COSMIC is the world's largest expert-cura...

    Parameters
    ----------
    operation : str
        Operation type (fixed: search)
    terms : str
        Search query - gene name (e.g., BRAF), mutation (e.g., V600E), or mutation ID...
    query : str
        Alias for terms. Search query - gene name, mutation, or COSMIC ID.
    max_results : int
        Maximum number of results to return (default: 20, max: 500)
    genome_build : int
        Genome build version: 37 (GRCh37/hg19) or 38 (GRCh38/hg38). Default: 37
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
            "terms": terms,
            "query": query,
            "max_results": max_results,
            "genome_build": genome_build,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "COSMIC_search_mutations",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["COSMIC_search_mutations"]
