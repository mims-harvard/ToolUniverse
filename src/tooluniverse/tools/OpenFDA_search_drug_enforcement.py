"""
OpenFDA_search_drug_enforcement

Search FDA drug recalls via openFDA. Record mode exposes exact totals and skip pagination; contin...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OpenFDA_search_drug_enforcement(
    search: Optional[str] = None,
    limit: Optional[int] = 5,
    skip: Optional[int] = None,
    count: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search FDA drug recalls via openFDA. Record mode exposes exact totals and skip pagination; contin...

    Parameters
    ----------
    search : str
        Lucene query for drug recalls (e.g., 'classification:"Class I"', 'status:Ongo...
    limit : int
        Record mode: max 100. Count mode: max 1000 terms.
    skip : int
        Record mode only. Number of recalls to skip; continue with metadata.next_skip...
    count : str
        Field to count by for frequency analysis. Must use the '.exact' keyword sub-f...
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
            "search": search,
            "limit": limit,
            "skip": skip,
            "count": count,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "OpenFDA_search_drug_enforcement",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OpenFDA_search_drug_enforcement"]
