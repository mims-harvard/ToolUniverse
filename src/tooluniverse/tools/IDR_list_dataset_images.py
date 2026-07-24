"""
IDR_list_dataset_images

List the individual images contained in a specific IDR (Image Data Resource) dataset, drilling do...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def IDR_list_dataset_images(
    dataset_id: int,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    List the individual images contained in a specific IDR (Image Data Resource) dataset, drilling do...

    Parameters
    ----------
    dataset_id : int
        IDR dataset ID (e.g. 51). Obtain from IDR_get_study_datasets.
    limit : int
        Maximum number of images to return (default 25, max 1000).
    offset : int
        Offset for pagination.
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
        for k, v in {"dataset_id": dataset_id, "limit": limit, "offset": offset}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "IDR_list_dataset_images",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["IDR_list_dataset_images"]
