"""
Mcule_get_database

Get detailed information for a specific Mcule compound database file by its ID. Returns database ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Mcule_get_database(
    operation: str,
    database_id: int,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get detailed information for a specific Mcule compound database file by its ID. Returns database ...

    Parameters
    ----------
    operation : str
        Operation type
    database_id : int
        Database file ID. Known IDs: 1 (Full), 2 (In Stock), 15 (Building Blocks), 3 ...
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
    _args = {
        k: v
        for k, v in {"operation": operation, "database_id": database_id}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Mcule_get_database",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Mcule_get_database"]
