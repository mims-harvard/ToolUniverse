"""
HPA_get_disease_expression_by_gene_tissue_disease

Compare the expression level of a gene in specific disease state versus healthy state using gene ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def HPA_get_disease_expression_by_gene_tissue_disease(
    gene_name: str,
    tissue_type: str,
    disease_name: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Compare the expression level of a gene in specific disease state versus healthy state using gene ...

    Parameters
    ----------
    gene_name : str
        Gene name or gene symbol, e.g., 'TP53', 'BRCA1', 'KRAS', etc.
    tissue_type : str
        Tissue type, e.g., 'brain', 'breast', 'colon', 'lung', etc., optional parameter.
    disease_name : str
        Disease name, supported diseases include: brain_cancer, breast_cancer, colon_...
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
            "gene_name": gene_name,
            "tissue_type": tissue_type,
            "disease_name": disease_name,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "HPA_get_disease_expression_by_gene_tissue_disease",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["HPA_get_disease_expression_by_gene_tissue_disease"]
