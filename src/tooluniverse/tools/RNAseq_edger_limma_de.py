"""
RNAseq_edger_limma_de

Bulk RNA-seq differential expression via edgeR (QL-F) or limma-voom on a count matrix + sample me...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def RNAseq_edger_limma_de(
    counts_file: str,
    metadata_file: str,
    contrast: str,
    method: str,
    design: Optional[str] = None,
    lfc_threshold: Optional[float] = None,
    fdr_threshold: Optional[float] = None,
    expr_threshold: Optional[float] = None,
    exclude_samples: Optional[str] = None,
    report_genes: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Bulk RNA-seq differential expression via edgeR (QL-F) or limma-voom on a count matrix + sample me...

    Parameters
    ----------
    counts_file : str
        Path to counts CSV (genes x samples; first column = gene IDs)
    metadata_file : str
        Path to sample metadata CSV (one row per sample)
    design : str
        Design formula, e.g. '~ condition' or '~ batch + condition' (default '~ condi...
    contrast : str
        Contrast as 'factor,level1,level2' (tests level1 vs level2)
    method : str
        DE framework: 'edger' (QL-F) or 'limma' (limma-voom)
    lfc_threshold : float
        abs(logFC) threshold for the sig sets (default 0.5)
    fdr_threshold : float
        FDR (adjusted p) threshold (default 0.05)
    expr_threshold : float
        Expression threshold (logCPM/AveExpr) for the strict set (default 0)
    exclude_samples : str
        Comma-separated sample IDs to drop before analysis
    report_genes : str
        Comma-separated gene IDs to report individual logFC/FDR for
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
        for k, v in {
            "counts_file": counts_file,
            "metadata_file": metadata_file,
            "design": design,
            "contrast": contrast,
            "method": method,
            "lfc_threshold": lfc_threshold,
            "fdr_threshold": fdr_threshold,
            "expr_threshold": expr_threshold,
            "exclude_samples": exclude_samples,
            "report_genes": report_genes,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "RNAseq_edger_limma_de",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["RNAseq_edger_limma_de"]
