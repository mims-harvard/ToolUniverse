"""
SwissLipids_search

Search SwissLipids (swisslipids.org, SIB Swiss Institute of Bioinformatics) for lipids by name or...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def SwissLipids_search(
    query: str,
    limit: Optional[int] = 10,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search SwissLipids (swisslipids.org, SIB Swiss Institute of Bioinformatics) for lipids by name or...

    Parameters
    ----------
    query : str
        Lipid name or shorthand abbreviation, e.g. 'PC(16:0/18:1)', 'sphingomyelin'.
    limit : int
        Maximum number of results (1-100, default 10).
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
    _args = {k: v for k, v in {"query": query, "limit": limit}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "SwissLipids_search",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["SwissLipids_search"]
