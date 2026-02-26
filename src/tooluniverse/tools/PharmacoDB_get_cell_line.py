"""
PharmacoDB_get_cell_line

Get detailed information about a cancer cell line from PharmacoDB, including tissue of origin, di...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PharmacoDB_get_cell_line(
    operation: str,
    cell_name: Optional[str | Any] = None,
    cell_id: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get detailed information about a cancer cell line from PharmacoDB, including tissue of origin, di...

    Parameters
    ----------
    operation : str
        Operation type
    cell_name : str | Any
        Cell line name (e.g., 'MCF-7', 'A549', 'HeLa'). Mutually exclusive with cell_id.
    cell_id : int | Any
        PharmacoDB cell line database ID (e.g., 273 for MCF-7). Mutually exclusive wi...
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
            "name": "PharmacoDB_get_cell_line",
            "arguments": {
                "operation": operation,
                "cell_name": cell_name,
                "cell_id": cell_id,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PharmacoDB_get_cell_line"]
