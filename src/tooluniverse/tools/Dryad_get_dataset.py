"""
Dryad_get_dataset

Get detailed metadata for a specific Dryad dataset by its numeric ID. Returns comprehensive infor...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Dryad_get_dataset(
    dataset_id: int,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get detailed metadata for a specific Dryad dataset by its numeric ID. Returns comprehensive infor...

    Parameters
    ----------
    dataset_id : int
        Numeric dataset ID from Dryad (e.g., 93, 94, 95). Find IDs using Dryad_search...
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
        {"name": "Dryad_get_dataset", "arguments": {"dataset_id": dataset_id}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Dryad_get_dataset"]
