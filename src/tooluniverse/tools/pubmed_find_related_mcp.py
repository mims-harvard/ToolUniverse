"""
pubmed_find_related_mcp

Find articles related to a given paper using PubMed's Similar Articles algorithm.
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def pubmed_find_related_mcp(
    pmid: str,
    limit: Optional[int] = 10,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Find articles related to a given paper using PubMed's Similar Articles algorithm.

    Parameters
    ----------
    pmid : str
        Source article PMID
    limit : int

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

    return get_shared_client().run_one_function(
        {
            "name": "pubmed_find_related_mcp",
            "arguments": {"pmid": pmid, "limit": limit},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["pubmed_find_related_mcp"]
