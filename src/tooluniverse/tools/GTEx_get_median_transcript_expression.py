"""
GTEx_get_median_transcript_expression

Get GTEx transcript/isoform-level median expression: per-transcript (ENST) median TPM across tiss...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GTEx_get_median_transcript_expression(
    operation: Optional[str] = None,
    gencode_id: Optional[str | list[str]] = None,
    gene_symbol: Optional[str] = None,
    tissue_site_detail_id: Optional[list[str]] = None,
    page: Optional[int] = 0,
    items_per_page: Optional[int] = 250,
    dataset_id: Optional[str] = "gtex_v8",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get GTEx transcript/isoform-level median expression: per-transcript (ENST) median TPM across tiss...

    Parameters
    ----------
    operation : str
        Operation type
    gencode_id : str | list[str]
        Gene identifier(s): gene symbol (e.g. 'BRCA1'), Ensembl ID, or versioned GENC...
    gene_symbol : str
        Gene symbol alias for gencode_id.
    tissue_site_detail_id : list[str]
        Optional tissue ID(s) to filter (e.g. ['Whole_Blood']). Omit for all tissues....
    page : int
        Page number (0-based)
    items_per_page : int
        Results per page
    dataset_id : str
        GTEx dataset version (default gtex_v8)
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
            "gencode_id": gencode_id,
            "gene_symbol": gene_symbol,
            "tissue_site_detail_id": tissue_site_detail_id,
            "page": page,
            "items_per_page": items_per_page,
            "dataset_id": dataset_id,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "GTEx_get_median_transcript_expression",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["GTEx_get_median_transcript_expression"]
