"""
NeuroVault_get_image

Get detailed metadata for a specific brain statistical map image in NeuroVault by image ID. Retur...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NeuroVault_get_image(
    image_id: int,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get detailed metadata for a specific brain statistical map image in NeuroVault by image ID. Retur...

    Parameters
    ----------
    image_id : int
        NeuroVault image ID. Examples: 3128 (HCP emotion task Z map), 946 (pain T map)
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
        {"name": "NeuroVault_get_image", "arguments": {"image_id": image_id}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["NeuroVault_get_image"]
