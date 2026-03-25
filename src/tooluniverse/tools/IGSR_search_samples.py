"""
IGSR_search_samples

Search samples from the 1000 Genomes Project by population, data collection, or sample name. Retu...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def IGSR_search_samples(
    operation: Optional[str] = "search_samples",
    population: Optional[str | Any] = None,
    data_collection: Optional[str | Any] = None,
    sample_name: Optional[str | Any] = None,
    limit: Optional[int] = 25,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search samples from the 1000 Genomes Project by population, data collection, or sample name. Retu...

    Parameters
    ----------
    operation : str
        Operation type (fixed: search_samples).
    population : str | Any
        Filter by population code (e.g., 'CHB', 'YRI', 'GBR', 'CEU'). Use IGSR_search...
    data_collection : str | Any
        Filter by data collection title (e.g., '1000 Genomes 30x on GRCh38', '1000 Ge...
    sample_name : str | Any
        Look up specific sample by name (e.g., 'HG00096', 'NA12878').
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
            "population": population,
            "data_collection": data_collection,
            "sample_name": sample_name,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "IGSR_search_samples",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["IGSR_search_samples"]
