"""
CellPainting_get_well_data

Get well-level metadata and image links for a specific plate in a Cell Painting experiment from t...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def CellPainting_get_well_data(
    operation: str,
    plate_id: int,
    limit: Optional[int] = 20,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Get well-level metadata and image links for a specific plate in a Cell Painting experiment from t...

    Parameters
    ----------
    operation : str
        Operation type
    plate_id : int
        IDR plate identifier (e.g., 5104 for a plate in idr0016 screenA)
    limit : int
        Maximum number of wells to return (default 20)
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    list[Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {k: v for k, v in {
        "operation": operation,
                "plate_id": plate_id,
                "limit": limit
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "CellPainting_get_well_data",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["CellPainting_get_well_data"]
