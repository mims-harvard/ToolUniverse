"""
PharmacoDB_get_molecular_profiling

Get the per-cell-line molecular profiling inventory from PharmacoDB: which molecular data types (...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PharmacoDB_get_molecular_profiling(
    operation: str,
    cell_line_name: Optional[str] = None,
    cell_line_id: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get the per-cell-line molecular profiling inventory from PharmacoDB: which molecular data types (...

    Parameters
    ----------
    operation : str
        Operation type
    cell_line_name : str
        Cancer cell line name (e.g., 'MCF-7', 'A549'). Mutually exclusive with cell_l...
    cell_line_id : int
        PharmacoDB cell line database ID (e.g., 273 for MCF-7). Mutually exclusive wi...
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
        for k, v in {
            "operation": operation,
            "cell_line_name": cell_line_name,
            "cell_line_id": cell_line_id,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "PharmacoDB_get_molecular_profiling",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PharmacoDB_get_molecular_profiling"]
