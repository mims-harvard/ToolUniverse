"""
eBird_get_taxonomy

Get bird taxonomy data from eBird (Cornell Lab of Ornithology). Returns taxonomic information inc...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def eBird_get_taxonomy(
    species: Optional[str | Any] = None,
    taxonType: Optional[str | Any] = None,
    locale: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get bird taxonomy data from eBird (Cornell Lab of Ornithology). Returns taxonomic information inc...

    Parameters
    ----------
    species : str | Any
        eBird species code to filter to a single species (e.g., 'amerob' for American...
    taxonType : str | Any
        Taxonomic category filter. Values: 'species' (full species only), 'issf' (ide...
    locale : str | Any
        Language code for common names (e.g., 'en' for English, 'es' for Spanish, 'fr...
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
            "name": "eBird_get_taxonomy",
            "arguments": {"species": species, "taxonType": taxonType, "locale": locale},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["eBird_get_taxonomy"]
