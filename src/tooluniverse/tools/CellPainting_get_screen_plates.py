"""
CellPainting_get_screen_plates

Get the list of plates in a Cell Painting screen from the Image Data Resource (IDR). Returns plat...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def CellPainting_get_screen_plates(
    operation: str,
    screen_id: int,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get the list of plates in a Cell Painting screen from the Image Data Resource (IDR). Returns plat...

    Parameters
    ----------
    operation : str
        Operation type
    screen_id : int
        IDR screen identifier (e.g., 1251 for idr0016 screenA)
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

    return get_shared_client().run_one_function(
        {
            "name": "CellPainting_get_screen_plates",
            "arguments": {"operation": operation, "screen_id": screen_id},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["CellPainting_get_screen_plates"]
