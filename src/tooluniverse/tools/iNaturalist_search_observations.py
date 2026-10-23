"""
iNaturalist_search_observations

Search iNaturalist observations by taxon/name, place, and quality, ordered by observation ID desc...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def iNaturalist_search_observations(
    taxon_id: Optional[int] = None,
    query: Optional[str] = None,
    quality_grade: Optional[str] = "research",
    place_id: Optional[int] = None,
    per_page: Optional[int] = 10,
    page: Optional[int] = 1,
    id_below: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search iNaturalist observations by taxon/name, place, and quality, ordered by observation ID desc...

    Parameters
    ----------
    taxon_id : int
        iNaturalist taxon ID to filter by. Examples: 41482 (bottlenose dolphin), 4194...
    query : str
        Text search for species name. Alternative to taxon_id.
    quality_grade : str
        Observation quality: 'research' (community-verified), 'needs_id' (unverified)...
    place_id : int
        iNaturalist place ID to filter by location. Example: 10211 (Yellowstone Natio...
    per_page : int
        Number of results per page (1-200, default 10).
    page : int
        One-based results page (default 1). iNaturalist exposes at most the first 10,...
    id_below : int
        Sliding-window cursor. Set page=1 and pass metadata.next_id_below from the pr...
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
            "page": page,
            "id_below": id_below,
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
