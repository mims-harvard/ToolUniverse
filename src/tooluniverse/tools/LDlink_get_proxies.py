"""
LDlink_get_proxies

Find variants in linkage disequilibrium (LD proxies) with a query SNP, population-specific, via N...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def LDlink_get_proxies(
    variant: str,
    population: Optional[str] = None,
    r2_threshold: Optional[float] = None,
    genome_build: Optional[str] = None,
    limit: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Find variants in linkage disequilibrium (LD proxies) with a query SNP, population-specific, via N...

    Parameters
    ----------
    variant : str
        Query SNP rsID, e.g. 'rs7903146'.
    population : str
        1000 Genomes population code (default 'CEU'). Examples: 'CEU' (European), 'YR...
    r2_threshold : float
        Minimum R2 to report (default 0.8; high LD).
    genome_build : str
        'grch38' (default) or 'grch37'.
    limit : int
        Max proxies to return (1-500, default 50).
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
            "variant": variant,
            "population": population,
            "r2_threshold": r2_threshold,
            "genome_build": genome_build,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "LDlink_get_proxies",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["LDlink_get_proxies"]
