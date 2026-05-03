"""
BVBRC_search_amr

Search for antimicrobial resistance (AMR) phenotype data in BV-BRC. Returns resistance/susceptibi...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def BVBRC_search_amr(
    antibiotic: Optional[str | Any] = None,
    genome_id: Optional[str | Any] = None,
    resistant_phenotype: Optional[str | Any] = None,
    limit: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search for antimicrobial resistance (AMR) phenotype data in BV-BRC. Returns resistance/susceptibi...

    Parameters
    ----------
    antibiotic : str | Any
        Antibiotic name to search for. Examples: 'methicillin', 'vancomycin', 'ciprof...
    genome_id : str | Any
        BV-BRC genome ID to get AMR data for a specific genome. Example: '83332.12'.
    resistant_phenotype : str | Any
        Filter by resistance phenotype. Options: 'Resistant', 'Susceptible', 'Interme...
    limit : int | Any
        Maximum number of results. Default: 25. Max: 100.
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
            "antibiotic": antibiotic,
            "genome_id": genome_id,
            "resistant_phenotype": resistant_phenotype,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "BVBRC_search_amr",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["BVBRC_search_amr"]
