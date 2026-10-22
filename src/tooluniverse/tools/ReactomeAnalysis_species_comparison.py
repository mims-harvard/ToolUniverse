"""
ReactomeAnalysis_species_comparison

Perform Reactome identifier projection: submit protein/gene identifiers and Reactome automaticall...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ReactomeAnalysis_species_comparison(
    identifiers: str,
    species: Optional[int] = None,
    page_size: Optional[int] = 20,
    page: Optional[int] = 1,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Perform Reactome identifier projection: submit protein/gene identifiers and Reactome automaticall...

    Parameters
    ----------
    identifiers : str
        Newline-separated list of gene/protein identifiers from any species. Supports...
    species : int
        Unsupported by this Reactome endpoint. Supplying it returns an explicit error...
    page_size : int
        Number of pathways to return (default 20, max 50).
    page : int
        One-based pathway result page.
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
            "page": page,
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
