"""
eBird_get_taxon_groups

Get the list of bird taxonomic groups from eBird (Cornell Lab of Ornithology). Returns all bird g...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def eBird_get_taxon_groups(
    speciesGrouping: str,
    groupNameLocale: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get the list of bird taxonomic groups from eBird (Cornell Lab of Ornithology). Returns all bird g...

    Parameters
    ----------
    speciesGrouping : str
        Grouping system to use. 'merlin' returns ~30 simplified groups used in the Me...
    groupNameLocale : str | Any
        Language code for group names (e.g., 'en' for English, 'es' for Spanish, 'fr'...
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
    _args = {k: v for k, v in {
        "speciesGrouping": speciesGrouping,
                "groupNameLocale": groupNameLocale
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "eBird_get_taxon_groups",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["eBird_get_taxon_groups"]
