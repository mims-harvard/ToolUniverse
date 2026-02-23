"""
CoL_get_taxon

Get detailed taxonomic information for a specific taxon in the Catalogue of Life by its CoL ID. R...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def CoL_get_taxon(
    taxon_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get detailed taxonomic information for a specific taxon in the Catalogue of Life by its CoL ID. R...

    Parameters
    ----------
    taxon_id : str
        CoL taxon ID (e.g., '6MB3T' for Homo sapiens, '64J67' for Panthera leo). Obta...
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
        {"name": "CoL_get_taxon", "arguments": {"taxon_id": taxon_id}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["CoL_get_taxon"]
