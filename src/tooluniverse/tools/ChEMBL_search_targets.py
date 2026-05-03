"""
ChEMBL_search_targets

Search targets by name, organism, target type, or other criteria. Use this tool to find target Ch...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ChEMBL_search_targets(
    target_chembl_id: Optional[str] = None,
    pref_name__contains: Optional[str] = None,
    organism: Optional[str] = None,
    target_type: Optional[str] = None,
    fields: Optional[list[str]] = None,
    limit: Optional[int] = 20,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search targets by name, organism, target type, or other criteria. Use this tool to find target Ch...

    Parameters
    ----------
    target_chembl_id : str
        Filter by target ChEMBL ID
    pref_name__contains : str
        Filter by target name (contains)
    organism : str
        Filter by organism (e.g., 'Homo sapiens')
    target_type : str
        Filter by target type (e.g., 'SINGLE PROTEIN', 'PROTEIN COMPLEX')
    fields : list[str]
        Optional list of ChEMBL target fields to include in each returned target obje...
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
            "target_chembl_id": target_chembl_id,
            "pref_name__contains": pref_name__contains,
            "organism": organism,
            "target_type": target_type,
            "fields": fields,
            "limit": limit,
            "offset": offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ChEMBL_search_targets",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ChEMBL_search_targets"]
