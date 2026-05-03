"""
NCIDrugDict_search

Search the NCI (National Cancer Institute) Drug Dictionary for cancer drugs, agents, and therapeu...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NCIDrugDict_search(
    query: str,
    matchType: Optional[str] = "Begins",
    size: Optional[int] = 10,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search the NCI (National Cancer Institute) Drug Dictionary for cancer drugs, agents, and therapeu...

    Parameters
    ----------
    query : str
        Drug name to search for (e.g., 'imatinib', 'pembrolizumab', 'tamoxifen', 'cis...
    matchType : str
        Match type: 'Begins' (starts with) or 'Contains' (default: Begins)
    size : int
        Number of results to return (default 10)
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
        for k, v in {"query": query, "matchType": matchType, "size": size}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "NCIDrugDict_search",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["NCIDrugDict_search"]
