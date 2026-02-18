"""
WikiPathways_get_pathway_genes

Get all genes (as gene symbols) involved in a WikiPathways pathway. Returns the list of HGNC gene...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def WikiPathways_get_pathway_genes(
    pathway_id: str,
    code: Optional[str] = "H",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get all genes (as gene symbols) involved in a WikiPathways pathway. Returns the list of HGNC gene...

    Parameters
    ----------
    pathway_id : str
        WikiPathways pathway identifier. Examples: 'WP254' (Apoptosis, 88 genes), 'WP...
    code : str
        Identifier system code for returned genes. Options: 'H' (HGNC symbols, defaul...
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
            "name": "WikiPathways_get_pathway_genes",
            "arguments": {"pathway_id": pathway_id, "code": code},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["WikiPathways_get_pathway_genes"]
