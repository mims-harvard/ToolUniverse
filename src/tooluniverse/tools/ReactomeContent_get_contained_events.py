"""
ReactomeContent_get_contained_events

Get all events (sub-pathways and reactions) contained within a Reactome pathway. Decomposes a top...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ReactomeContent_get_contained_events(
    identifier: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get all events (sub-pathways and reactions) contained within a Reactome pathway. Decomposes a top...

    Parameters
    ----------
    identifier : str
        Reactome pathway stable identifier. Examples: 'R-HSA-109581' (Apoptosis, 177 ...
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
        "identifier": identifier
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "ReactomeContent_get_contained_events",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["ReactomeContent_get_contained_events"]
