"""
EnsemblPheno_get_by_region

Get phenotype associations for variants and genes in an Ensembl region with limit/offset paginati...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EnsemblPheno_get_by_region(
    region: str,
    species: Optional[str] = "homo_sapiens",
    feature_type: Optional[str] = None,
    limit: Optional[int] = 200,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get phenotype associations for variants and genes in an Ensembl region with limit/offset paginati...

    Parameters
    ----------
    species : str
        Species name. Use 'homo_sapiens' for human. Default: 'homo_sapiens'.
    region : str
        Genomic region in format 'chromosome:start-end'. Example: '17:7661779-7687538...
    feature_type : str
        Filter by feature type: 'Variation' (variants only), 'Gene' (genes only), 'QT...
    limit : int
        Maximum number of deduplicated phenotype associations to return in this page.
    offset : int
        Zero-based association offset. Use data.next_offset for the next page.
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
            "feature_type": feature_type,
            "limit": limit,
            "offset": offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "EnsemblPheno_get_by_region",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["EnsemblPheno_get_by_region"]
