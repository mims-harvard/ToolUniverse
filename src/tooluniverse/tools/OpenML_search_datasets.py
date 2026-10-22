"""
OpenML_search_datasets

List/discover OpenML benchmark datasets in catalog order. This endpoint does not perform keyword ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OpenML_search_datasets(
    limit: Optional[int] = 20,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    List/discover OpenML benchmark datasets in catalog order. This endpoint does not perform keyword ...

    Parameters
    ----------
    limit : int
        Datasets per page (default 20, max 10000).
    offset : int
        Zero-based dataset offset. Continue with metadata.next_offset while metadata....
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
        k: v for k, v in {"limit": limit, "offset": offset}.items() if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "OpenML_search_datasets",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OpenML_search_datasets"]
