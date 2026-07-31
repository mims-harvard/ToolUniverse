"""
WoRMS_get_synonyms

Get the taxonomic synonyms (unaccepted names) for a marine taxon from the World Register of Marin...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def WoRMS_get_synonyms(
    AphiaID: int,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get the taxonomic synonyms (unaccepted names) for a marine taxon from the World Register of Marin...

    Parameters
    ----------
    AphiaID : int
        WoRMS AphiaID of the accepted taxon, e.g. 127160 (Solea solea). Obtain from W...
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
    _args = {k: v for k, v in {"AphiaID": AphiaID}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "WoRMS_get_synonyms",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["WoRMS_get_synonyms"]
