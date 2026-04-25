"""
OpenNeuro_get_dataset_snapshots

Get all version snapshots of a specific dataset on OpenNeuro. Returns snapshot tags, creation dat...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OpenNeuro_get_dataset_snapshots(
    datasetId: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get all version snapshots of a specific dataset on OpenNeuro. Returns snapshot tags, creation dat...

    Parameters
    ----------
    datasetId : str
        OpenNeuro dataset ID (e.g., 'ds000114')
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
        "datasetId": datasetId
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "OpenNeuro_get_dataset_snapshots",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["OpenNeuro_get_dataset_snapshots"]
