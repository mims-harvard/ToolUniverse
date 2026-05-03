"""
mesh_get_subjects_by_subject_id

Find MeSH (Medical Subject Heading) subjects with a matching subject ID (also called Descriptor UI).
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def mesh_get_subjects_by_subject_id(
    query: str,
    case_sensitive: bool,
    exact_match: bool,
    limit: int,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Find MeSH (Medical Subject Heading) subjects with a matching subject ID (also called Descriptor UI).

    Parameters
    ----------
    query : str
        Query ID to search for among the MeSH subject IDs
    case_sensitive : bool
        Select True to perform a case-sensitive search for the query
    exact_match : bool
        Select True to require an exact match for the query
    limit : int
        Maximum number of results to return
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
            "query": query,
            "case_sensitive": case_sensitive,
            "exact_match": exact_match,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "mesh_get_subjects_by_subject_id",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["mesh_get_subjects_by_subject_id"]
