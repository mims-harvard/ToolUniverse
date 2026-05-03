"""
EnsemblLD_get_ld_variants

Get linkage disequilibrium (LD) data for a variant from the Ensembl REST API. Returns all variant...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EnsemblLD_get_ld_variants(
    variant_id: str,
    population: str,
    r2_threshold: Optional[float | Any] = None,
    d_prime_threshold: Optional[float | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get linkage disequilibrium (LD) data for a variant from the Ensembl REST API. Returns all variant...

    Parameters
    ----------
    variant_id : str
        rs ID of the variant. Examples: 'rs1042779', 'rs429358', 'rs7903146', 'rs6792...
    population : str
        1000 Genomes population. Format: '1000GENOMES:phase_3:<POP>'. Common populati...
    r2_threshold : float | Any
        Minimum r-squared threshold to report. Default: 0.05. Set higher (e.g., 0.8) ...
    d_prime_threshold : float | Any
        Minimum D' threshold. Default: none. Set e.g., 0.8 for high D' only.
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
            "variant_id": variant_id,
            "population": population,
            "r2_threshold": r2_threshold,
            "d_prime_threshold": d_prime_threshold,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "EnsemblLD_get_ld_variants",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["EnsemblLD_get_ld_variants"]
