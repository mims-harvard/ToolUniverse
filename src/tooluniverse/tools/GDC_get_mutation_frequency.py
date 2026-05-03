"""
GDC_get_mutation_frequency

Get pan-cancer mutation frequency statistics for a gene across all TCGA/GDC cancer projects. Retu...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GDC_get_mutation_frequency(
    gene_symbol: str,
    gene: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get pan-cancer mutation frequency statistics for a gene across all TCGA/GDC cancer projects. Retu...

    Parameters
    ----------
    gene_symbol : str
        Gene symbol (e.g., 'TP53', 'KRAS', 'EGFR')
    gene : str
        Gene symbol alias — alternative to gene_symbol
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    dict[str, Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {"gene_symbol": gene_symbol, "gene": gene}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "GDC_get_mutation_frequency",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["GDC_get_mutation_frequency"]
