"""
ensembl_get_variants

Get genetic variants (SNPs, indels) in a genomic region using explicit offset/limit pagination ov...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ensembl_get_variants(
    region: str,
    species: Optional[str] = "human",
    feature: Optional[str] = "variation",
    offset: Optional[int] = 0,
    limit: Optional[int] = 500,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Get genetic variants (SNPs, indels) in a genomic region using explicit offset/limit pagination ov...

    Parameters
    ----------
    region : str
        Genomic region in format 'chromosome:start-end' (e.g., '13:32315086-32400268'...
    species : str
        Species name (default 'human'). Examples: 'human', 'mouse', 'rat'
    feature : str
        Feature type to retrieve (default 'variation')
    offset : int
        Zero-based offset within all variants returned by Ensembl.
    limit : int
        Maximum variants returned in this response (default 500, max 5000). Set null ...
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
            "region": region,
            "species": species,
            "feature": feature,
            "offset": offset,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ensembl_get_variants",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ensembl_get_variants"]
