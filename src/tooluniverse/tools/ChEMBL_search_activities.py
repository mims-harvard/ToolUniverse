"""
ChEMBL_search_activities

Search activity data by molecule, target, assay, or activity values. Supports filtering by IC50, ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ChEMBL_search_activities(
    molecule_chembl_id: Optional[str] = None,
    target_chembl_id: Optional[str] = None,
    assay_chembl_id: Optional[str] = None,
    standard_type: Optional[str] = None,
    standard_value__lte: Optional[float] = None,
    standard_value__gte: Optional[float] = None,
    fields: Optional[list[str]] = None,
    limit: Optional[int] = 20,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search activity data by molecule, target, assay, or activity values. Supports filtering by IC50, ...

    Parameters
    ----------
    molecule_chembl_id : str
        Filter by molecule ChEMBL ID
    target_chembl_id : str
        Filter by target ChEMBL ID
    assay_chembl_id : str
        Filter by assay ChEMBL ID
    standard_type : str
        Filter by activity type (e.g., 'IC50', 'Ki', 'EC50')
    standard_value__lte : float
        Filter by maximum activity value
    standard_value__gte : float
        Filter by minimum activity value
    fields : list[str]
        Optional list of ChEMBL activity fields to include in each returned activity ...
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
            "molecule_chembl_id": molecule_chembl_id,
            "target_chembl_id": target_chembl_id,
            "assay_chembl_id": assay_chembl_id,
            "standard_type": standard_type,
            "standard_value__lte": standard_value__lte,
            "standard_value__gte": standard_value__gte,
            "fields": fields,
            "limit": limit,
            "offset": offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ChEMBL_search_activities",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ChEMBL_search_activities"]
