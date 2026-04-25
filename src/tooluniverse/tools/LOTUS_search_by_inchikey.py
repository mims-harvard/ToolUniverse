"""
LOTUS_search_by_inchikey

Search the LOTUS natural products database specifically by InChIKey, which provides exact structu...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def LOTUS_search_by_inchikey(
    inchikey: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search the LOTUS natural products database specifically by InChIKey, which provides exact structu...

    Parameters
    ----------
    inchikey : str
        InChIKey to search for (e.g., 'RYYVLZVUVIJVGH-UHFFFAOYSA-N' for caffeine, 'IQ...
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
        "inchikey": inchikey
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "LOTUS_search_by_inchikey",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["LOTUS_search_by_inchikey"]
