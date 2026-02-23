"""
eQTL_get_associations

Get eQTL associations (variant-gene expression correlations) from a specific dataset in the EBI e...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def eQTL_get_associations(
    dataset_id: str,
    size: Optional[int] = 20,
    gene_id: Optional[str | Any] = None,
    variant: Optional[str | Any] = None,
    molecular_trait_id: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get eQTL associations (variant-gene expression correlations) from a specific dataset in the EBI e...

    Parameters
    ----------
    dataset_id : str
        Dataset identifier from eQTL_list_datasets (e.g., 'QTD000001', 'QTD000584')
    size : int
        Number of associations to return (default 20)
    gene_id : str | Any
        Filter by Ensembl gene ID (e.g., 'ENSG00000141510' for TP53). Returns all eQT...
    variant : str | Any
        Filter by variant in chr_pos_ref_alt format (e.g., 'chr1_791100_G_GGGA'). Ret...
    molecular_trait_id : str | Any
        Filter by molecular trait ID (usually same as gene_id for 'ge' datasets)
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

    return get_shared_client().run_one_function(
        {
            "name": "eQTL_get_associations",
            "arguments": {
                "dataset_id": dataset_id,
                "size": size,
                "gene_id": gene_id,
                "variant": variant,
                "molecular_trait_id": molecular_trait_id,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["eQTL_get_associations"]
