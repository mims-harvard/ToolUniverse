"""
UniProtLocations_get_location

Get detailed information about a UniProt subcellular location by its ID. Returns the location nam...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def UniProtLocations_get_location(
    location_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get detailed information about a UniProt subcellular location by its ID. Returns the location nam...

    Parameters
    ----------
    location_id : str
        UniProt subcellular location ID. Format: SL-XXXX. Examples: 'SL-0091' (Cytoso...
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
    _args = {k: v for k, v in {"location_id": location_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "UniProtLocations_get_location",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["UniProtLocations_get_location"]
