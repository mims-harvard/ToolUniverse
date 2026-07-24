"""
EnsemblLD_get_ld_region

Get region-wide pairwise linkage disequilibrium (LD) from the Ensembl REST API: every r-squared a...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EnsemblLD_get_ld_region(
    region: str,
    population: str,
    r2_threshold: Optional[float] = None,
    d_prime_threshold: Optional[float] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get region-wide pairwise linkage disequilibrium (LD) from the Ensembl REST API: every r-squared a...

    Parameters
    ----------
    region : str
        Chromosomal window as 'chr:start..end' (1-based, GRCh38), max 1 Mb. Example: ...
    population : str
        1000 Genomes population. Format: '1000GENOMES:phase_3:<POP>'. Common populati...
    r2_threshold : float
        Minimum r-squared threshold to report. Set higher (e.g., 0.8) for strong LD o...
    d_prime_threshold : float
        Minimum D' threshold to report. Set e.g., 0.8 for high D' only.
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
            "region": region,
            "population": population,
            "r2_threshold": r2_threshold,
            "d_prime_threshold": d_prime_threshold,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "EnsemblLD_get_ld_region",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["EnsemblLD_get_ld_region"]
