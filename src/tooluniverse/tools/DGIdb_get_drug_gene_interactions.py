"""
DGIdb_get_drug_gene_interactions

Get drug-gene interactions for a list of genes from DGIdb. Returns drugs targeting each gene, int...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def DGIdb_get_drug_gene_interactions(
    genes: Optional[list[str]] = None,
    gene_name: Optional[str] = None,
    gene: Optional[str] = None,
    interaction_sources: Optional[list[str]] = None,
    interaction_types: Optional[list[str]] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get drug-gene interactions for a list of genes from DGIdb. Returns drugs targeting each gene, int...

    Parameters
    ----------
    genes : list[str]
        List of gene symbols (e.g., ['EGFR', 'BRAF']). Also accepts a single gene as ...
    gene_name : str
        Alias for genes. Single gene symbol (e.g., 'EGFR').
    gene : str
        Alias for genes. Single gene symbol (e.g., 'EGFR').
    interaction_sources : list[str]
        Optional filter by data sources (e.g., ['DrugBank', 'ChEMBL']).
    interaction_types : list[str]
        Optional filter by interaction types (e.g., ['inhibitor', 'antagonist']).
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
            "genes": genes,
            "gene_name": gene_name,
            "gene": gene,
            "interaction_sources": interaction_sources,
            "interaction_types": interaction_types,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "DGIdb_get_drug_gene_interactions",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["DGIdb_get_drug_gene_interactions"]
