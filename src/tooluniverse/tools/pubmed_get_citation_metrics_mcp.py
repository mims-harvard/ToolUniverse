"""
pubmed_get_citation_metrics_mcp

Get NIH iCite citation metrics (RCR, percentile) for articles.
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def pubmed_get_citation_metrics_mcp(
    pmids: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get NIH iCite citation metrics (RCR, percentile) for articles.

    Parameters
    ----------
    pmids : str
        Comma-separated PMIDs
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
        {"name": "pubmed_get_citation_metrics_mcp", "arguments": {"pmids": pmids}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["pubmed_get_citation_metrics_mcp"]
