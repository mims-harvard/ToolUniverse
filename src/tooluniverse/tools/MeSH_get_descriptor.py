"""
MeSH_get_descriptor

Get detailed information for a MeSH descriptor by its ID. Returns the descriptor's label, type, a...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MeSH_get_descriptor(
    descriptor_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get detailed information for a MeSH descriptor by its ID. Returns the descriptor's label, type, a...

    Parameters
    ----------
    descriptor_id : str
        MeSH descriptor ID. Examples: 'D009369' (Neoplasms), 'D003920' (Diabetes Mell...
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
    _args = {k: v for k, v in {"descriptor_id": descriptor_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "MeSH_get_descriptor",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MeSH_get_descriptor"]
