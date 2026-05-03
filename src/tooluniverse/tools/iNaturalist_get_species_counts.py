"""
iNaturalist_get_species_counts

Get species observation counts from iNaturalist for a given taxon group or location. Returns a ra...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def iNaturalist_get_species_counts(
    taxon_id: Optional[int | Any] = None,
    place_id: Optional[int | Any] = None,
    quality_grade: Optional[str | Any] = None,
    per_page: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get species observation counts from iNaturalist for a given taxon group or location. Returns a ra...

    Parameters
    ----------
    taxon_id : int | Any
        Parent taxon ID to get species counts within. Examples: 41479 (Delphinidae - ...
    place_id : int | Any
        Place ID to filter by location. Example: 10211 (Yellowstone).
    quality_grade : str | Any
        Quality filter: 'research', 'needs_id', or 'casual'. Default: 'research'.
    per_page : int | Any
        Number of species to return (1-500, default 20).
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
            "taxon_id": taxon_id,
            "place_id": place_id,
            "quality_grade": quality_grade,
            "per_page": per_page,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "iNaturalist_get_species_counts",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["iNaturalist_get_species_counts"]
