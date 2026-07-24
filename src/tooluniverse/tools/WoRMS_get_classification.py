"""
WoRMS_get_classification

Get the full taxonomic classification tree (ranked lineage) for a marine taxon from the World Reg...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def WoRMS_get_classification(
    AphiaID: int,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get the full taxonomic classification tree (ranked lineage) for a marine taxon from the World Reg...

    Parameters
    ----------
    AphiaID : int
        WoRMS AphiaID of the taxon, e.g. 127160 (Solea solea, common sole). Obtain fr...
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
            "name": "WoRMS_get_classification",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["WoRMS_get_classification"]
