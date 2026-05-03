"""
GDC_list_files

List GDC files filtered by data_type and other fields. Use to identify downloadable artifacts (e....
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GDC_list_files(
    data_type: Optional[str] = None,
    size: Optional[int] = 10,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    List GDC files filtered by data_type and other fields. Use to identify downloadable artifacts (e....

    Parameters
    ----------
    data_type : str
        Data type filter (e.g., 'Gene Expression Quantification').
    size : int
        Number of results (1–100).
    offset : int
        Offset for pagination (0-based).
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

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {"data_type": data_type, "size": size, "offset": offset}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "GDC_list_files",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["GDC_list_files"]
