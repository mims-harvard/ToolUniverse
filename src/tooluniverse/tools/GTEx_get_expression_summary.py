"""
GTEx_get_expression_summary

Summarize tissue-specific expression (e.g., median TPM) for a gene across GTEx tissues. Accepts g...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GTEx_get_expression_summary(
    gene_symbol: Optional[str] = None,
    ensembl_gene_id: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Summarize tissue-specific expression (e.g., median TPM) for a gene across GTEx tissues. Accepts g...

    Parameters
    ----------
    gene_symbol : str
        Gene symbol (e.g., 'TP53', 'BRCA1', 'FBN1'). Auto-resolved to versioned GENCO...
    ensembl_gene_id : str
        Ensembl gene identifier (e.g., 'ENSG00000141510' or 'ENSG00000141510.11'). Us...
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
            "gene_symbol": gene_symbol,
            "ensembl_gene_id": ensembl_gene_id,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "GTEx_get_expression_summary",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["GTEx_get_expression_summary"]
