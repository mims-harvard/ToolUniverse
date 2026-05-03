"""
iNaturalist_search_observations

Search for georeferenced species observations from iNaturalist citizen scientists. Filter by taxo...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def iNaturalist_search_observations(
    taxon_id: Optional[int | Any] = None,
    query: Optional[str | Any] = None,
    quality_grade: Optional[str | Any] = None,
    place_id: Optional[int | Any] = None,
    per_page: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search for georeferenced species observations from iNaturalist citizen scientists. Filter by taxo...

    Parameters
    ----------
    taxon_id : int | Any
        iNaturalist taxon ID to filter by. Examples: 41482 (bottlenose dolphin), 4194...
    query : str | Any
        Text search for species name. Alternative to taxon_id.
    quality_grade : str | Any
        Observation quality: 'research' (community-verified), 'needs_id' (unverified)...
    place_id : int | Any
        iNaturalist place ID to filter by location. Example: 10211 (Yellowstone Natio...
    per_page : int | Any
        Number of results (1-200, default 10).
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
            "query": query,
            "quality_grade": quality_grade,
            "place_id": place_id,
            "per_page": per_page,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "iNaturalist_search_observations",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["iNaturalist_search_observations"]
