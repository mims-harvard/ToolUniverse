"""
CancerPrognosis_get_gene_expression

Fetch gene expression values (RNA-seq) for a specific gene across cancer samples in a TCGA or cBi...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def CancerPrognosis_get_gene_expression(
    operation: str,
    cancer: str,
    gene: str,
    max_samples: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Fetch gene expression values (RNA-seq) for a specific gene across cancer samples in a TCGA or cBi...

    Parameters
    ----------
    operation : str
        Operation type
    cancer : str
        TCGA cancer type abbreviation (e.g., 'BRCA', 'LUAD') or cBioPortal study ID
    gene : str
        Gene symbol (e.g., 'TP53', 'BRCA1', 'EGFR', 'CD8A')
    max_samples : int | Any
        Maximum number of sample records to return (default 500, max 2000)
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
            "name": "CancerPrognosis_get_gene_expression",
            "arguments": {
                "operation": operation,
                "cancer": cancer,
                "gene": gene,
                "max_samples": max_samples,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["CancerPrognosis_get_gene_expression"]
