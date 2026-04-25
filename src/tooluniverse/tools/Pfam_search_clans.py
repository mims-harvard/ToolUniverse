"""
Pfam_search_clans

Search and list Pfam clans (superfamilies) by keyword. Pfam clans group together related Pfam fam...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Pfam_search_clans(
    query: Optional[str] = None,
    max_results: Optional[int] = 20,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search and list Pfam clans (superfamilies) by keyword. Pfam clans group together related Pfam fam...

    Parameters
    ----------
    query : str
        Search keyword for clan name. Examples: 'kinase', 'EGF', 'RRM', 'immunoglobul...
    max_results : int
        Maximum number of clans to return (default 20, max 100).
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
    _args = {k: v for k, v in {
        "query": query,
                "max_results": max_results
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "Pfam_search_clans",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["Pfam_search_clans"]
