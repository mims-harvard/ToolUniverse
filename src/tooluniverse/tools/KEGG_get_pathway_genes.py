"""
KEGG_get_pathway_genes

Get all genes in a KEGG pathway. Returns gene IDs for all member genes of a specific pathway. Exa...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def KEGG_get_pathway_genes(
    pathway_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get all genes in a KEGG pathway. Returns gene IDs for all member genes of a specific pathway. Exa...

    Parameters
    ----------
    pathway_id : str
        KEGG pathway identifier (e.g., 'hsa04115' for p53 signaling pathway, 'hsa0411...
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
        {"name": "KEGG_get_pathway_genes", "arguments": {"pathway_id": pathway_id}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["KEGG_get_pathway_genes"]
