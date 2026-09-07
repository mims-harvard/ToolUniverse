"""
VSDRemoveSource

Remove one explicitly registered source from the local Verified Source Directory.
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def VSDRemoveSource(
    source_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Remove one explicitly registered source from the local Verified Source Directory.

    Parameters
    ----------
    source_id : str
        Registered VSD source identifier to remove.
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
    _args = {k: v for k, v in {"source_id": source_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "VSDRemoveSource",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["VSDRemoveSource"]
