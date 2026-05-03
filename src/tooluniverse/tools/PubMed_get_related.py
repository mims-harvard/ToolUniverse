"""
PubMed_get_related

Get related PubMed articles for a specific PMID using elink. Returns a list of computationally si...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PubMed_get_related(
    pmid: str,
    limit: Optional[int] = 20,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get related PubMed articles for a specific PMID using elink. Returns a list of computationally si...

    Parameters
    ----------
    pmid : str
        PubMed ID (PMID) for which to find related articles (e.g., '20210808', '19879...
    limit : int
        Maximum number of related articles to return (default: 20, max: 100).
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
    _args = {k: v for k, v in {"pmid": pmid, "limit": limit}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "PubMed_get_related",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PubMed_get_related"]
