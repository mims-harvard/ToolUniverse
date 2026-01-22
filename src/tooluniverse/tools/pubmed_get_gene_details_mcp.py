"""
pubmed_get_gene_details_mcp

Get detailed information about a specific gene by NCBI Gene ID.
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def pubmed_get_gene_details_mcp(
    gene_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get detailed information about a specific gene by NCBI Gene ID.

    Parameters
    ----------
    gene_id : str
        NCBI Gene ID (e.g., '672' for BRCA1)
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
        {"name": "pubmed_get_gene_details_mcp", "arguments": {"gene_id": gene_id}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["pubmed_get_gene_details_mcp"]
