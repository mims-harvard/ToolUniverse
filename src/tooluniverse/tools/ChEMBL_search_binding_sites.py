"""
ChEMBL_search_binding_sites

Search binding sites by target, site name, or other criteria.
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ChEMBL_search_binding_sites(
    target_chembl_id: Optional[str] = None,
    site_name__contains: Optional[str] = None,
    limit: Optional[int] = 20,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search binding sites by target, site name, or other criteria.

    Parameters
    ----------
    target_chembl_id : str
        Filter by target ChEMBL ID
    site_name__contains : str
        Filter by site name (contains)
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
            "site_name__contains": site_name__contains,
            "limit": limit,
            "offset": offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ChEMBL_search_binding_sites",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ChEMBL_search_binding_sites"]
