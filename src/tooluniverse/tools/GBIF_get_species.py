"""
GBIF_get_species

Get detailed species information from the Global Biodiversity Information Facility (GBIF) by its ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GBIF_get_species(
    speciesKey: int,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get detailed species information from the Global Biodiversity Information Facility (GBIF) by its ...

    Parameters
    ----------
    speciesKey : int
        GBIF species/taxon key. Examples: 2435099 (Puma concolor / puma), 2878688 (Qu...
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
    _args = {k: v for k, v in {"speciesKey": speciesKey}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "GBIF_get_species",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["GBIF_get_species"]
