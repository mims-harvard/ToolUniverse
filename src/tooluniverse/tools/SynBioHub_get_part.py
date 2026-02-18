"""
SynBioHub_get_part

Get detailed SBOL (Synthetic Biology Open Language) information for a specific genetic part from ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def SynBioHub_get_part(
    display_id: Optional[str | Any] = None,
    part_uri: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get detailed SBOL (Synthetic Biology Open Language) information for a specific genetic part from ...

    Parameters
    ----------
    display_id : str | Any
        BioBrick/part display ID from the iGEM collection. Examples: 'BBa_E0040' (GFP...
    part_uri : str | Any
        Full SynBioHub URI for the part (from search results). Example: 'https://synb...
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
            "name": "SynBioHub_get_part",
            "arguments": {"display_id": display_id, "part_uri": part_uri},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["SynBioHub_get_part"]
