"""
ChEMBL_get_assay_activities

Get all activity data for an assay by ChEMBL assay ID. Returns bioactivity measurements from the ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ChEMBL_get_assay_activities(
    assay_chembl_id__exact: str,
    limit: Optional[int] = 20,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get all activity data for an assay by ChEMBL assay ID. Returns bioactivity measurements from the ...

    Parameters
    ----------
    assay_chembl_id__exact : str
        ChEMBL assay ID (e.g., 'CHEMBL615117'). To find an assay ID, use ChEMBL_searc...
    limit : int

    offset : int

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
            "assay_chembl_id__exact": assay_chembl_id__exact,
            "limit": limit,
            "offset": offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ChEMBL_get_assay_activities",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ChEMBL_get_assay_activities"]
