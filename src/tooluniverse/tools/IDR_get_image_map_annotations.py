"""
IDR_get_image_map_annotations

Fetch the map (key-value) annotations attached to a specific IDR image. Map annotations carry the...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def IDR_get_image_map_annotations(
    image: int,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Fetch the map (key-value) annotations attached to a specific IDR image. Map annotations carry the...

    Parameters
    ----------
    image : int
        IDR image ID (e.g. 1884807). Obtain from IDR_list_dataset_images.
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
    _args = {k: v for k, v in {"image": image}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "IDR_get_image_map_annotations",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["IDR_get_image_map_annotations"]
