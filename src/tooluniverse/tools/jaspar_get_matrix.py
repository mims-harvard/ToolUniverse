"""
jaspar_get_matrix

Get full details for a single JASPAR matrix by `matrix_id` (e.g., MA0002.2). Returns metadata plu...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def jaspar_get_matrix(
    matrix_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get full details for a single JASPAR matrix by `matrix_id` (e.g., MA0002.2). Returns metadata plu...

    Parameters
    ----------
    matrix_id : str
        JASPAR matrix ID (e.g., 'MA0002.2'). You can discover IDs with `JASPAR_get_tr...
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
    _args = {k: v for k, v in {"matrix_id": matrix_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "jaspar_get_matrix",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["jaspar_get_matrix"]
