"""
Ensembl_get_gene_overlapping_features

Get features overlapping an Ensembl gene by gene ID. Returns all genomic features co-located with...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Ensembl_get_gene_overlapping_features(
    gene_id: str,
    feature_types: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get features overlapping an Ensembl gene by gene ID. Returns all genomic features co-located with...

    Parameters
    ----------
    gene_id : str
        Ensembl gene ID. Examples: 'ENSG00000141510' (TP53), 'ENSG00000012048' (BRCA1...
    feature_types : str
        Comma-separated feature types. Options: 'gene', 'transcript', 'regulatory', '...
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
            "name": "Ensembl_get_gene_overlapping_features",
            "arguments": {"gene_id": gene_id, "feature_types": feature_types},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Ensembl_get_gene_overlapping_features"]
