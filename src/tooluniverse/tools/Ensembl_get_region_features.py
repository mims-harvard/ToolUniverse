"""
Ensembl_get_region_features

Get all genomic features overlapping a specified chromosomal region. Returns genes, transcripts, ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Ensembl_get_region_features(
    region: str,
    species: Optional[str] = None,
    feature_types: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get all genomic features overlapping a specified chromosomal region. Returns genes, transcripts, ...

    Parameters
    ----------
    species : str
        Species name. Default: 'human'. Examples: 'human', 'mouse', 'rat', 'zebrafish'.
    region : str
        Genomic region in format 'chr:start-end'. Examples: '17:7661779-7687546' (TP5...
    feature_types : str
        Comma-separated feature types to retrieve. Options: 'gene', 'transcript', 're...
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
            "species": species,
            "region": region,
            "feature_types": feature_types,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Ensembl_get_region_features",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Ensembl_get_region_features"]
