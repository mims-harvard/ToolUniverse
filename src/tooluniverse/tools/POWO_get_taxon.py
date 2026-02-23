"""
POWO_get_taxon

Get detailed taxonomic information for a specific plant species from Plants of the World Online (...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def POWO_get_taxon(
    fqId: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get detailed taxonomic information for a specific plant species from Plants of the World Online (...

    Parameters
    ----------
    fqId : str
        Fully qualified taxon ID from POWO. Format: 'urn:lsid:ipni.org:names:XXXXXXX-...
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
        {"name": "POWO_get_taxon", "arguments": {"fqId": fqId}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["POWO_get_taxon"]
