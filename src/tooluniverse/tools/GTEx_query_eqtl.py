"""
GTEx_query_eqtl

Query GTEx single-tissue eQTL associations for a gene. Accepts gene symbols (TP53, BRCA1) or Ense...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GTEx_query_eqtl(
    gene_symbol: Optional[str] = None,
    ensembl_gene_id: Optional[str] = None,
    gene_id: Optional[str] = None,
    gene_input: Optional[str] = None,
    tissue_id: Optional[str] = None,
    tissue: Optional[str] = None,
    page: Optional[int] = 1,
    size: Optional[int] = 10,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Query GTEx single-tissue eQTL associations for a gene. Accepts gene symbols (TP53, BRCA1) or Ense...

    Parameters
    ----------
    gene_symbol : str
        Gene symbol (e.g., 'TP53', 'BRCA1'). Auto-resolved to versioned GENCODE ID.
    ensembl_gene_id : str
        Ensembl gene identifier (e.g., 'ENSG00000141510'). Use gene_symbol instead if...
    gene_id : str
        Alias for ensembl_gene_id. Ensembl gene ID (e.g., 'ENSG00000141510').
    gene_input : str
        Alias for gene_symbol. Gene symbol or Ensembl ID (e.g., 'TP53', 'ENSG00000141...
    tissue_id : str
        GTEx tissue ID to filter eQTL results (e.g., 'Brain_Cortex', 'Whole_Blood', '...
    tissue : str
        Alias for tissue_id. GTEx tissue name (e.g., 'Brain_Cortex', 'Whole_Blood').
    page : int
        Page number (1-based).
    size : int
        Number of records per page (1–100).
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
            "gene_symbol": gene_symbol,
            "ensembl_gene_id": ensembl_gene_id,
            "gene_id": gene_id,
            "gene_input": gene_input,
            "tissue_id": tissue_id,
            "tissue": tissue,
            "page": page,
            "size": size,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "GTEx_query_eqtl",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["GTEx_query_eqtl"]
