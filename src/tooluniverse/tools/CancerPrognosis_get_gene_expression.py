"""
CancerPrognosis_get_gene_expression

Fetch gene expression values (RNA-seq) for a specific gene across cancer samples in a TCGA or cBi...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def CancerPrognosis_get_gene_expression(
    operation: Optional[str] = None,
    cancer: Optional[str] = None,
    cancer_type: Optional[str] = None,
    study_id: Optional[str] = None,
    gene: Optional[str] = None,
    gene_symbol: Optional[str] = None,
    gene_name: Optional[str] = None,
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
        TCGA cancer type abbreviation (e.g., 'BRCA', 'LUAD', 'COADREAD') or cBioPorta...
    cancer_type : str
        Alias for cancer. TCGA cancer type (e.g., 'BRCA', 'LUAD', 'COADREAD') or cBio...
    study_id : str
        Alias for cancer. cBioPortal study ID (e.g., 'brca_tcga', 'luad_tcga').
    gene : str
        Gene symbol (e.g., 'TP53', 'BRCA1', 'EGFR', 'CD8A')
    gene_symbol : str
        Alias for gene. Gene symbol (e.g., 'TP53', 'BRCA1', 'EGFR').
    gene_name : str
        Alias for gene. Gene symbol or name (e.g., 'TP53', 'BRCA1').
    max_samples : int | Any
        Upper bound on sample records to return (default 500, max 2000). Actual count...
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
        for k, v in {
            "operation": operation,
            "cancer": cancer,
            "cancer_type": cancer_type,
            "study_id": study_id,
            "gene": gene,
            "gene_symbol": gene_symbol,
            "gene_name": gene_name,
            "max_samples": max_samples,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "CancerPrognosis_get_gene_expression",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["CancerPrognosis_get_gene_expression"]
