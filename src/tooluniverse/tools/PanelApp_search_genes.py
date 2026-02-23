"""
PanelApp_search_genes

Search for a gene across all Genomics England PanelApp panels to find which clinical testing pane...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PanelApp_search_genes(
    gene_symbol: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search for a gene across all Genomics England PanelApp panels to find which clinical testing pane...

    Parameters
    ----------
    gene_symbol : str
        Gene symbol to search across all panels (e.g., 'TP53', 'BRCA1', 'EGFR', 'MLH1')
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
        {"name": "PanelApp_search_genes", "arguments": {"gene_symbol": gene_symbol}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PanelApp_search_genes"]
