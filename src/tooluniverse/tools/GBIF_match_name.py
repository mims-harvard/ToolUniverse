"""
GBIF_match_name

Resolve a free-text scientific name to the single best-matching GBIF Backbone taxon. Unlike GBIF_...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GBIF_match_name(
    name: str,
    kingdom: Optional[str] = None,
    rank: Optional[str] = None,
    strict: Optional[bool] = None,
    verbose: Optional[bool] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Resolve a free-text scientific name to the single best-matching GBIF Backbone taxon. Unlike GBIF_...

    Parameters
    ----------
    name : str
        Scientific name to match, e.g. 'Puma concolor', 'Quercus robur', 'Homo sapiens'.
    kingdom : str
        Optional kingdom to disambiguate homonyms, e.g. 'Animalia', 'Plantae'.
    rank : str
        Optional rank hint, e.g. 'SPECIES', 'GENUS'.
    strict : bool
        If true, only return exact matches (no fuzzy matching).
    verbose : bool
        If true, include alternative matches in the response.
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
            "name": name,
            "kingdom": kingdom,
            "rank": rank,
            "strict": strict,
            "verbose": verbose,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "GBIF_match_name",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["GBIF_match_name"]
