"""
LINCS_list_libraries

List and optionally keyword-filter the complete LINCS SigCom library catalog. Filtering is applie...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def LINCS_list_libraries(
    keyword: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    List and optionally keyword-filter the complete LINCS SigCom library catalog. Filtering is applie...

    Parameters
    ----------
    keyword : str
        Optional keyword to filter libraries (case-insensitive). Examples: 'L1000', '...
    limit : int
        Libraries per page (1-1000, default 50).
    offset : int
        Zero-based offset into the filtered library list. Continue with metadata.next...
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
    _args = {
        k: v
        for k, v in {"keyword": keyword, "limit": limit, "offset": offset}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "LINCS_list_libraries",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["LINCS_list_libraries"]
