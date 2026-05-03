"""
ChEMBL_search_cell_lines

Search cell lines used in ChEMBL assays.
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ChEMBL_search_cell_lines(
    cell_chembl_id: Optional[str] = None,
    cell_name__contains: Optional[str] = None,
    limit: Optional[int] = 20,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search cell lines used in ChEMBL assays.

    Parameters
    ----------
    cell_chembl_id : str
        Filter by cell line ChEMBL ID
    cell_name__contains : str
        Filter by cell line name (contains)
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
            "cell_chembl_id": cell_chembl_id,
            "cell_name__contains": cell_name__contains,
            "limit": limit,
            "offset": offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ChEMBL_search_cell_lines",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ChEMBL_search_cell_lines"]
