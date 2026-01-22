"""
pubmed_build_citation_tree_mcp

Build citation network graph from a seed article. Supports cytoscape, g6, d3, vis, graphml, merma...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def pubmed_build_citation_tree_mcp(
    pmid: str,
    depth: Optional[int] = 1,
    limit_per_level: Optional[int] = 5,
    direction: Optional[str] = "both",
    format: Optional[str] = "cytoscape",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Build citation network graph from a seed article. Supports cytoscape, g6, d3, vis, graphml, merma...

    Parameters
    ----------
    pmid : str

    depth : int

    limit_per_level : int

    direction : str

    format : str

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
            "name": "pubmed_build_citation_tree_mcp",
            "arguments": {
                "pmid": pmid,
                "depth": depth,
                "limit_per_level": limit_per_level,
                "direction": direction,
                "format": format,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["pubmed_build_citation_tree_mcp"]
