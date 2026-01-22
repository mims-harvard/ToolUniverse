"""
pubmed_get_compound_literature_mcp

Get PubMed articles related to a specific compound.
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def pubmed_get_compound_literature_mcp(
    cid: str,
    limit: Optional[int] = 20,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get PubMed articles related to a specific compound.

    Parameters
    ----------
    cid : str

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
            "name": "pubmed_get_compound_literature_mcp",
            "arguments": {"cid": cid, "limit": limit},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["pubmed_get_compound_literature_mcp"]
