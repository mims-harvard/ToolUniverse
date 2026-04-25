"""
TIMER2_gene_correlation

Analyze Spearman correlation between two genes across TCGA cancer samples using cBioPortal data. ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def TIMER2_gene_correlation(
    operation: str,
    cancer: str,
    gene1: str,
    gene2: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Analyze Spearman correlation between two genes across TCGA cancer samples using cBioPortal data. ...

    Parameters
    ----------
    operation : str
        Operation type
    cancer : str
        TCGA cancer type (e.g., 'BRCA', 'LUAD')
    gene1 : str
        First gene symbol (e.g., 'CD8A')
    gene2 : str
        Second gene symbol (e.g., 'PDCD1')
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
    _args = {k: v for k, v in {
        "operation": operation,
                "cancer": cancer,
                "gene1": gene1,
                "gene2": gene2
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "TIMER2_gene_correlation",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["TIMER2_gene_correlation"]
