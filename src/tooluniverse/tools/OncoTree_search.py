"""
OncoTree_search

Search the OncoTree cancer type ontology by name, code, main type, or tissue. OncoTree is a hiera...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OncoTree_search(
    query: str,
    field: Optional[str] = "name",
    exact_match: Optional[bool] = False,
    version: Optional[str] = "oncotree_latest_stable",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search the OncoTree cancer type ontology by name, code, main type, or tissue. OncoTree is a hiera...

    Parameters
    ----------
    query : str
        Search term. Interpreted according to the 'field' parameter. Examples: 'breas...
    field : str
        Field to search in. One of: 'name' (cancer type name), 'code' (OncoTree code)...
    exact_match : bool
        If true, requires exact match. If false (default), performs substring/prefix ...
    version : str
        OncoTree version identifier. Use 'oncotree_latest_stable' (default) for the c...
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
            "query": query,
            "field": field,
            "exact_match": exact_match,
            "version": version,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "OncoTree_search",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OncoTree_search"]
