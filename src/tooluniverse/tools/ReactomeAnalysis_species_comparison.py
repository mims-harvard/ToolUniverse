"""
ReactomeAnalysis_species_comparison

Perform Reactome pathway analysis with cross-species projection. Submit protein/gene identifiers ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ReactomeAnalysis_species_comparison(
    identifiers: str,
    species: Optional[int | Any] = None,
    page_size: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Perform Reactome pathway analysis with cross-species projection. Submit protein/gene identifiers ...

    Parameters
    ----------
    identifiers : str
        Newline-separated list of gene/protein identifiers from any species. Supports...
    species : int | Any
        NCBI taxonomy ID of the source species (default 9606 for human). Examples: 10...
    page_size : int | Any
        Number of pathways to return (default 20, max 50).
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
            "identifiers": identifiers,
            "species": species,
            "page_size": page_size,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ReactomeAnalysis_species_comparison",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ReactomeAnalysis_species_comparison"]
