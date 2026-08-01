"""
VSDCDCPlacesHeartHealthProfile

Retrieve a validated eight-measure CDC PLACES heart-health profile for census tracts in one US co...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def VSDCDCPlacesHeartHealthProfile(
    state_abbr: str,
    county_name: str,
    limit: Optional[int] = 500,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Retrieve a validated eight-measure CDC PLACES heart-health profile for census tracts in one US co...

    Parameters
    ----------
    state_abbr : str
        Two-letter US state abbreviation.
    county_name : str
        County name without the word County, for example Autauga.
    limit : int
        Maximum census-tract measure records to retrieve.
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    dict[str, Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "state_abbr": state_abbr,
            "county_name": county_name,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "VSDCDCPlacesHeartHealthProfile",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["VSDCDCPlacesHeartHealthProfile"]
