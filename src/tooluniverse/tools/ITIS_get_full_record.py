"""
ITIS_get_full_record

Get the complete taxonomic record from ITIS for a given TSN (Taxonomic Serial Number). Returns sc...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ITIS_get_full_record(
    tsn: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get the complete taxonomic record from ITIS for a given TSN (Taxonomic Serial Number). Returns sc...

    Parameters
    ----------
    tsn : str
        ITIS Taxonomic Serial Number. Examples: '180092' (Homo sapiens), '573082' (Pa...
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
    _args = {k: v for k, v in {"tsn": tsn}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "ITIS_get_full_record",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ITIS_get_full_record"]
