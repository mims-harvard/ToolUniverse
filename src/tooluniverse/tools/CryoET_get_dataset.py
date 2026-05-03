"""
CryoET_get_dataset

Get full metadata for a specific CryoET Data Portal dataset by its numeric ID. Returns complete d...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def CryoET_get_dataset(
    operation: str,
    dataset_id: int,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get full metadata for a specific CryoET Data Portal dataset by its numeric ID. Returns complete d...

    Parameters
    ----------
    operation : str
        Operation type
    dataset_id : int
        Numeric dataset ID from the CryoET Data Portal (e.g. 10053, 10174, 10460).
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
        for k, v in {"operation": operation, "dataset_id": dataset_id}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "CryoET_get_dataset",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["CryoET_get_dataset"]
