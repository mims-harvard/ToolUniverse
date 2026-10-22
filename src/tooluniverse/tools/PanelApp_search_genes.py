"""
PanelApp_search_genes

Search a gene across Genomics England PanelApp panels with case-normalized symbols and page metad...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PanelApp_search_genes(
    gene_symbol: str,
    page: Optional[int] = 1,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search a gene across Genomics England PanelApp panels with case-normalized symbols and page metad...

    Parameters
    ----------
    gene_symbol : str
        Gene symbol to search across all panels (e.g., 'TP53', 'BRCA1', 'EGFR', 'MLH1')
    page : int
        One-based PanelApp response page. Continue with metadata.next_page when avail...
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

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {"gene_symbol": gene_symbol, "page": page}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "PanelApp_search_genes",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PanelApp_search_genes"]
