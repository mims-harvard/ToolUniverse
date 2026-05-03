"""
BVBRC_search_surveillance

Search influenza and pathogen surveillance data in BV-BRC. Returns surveillance samples with host...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def BVBRC_search_surveillance(
    subtype: Optional[str | Any] = None,
    geographic_group: Optional[str | Any] = None,
    host_group: Optional[str | Any] = None,
    collection_country: Optional[str | Any] = None,
    limit: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search influenza and pathogen surveillance data in BV-BRC. Returns surveillance samples with host...

    Parameters
    ----------
    subtype : str | Any
        Influenza subtype to search for. Examples: 'H5N1', 'H1N1', 'H3N2', 'H7N9'. Co...
    geographic_group : str | Any
        Geographic region filter. Options: 'North America', 'Europe', 'Asia', 'Africa...
    host_group : str | Any
        Host organism group. Options: 'Human', 'Animal', 'Avian', 'Swine', 'Environme...
    collection_country : str | Any
        Country of sample collection. Examples: 'USA', 'China', 'Egypt', 'Vietnam'.
    limit : int | Any
        Maximum number of results. Default: 25. Max: 100.
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
            "subtype": subtype,
            "geographic_group": geographic_group,
            "host_group": host_group,
            "collection_country": collection_country,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "BVBRC_search_surveillance",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["BVBRC_search_surveillance"]
