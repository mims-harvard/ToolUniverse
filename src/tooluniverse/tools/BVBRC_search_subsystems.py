"""
BVBRC_search_subsystems

Search for functional subsystems (curated groups of functionally related proteins) in BV-BRC path...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def BVBRC_search_subsystems(
    taxon_id: Optional[str | Any] = None,
    superclass: Optional[str | Any] = None,
    subsystem_name: Optional[str | Any] = None,
    role_name: Optional[str | Any] = None,
    genome_id: Optional[str | Any] = None,
    limit: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search for functional subsystems (curated groups of functionally related proteins) in BV-BRC path...

    Parameters
    ----------
    taxon_id : str | Any
        NCBI Taxonomy ID. Examples: '1773' (M. tuberculosis), '1280' (S. aureus), '56...
    superclass : str | Any
        Top-level functional category. Options include: 'METABOLISM', 'STRESS RESPONS...
    subsystem_name : str | Any
        Subsystem name keyword. Examples: 'mycothiol', 'iron acquisition', 'beta-lact...
    role_name : str | Any
        Specific functional role keyword. Examples: 'catalase', 'penicillin-binding p...
    genome_id : str | Any
        Restrict to a specific genome. Example: '83332.12'.
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

    return get_shared_client().run_one_function(
        {
            "name": "BVBRC_search_subsystems",
            "arguments": {
                "taxon_id": taxon_id,
                "superclass": superclass,
                "subsystem_name": subsystem_name,
                "role_name": role_name,
                "genome_id": genome_id,
                "limit": limit,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["BVBRC_search_subsystems"]
