"""
GBIF_suggest_species

Autocomplete species names using the GBIF species suggestion endpoint. Returns quick matches as y...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GBIF_suggest_species(
    q: str,
    limit: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Autocomplete species names using the GBIF species suggestion endpoint. Returns quick matches as y...

    Parameters
    ----------
    q : str
        Partial or full species/taxon name to autocomplete. Examples: 'Homo sap', 'Qu...
    limit : int | Any
        Maximum number of suggestions to return (1-20, default 10).
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
        {"name": "GBIF_suggest_species", "arguments": {"q": q, "limit": limit}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["GBIF_suggest_species"]
