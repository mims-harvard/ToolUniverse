"""
PharmacoDB_get_biomarker_assoc

Get gene-compound biomarker associations from PharmacoDB showing how gene expression or other mol...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PharmacoDB_get_biomarker_assoc(
    operation: str,
    compound_name: Optional[str | Any] = None,
    compound_id: Optional[int | Any] = None,
    gene_name: Optional[str | Any] = None,
    tissue_name: Optional[str | Any] = None,
    mdata_type: Optional[str | Any] = None,
    per_page: Optional[int] = 20,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get gene-compound biomarker associations from PharmacoDB showing how gene expression or other mol...

    Parameters
    ----------
    operation : str
        Operation type
    compound_name : str | Any
        Compound name (e.g., 'Paclitaxel', 'Erlotinib'). Either compound_name or comp...
    compound_id : int | Any
        PharmacoDB compound ID. Either compound_name or compound_id required.
    gene_name : str | Any
        Gene Ensembl ID to filter (e.g., 'ENSG00000141510' for TP53)
    tissue_name : str | Any
        Tissue type to filter (e.g., 'Breast', 'Lung', 'Skin')
    mdata_type : str | Any
        Molecular data type: 'rna' (gene expression), 'cnv' (copy number), 'mutation'
    per_page : int
        Number of results per page (default 20, max 100)
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
            "compound_name": compound_name,
            "compound_id": compound_id,
            "gene_name": gene_name,
            "tissue_name": tissue_name,
            "mdata_type": mdata_type,
            "per_page": per_page,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "PharmacoDB_get_biomarker_assoc",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PharmacoDB_get_biomarker_assoc"]
