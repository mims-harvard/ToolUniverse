"""
REBASE_search_by_site

Find restriction enzymes by what they recognize. Give site to find every enzyme reading an exact ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def REBASE_search_by_site(
    site: Optional[str] = None,
    sequence: Optional[str] = None,
    only_commercial: Optional[bool] = None,
    limit: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Find restriction enzymes by what they recognize. Give site to find every enzyme reading an exact ...

    Parameters
    ----------
    site : str
        Exact recognition sequence to match, e.g. 'GAATTC'. Mutually exclusive with s...
    sequence : str
        DNA sequence to find cutters for, e.g. a plasmid region. Mutually exclusive w...
    only_commercial : bool
        If true, return only commercially available enzymes.
    limit : int
        Maximum enzymes to return (default 25, max 200).
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
            "site": site,
            "sequence": sequence,
            "only_commercial": only_commercial,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "REBASE_search_by_site",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["REBASE_search_by_site"]
