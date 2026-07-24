"""
run_deseq2_analysis

Run R DESeq2 differential expression analysis on a count matrix + metadata. Returns gene counts, ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def run_deseq2_analysis(
    operation: str,
    counts_file: Optional[str] = None,
    metadata_file: Optional[str] = None,
    design: Optional[str] = None,
    contrast: Optional[str] = None,
    ref_level: Optional[str] = None,
    alpha: Optional[float] = None,
    lfc_threshold: Optional[float] = None,
    lfc_shrinkage: Optional[bool] = None,
    refit_cooks: Optional[bool] = None,
    gene_list_file: Optional[str] = None,
    background_file: Optional[str] = None,
    ontology: Optional[str] = None,
    simplify_cutoff: Optional[float] = None,
    id_type: Optional[str] = None,
    organism: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Run R DESeq2 differential expression analysis on a count matrix + metadata. Returns gene counts, ...

    Parameters
    ----------
    operation : str
        deseq2: differential expression, enrichgo: GO enrichment with clusterProfiler...
    counts_file : str
        Path to CSV count matrix (genes x samples, first column = gene IDs)
    metadata_file : str
        Path to CSV metadata (samples x variables, must include design variables)
    design : str
        R formula string (e.g., '~ condition', '~ Replicate + Media + Strain')
    contrast : str
        Contrast specification: 'variable, level, reference' (e.g., 'Strain, 97, 1')
    ref_level : str
        Reference level: 'variable, level' (e.g., 'condition, Control')
    alpha : float
        Significance threshold (default: 0.05)
    lfc_threshold : float
        Log2 fold change threshold for filtering (default: 0 = no filter)
    lfc_shrinkage : bool
        Apply apeglm LFC shrinkage (default: false)
    refit_cooks : bool
        Refit Cook's outliers (default: false)
    gene_list_file : str
        For enrichgo: path to file with one gene ID per line
    background_file : str
        For enrichgo: path to background gene list file
    ontology : str
        For enrichgo: GO ontology (BP, CC, MF). Default: BP
    simplify_cutoff : float
        For enrichgo: simplify similarity cutoff (default: 0.7)
    id_type : str
        Gene ID type (ENSEMBL, ENTREZID, SYMBOL). Default: ENSEMBL
    organism : str
        Organism annotation DB (org.Hs.eg.db, org.Mm.eg.db). Default: org.Hs.eg.db
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
            "operation": operation,
            "counts_file": counts_file,
            "metadata_file": metadata_file,
            "design": design,
            "contrast": contrast,
            "ref_level": ref_level,
            "alpha": alpha,
            "lfc_threshold": lfc_threshold,
            "lfc_shrinkage": lfc_shrinkage,
            "refit_cooks": refit_cooks,
            "gene_list_file": gene_list_file,
            "background_file": background_file,
            "ontology": ontology,
            "simplify_cutoff": simplify_cutoff,
            "id_type": id_type,
            "organism": organism,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "run_deseq2_analysis",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["run_deseq2_analysis"]
