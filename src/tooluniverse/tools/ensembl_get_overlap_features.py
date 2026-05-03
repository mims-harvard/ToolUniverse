"""
ensembl_get_overlap_features

Get genomic features (genes, transcripts, repeats) overlapping a region. Returns comprehensive an...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ensembl_get_overlap_features(
    species: str,
    region: str,
    feature: Optional[str] = "gene",
    biotype: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Get genomic features (genes, transcripts, repeats) overlapping a region. Returns comprehensive an...

    Parameters
    ----------
    species : str
        Species (e.g., 'human', 'homo_sapiens')
    region : str
        Genomic region (e.g., '7:140424943-140624564')
    feature : str
        Feature type to retrieve
    biotype : str
        Filter by biotype (optional, e.g., 'protein_coding', 'lincRNA', 'miRNA')
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    list[Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "species": species,
            "region": region,
            "feature": feature,
            "biotype": biotype,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ensembl_get_overlap_features",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ensembl_get_overlap_features"]
