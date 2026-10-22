"""
EOL_get_hierarchy_entry

Get a taxonomy hierarchy entry from a specific Encyclopedia of Life classification. Returns the f...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EOL_get_hierarchy_entry(
    hierarchy_entry_id: int,
    child_limit: Optional[int] = 20,
    child_offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get a taxonomy hierarchy entry from a specific Encyclopedia of Life classification. Returns the f...

    Parameters
    ----------
    hierarchy_entry_id : int
        EOL hierarchy entry ID from a specific classification system. Get this from E...
    child_limit : int
        Maximum number of direct child taxa to return on this page.
    child_offset : int
        Zero-based offset into all direct child taxa. Continue with metadata.next_chi...
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
    _args = {
        k: v
        for k, v in {
            "hierarchy_entry_id": hierarchy_entry_id,
            "child_limit": child_limit,
            "child_offset": child_offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "EOL_get_hierarchy_entry",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["EOL_get_hierarchy_entry"]
