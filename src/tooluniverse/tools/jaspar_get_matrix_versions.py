"""
jaspar_get_matrix_versions

List all versions available for a JASPAR matrix base ID (e.g., base_id MA0002). This is useful fo...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def jaspar_get_matrix_versions(
    base_id: str,
    page: Optional[int] = 1,
    page_size: Optional[int] = 20,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    List all versions available for a JASPAR matrix base ID (e.g., base_id MA0002). This is useful fo...

    Parameters
    ----------
    base_id : str
        JASPAR base matrix ID without version (e.g., 'MA0002'). You can get `base_id`...
    page : int
        Page number (1-based).
    page_size : int
        Results per page.
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
        for k, v in {"base_id": base_id, "page": page, "page_size": page_size}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "jaspar_get_matrix_versions",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["jaspar_get_matrix_versions"]
