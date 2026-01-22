"""
pubmed_generate_queries_mcp

Generate optimized PubMed search queries using MeSH vocabulary and synonyms.
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def pubmed_generate_queries_mcp(
    topic: str,
    strategy: Optional[str] = "comprehensive",
    check_spelling: Optional[bool] = True,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Generate optimized PubMed search queries using MeSH vocabulary and synonyms.

    Parameters
    ----------
    topic : str
        Research topic in natural language
    strategy : str

    check_spelling : bool

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
            "name": "pubmed_generate_queries_mcp",
            "arguments": {
                "topic": topic,
                "strategy": strategy,
                "check_spelling": check_spelling,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["pubmed_generate_queries_mcp"]
