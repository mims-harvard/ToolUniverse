"""
BOLDSystems_search_by_taxon

Search BOLD (Barcode of Life Data System) DNA barcode records by taxon. rank='genus'/'family'/'or...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def BOLDSystems_search_by_taxon(
    taxon_name: str,
    rank: Optional[str] = None,
    country: Optional[str] = None,
    limit: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search BOLD (Barcode of Life Data System) DNA barcode records by taxon. rank='genus'/'family'/'or...

    Parameters
    ----------
    taxon_name : str
        Taxon name matching rank, e.g. 'Panthera' (genus), 'Felidae' (family), 'Carni...
    rank : str
        Taxonomic rank of taxon_name. Default 'genus'.
    country : str
        Optional country/ocean name to narrow results, e.g. 'Canada'.
    limit : int
        Max records to return, 1-200. Default 30.
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
            "taxon_name": taxon_name,
            "rank": rank,
            "country": country,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "BOLDSystems_search_by_taxon",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["BOLDSystems_search_by_taxon"]
