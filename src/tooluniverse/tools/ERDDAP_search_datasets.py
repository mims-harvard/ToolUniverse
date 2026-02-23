"""
ERDDAP_search_datasets

Search for oceanographic and atmospheric datasets in NOAA CoastWatch ERDDAP (Environmental Resear...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ERDDAP_search_datasets(
    searchFor: str,
    itemsPerPage: Optional[int | Any] = None,
    page: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search for oceanographic and atmospheric datasets in NOAA CoastWatch ERDDAP (Environmental Resear...

    Parameters
    ----------
    searchFor : str
        Search keyword(s) for dataset discovery. Examples: 'sea surface temperature',...
    itemsPerPage : int | Any
        Number of results to return (1-100). Default: 10
    page : int | Any
        Page number for pagination. Default: 1
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
        {
            "name": "ERDDAP_search_datasets",
            "arguments": {
                "searchFor": searchFor,
                "itemsPerPage": itemsPerPage,
                "page": page,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ERDDAP_search_datasets"]
