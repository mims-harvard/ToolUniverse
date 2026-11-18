"""
HealthCanadaDPD_search_by_ingredient

Find drug products authorized in Canada that contain an active ingredient, from the Health Canada...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def HealthCanadaDPD_search_by_ingredient(
    ingredient: str,
    marketed_only: Optional[bool] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any] | dict[str, Any]:
    """
    Find drug products authorized in Canada that contain an active ingredient, from the Health Canada...

    Parameters
    ----------
    ingredient : str
        Active ingredient name or part of it, e.g. 'imatinib', 'acetaminophen'.
    marketed_only : bool
        Keep only products with status Marketed (default false: all statuses).
    limit : int
        Products to return (default 10; at most 25, or 100 with marketed_only).
    offset : int
        Matching products to skip, for paging (metadata.next_offset).
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    list[Any] | dict[str, Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "ingredient": ingredient,
            "marketed_only": marketed_only,
            "limit": limit,
            "offset": offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "HealthCanadaDPD_search_by_ingredient",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["HealthCanadaDPD_search_by_ingredient"]
