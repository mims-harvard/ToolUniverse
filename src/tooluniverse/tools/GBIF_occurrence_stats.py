"""
GBIF_occurrence_stats

Get GBIF occurrence statistics for a taxonKey: the total occurrence count plus faceted breakdowns...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GBIF_occurrence_stats(
    taxonKey: int,
    facet: Optional[str] = "country",
    facetLimit: Optional[int] = 10,
    country: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get GBIF occurrence statistics for a taxonKey: the total occurrence count plus faceted breakdowns...

    Parameters
    ----------
    taxonKey : int
        GBIF taxon key, e.g. 2435099 (Puma concolor). Obtain from GBIF_match_name or ...
    facet : str
        Field to break occurrence counts down by, e.g. 'country', 'year', 'basisOfRec...
    facetLimit : int
        Number of top facet values to return (default 10).
    country : str
        Optional ISO 3166-1 alpha-2 country code filter, e.g. 'US'.
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
            "taxonKey": taxonKey,
            "facet": facet,
            "facetLimit": facetLimit,
            "country": country,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "GBIF_occurrence_stats",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["GBIF_occurrence_stats"]
