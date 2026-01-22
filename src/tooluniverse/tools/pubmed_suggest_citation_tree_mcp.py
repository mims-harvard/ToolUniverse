"""
pubmed_suggest_citation_tree_mcp

Suggest optimal citation tree parameters based on article characteristics.
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def pubmed_suggest_citation_tree_mcp(
    pmid: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Suggest optimal citation tree parameters based on article characteristics.

    Parameters
    ----------
    pmid : str

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
        {"name": "pubmed_suggest_citation_tree_mcp", "arguments": {"pmid": pmid}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["pubmed_suggest_citation_tree_mcp"]
