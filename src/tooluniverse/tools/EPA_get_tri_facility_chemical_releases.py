"""
EPA_get_tri_facility_chemical_releases

Get per-chemical, per-year EPA TRI reporting forms for one facility. Results use native Envirofac...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EPA_get_tri_facility_chemical_releases(
    tri_facility_id: str,
    limit: Optional[int] = None,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get per-chemical, per-year EPA TRI reporting forms for one facility. Results use native Envirofac...

    Parameters
    ----------
    tri_facility_id : str
        EPA TRI facility identifier, e.g. '15902CCKRN75BRI'. Obtain from EPA_search_t...
    limit : int
        Max reporting forms per page (default 10, max 100).
    offset : int
        Zero-based row offset; continue with metadata.next_offset.
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    Any
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "tri_facility_id": tri_facility_id,
            "limit": limit,
            "offset": offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "EPA_get_tri_facility_chemical_releases",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["EPA_get_tri_facility_chemical_releases"]
