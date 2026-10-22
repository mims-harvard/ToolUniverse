"""
Progenetix_list_cohorts

List Progenetix cohorts with IDs, names, sizes, types, and data types. Returns exact total_cohort...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Progenetix_list_cohorts(
    limit: Optional[int] = 10,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    List Progenetix cohorts with IDs, names, sizes, types, and data types. Returns exact total_cohort...

    Parameters
    ----------
    limit : int
        Maximum number of cohorts to return (default: 10).
    offset : int
        Zero-based offset in the complete cohort list. Continue with data.next_offset.
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
        k: v for k, v in {"limit": limit, "offset": offset}.items() if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Progenetix_list_cohorts",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Progenetix_list_cohorts"]
