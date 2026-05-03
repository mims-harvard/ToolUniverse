"""
ClinVar_search_variants

Search for variants in ClinVar database by gene name, condition, or variant ID. Returns variant i...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ClinVar_search_variants(
    gene: Optional[str] = None,
    condition: Optional[str] = None,
    variant_id: Optional[str] = None,
    max_results: Optional[int] = 20,
    limit: Optional[int] = None,
    clinical_significance: Optional[str] = None,
    gene_symbol: Optional[str | Any] = None,
    significance: Optional[str | Any] = None,
    query: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search for variants in ClinVar database by gene name, condition, or variant ID. Returns variant i...

    Parameters
    ----------
    gene : str
        Gene name or symbol (e.g., 'BRCA1', 'BRCA2') At least one of gene, condition,...
    condition : str
        Disease or condition name (e.g., 'breast cancer', 'diabetes') At least one of...
    variant_id : str
        ClinVar variant ID (e.g., '12345') At least one of gene, condition, or varian...
    max_results : int
        Maximum number of results to return (default: 20). Alias: limit.
    limit : int
        Alias for max_results: maximum number of results to return.
    clinical_significance : str
        Filter by clinical significance (e.g., 'Pathogenic', 'Likely pathogenic', 'Be...
    gene_symbol : str | Any
        Alias for gene. HGNC gene symbol (e.g., "DPYD", "CYP2C19").
    significance : str | Any
        Alias for clinical_significance (e.g., "pathogenic", "benign", "uncertain_sig...
    query : str | Any
        Alias for condition. Free-text search mapped to condition/disease field.
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
            "gene": gene,
            "condition": condition,
            "variant_id": variant_id,
            "max_results": max_results,
            "limit": limit,
            "clinical_significance": clinical_significance,
            "gene_symbol": gene_symbol,
            "significance": significance,
            "query": query,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ClinVar_search_variants",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ClinVar_search_variants"]
