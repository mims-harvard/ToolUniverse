"""
ChEMBL_get_target_activities

Get all activity data for a target by ChEMBL target ID. Returns bioactivity measurements (IC50, K...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ChEMBL_get_target_activities(
    target_chembl_id__exact: Optional[str] = None,
    limit: Optional[int] = 20,
    offset: Optional[int] = 0,
    target_chembl_id: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get all activity data for a target by ChEMBL target ID. Returns bioactivity measurements (IC50, K...

    Parameters
    ----------
    target_chembl_id__exact : str
        ChEMBL target ID (e.g., 'CHEMBL2074'). To find a target ID, use ChEMBL_search...
    limit : int

    offset : int

    target_chembl_id : str
        Alias for target_chembl_id__exact. ChEMBL target ID (e.g., CHEMBL213).
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
        for k, v in {
            "target_chembl_id__exact": target_chembl_id__exact,
            "limit": limit,
            "offset": offset,
            "target_chembl_id": target_chembl_id,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ChEMBL_get_target_activities",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ChEMBL_get_target_activities"]
