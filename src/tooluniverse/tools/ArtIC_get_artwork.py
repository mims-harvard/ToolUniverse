"""
ArtIC_get_artwork

Get detailed information about a specific artwork from the Art Institute of Chicago collection by...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ArtIC_get_artwork(
    id: int,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get detailed information about a specific artwork from the Art Institute of Chicago collection by...

    Parameters
    ----------
    id : int
        Artwork ID from Art Institute of Chicago. Examples: 27992 (A Sunday on La Gra...
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
    _args = {k: v for k, v in {"id": id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "ArtIC_get_artwork",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ArtIC_get_artwork"]
