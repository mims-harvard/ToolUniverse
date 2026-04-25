"""
NASACMR_search_granules

Search NASA CMR for individual granules (data files/scenes) within Earth observation collections....
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NASACMR_search_granules(
    concept_id: Optional[str | Any] = None,
    short_name: Optional[str | Any] = None,
    temporal: Optional[str | Any] = None,
    bounding_box: Optional[str | Any] = None,
    page_size: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search NASA CMR for individual granules (data files/scenes) within Earth observation collections....

    Parameters
    ----------
    concept_id : str | Any
        Parent collection concept ID (e.g., 'C2036882064-POCLOUD'). Get from NASACMR_...
    short_name : str | Any
        Collection short name (e.g., 'MYD11A1', 'MODIS_A-JPL-L2P-v2019.0')
    temporal : str | Any
        Temporal range in format 'YYYY-MM-DD,YYYY-MM-DD'. Examples: '2020-01-01,2020-...
    bounding_box : str | Any
        Spatial bounding box: 'west,south,east,north' in decimal degrees. Example: '-...
    page_size : int | Any
        Number of results (default 10, max 2000)
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
        "concept_id": concept_id,
                "short_name": short_name,
                "temporal": temporal,
                "bounding_box": bounding_box,
                "page_size": page_size
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "NASACMR_search_granules",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["NASACMR_search_granules"]
