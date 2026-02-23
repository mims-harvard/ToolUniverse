"""
EOL_get_hierarchy_entry

Get taxonomy hierarchy (classification tree) for a species from a specific classification system ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EOL_get_hierarchy_entry(
    hierarchy_entry_id: int,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get taxonomy hierarchy (classification tree) for a species from a specific classification system ...

    Parameters
    ----------
    hierarchy_entry_id : int
        EOL hierarchy entry ID from a specific classification system. Get this from E...
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
            "name": "EOL_get_hierarchy_entry",
            "arguments": {"hierarchy_entry_id": hierarchy_entry_id},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["EOL_get_hierarchy_entry"]
