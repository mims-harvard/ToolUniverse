"""
GDC_get_mutation_frequency_by_project

Get per-project (per-cancer-type) somatic mutation frequency for a gene from NCI GDC. For each TC...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GDC_get_mutation_frequency_by_project(
    gene_symbol: Optional[str] = None,
    gene: Optional[str] = None,
    size: Optional[int] = 100,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get per-project (per-cancer-type) somatic mutation frequency for a gene from NCI GDC. For each TC...

    Parameters
    ----------
    gene_symbol : str
        Gene symbol (e.g., 'KRAS', 'TP53', 'EGFR')
    gene : str
        Gene symbol alias — alternative to gene_symbol
    size : int
        Maximum number of projects to return (default 100)
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
        for k, v in {"gene_symbol": gene_symbol, "gene": gene, "size": size}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "GDC_get_mutation_frequency_by_project",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["GDC_get_mutation_frequency_by_project"]
