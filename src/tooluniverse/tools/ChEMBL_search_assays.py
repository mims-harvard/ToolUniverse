"""
ChEMBL_search_assays

Search assays by various criteria including assay type, target, organism. Use this tool to find a...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ChEMBL_search_assays(
    assay_chembl_id: Optional[str] = None,
    assay_type: Optional[str] = None,
    target_chembl_id: Optional[str] = None,
    fields: Optional[list[str]] = None,
    limit: Optional[int] = 20,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search assays by various criteria including assay type, target, organism. Use this tool to find a...

    Parameters
    ----------
    assay_chembl_id : str
        Filter by assay ChEMBL ID
    assay_type : str
        Filter by assay type (e.g., 'B', 'F', 'A')
    target_chembl_id : str
        Filter by target ChEMBL ID
    fields : list[str]
        Optional list of ChEMBL assay fields to include in each returned assay object...
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
            "assay_chembl_id": assay_chembl_id,
            "assay_type": assay_type,
            "target_chembl_id": target_chembl_id,
            "fields": fields,
            "limit": limit,
            "offset": offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ChEMBL_search_assays",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ChEMBL_search_assays"]
