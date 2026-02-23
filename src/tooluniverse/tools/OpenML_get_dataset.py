"""
OpenML_get_dataset

Get detailed metadata for a specific OpenML dataset by its numeric ID. Returns comprehensive info...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OpenML_get_dataset(
    data_id: int,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get detailed metadata for a specific OpenML dataset by its numeric ID. Returns comprehensive info...

    Parameters
    ----------
    data_id : int
        OpenML dataset ID number (e.g., 61 for iris, 554 for MNIST, 31 for credit-g)....
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
        {"name": "OpenML_get_dataset", "arguments": {"data_id": data_id}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OpenML_get_dataset"]
