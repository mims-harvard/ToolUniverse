"""
IGSR_search_populations

Search 1000 Genomes Project populations from the International Genome Sample Resource (IGSR). The...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def IGSR_search_populations(
    operation: Optional[str] = "search_populations",
    superpopulation: Optional[str | Any] = None,
    query: Optional[str | Any] = None,
    limit: Optional[int] = 25,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search 1000 Genomes Project populations from the International Genome Sample Resource (IGSR). The...

    Parameters
    ----------
    operation : str
        Operation type (fixed: search_populations).
    superpopulation : str | Any
        Filter by superpopulation code: AFR (African), AMR (Admixed American), EAS (E...
    query : str | Any
        Free-text search query to find populations by name or description (e.g., 'Chi...
    limit : int
        Maximum number of results to return.
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
    _args = {
        k: v
        for k, v in {
            "operation": operation,
            "superpopulation": superpopulation,
            "query": query,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "IGSR_search_populations",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["IGSR_search_populations"]
