"""
NeuroVault_list_collection_images

List all statistical map images in a specific NeuroVault collection. Returns image metadata inclu...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NeuroVault_list_collection_images(
    collection_id: int,
    limit: Optional[int | Any] = None,
    offset: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    List all statistical map images in a specific NeuroVault collection. Returns image metadata inclu...

    Parameters
    ----------
    collection_id : int
        NeuroVault collection ID. Example: 457 (Human Connectome Project)
    limit : int | Any
        Maximum number of images to return (default 10, max 100)
    offset : int | Any
        Number of images to skip for pagination (default 0)
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
            "name": "NeuroVault_list_collection_images",
            "arguments": {
                "collection_id": collection_id,
                "limit": limit,
                "offset": offset,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["NeuroVault_list_collection_images"]
