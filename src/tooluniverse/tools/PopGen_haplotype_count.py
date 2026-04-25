"""
PopGen_haplotype_count

Estimate distinct haplotypes after recombination across generations for a region with multiple bi...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PopGen_haplotype_count(
    operation: str,
    n_snps: int,
    generations: Optional[int] = None,
    recomb_rate: Optional[float] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Estimate distinct haplotypes after recombination across generations for a region with multiple bi...

    Parameters
    ----------
    operation : str
        Operation type
    n_snps : int
        Number of biallelic SNP loci in the region
    generations : int
        Number of generations of random mating (default 1)
    recomb_rate : float
        Per-adjacent-interval recombination rate [0, 1] per generation (default 0.5)
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
            "operation": operation,
            "n_snps": n_snps,
            "generations": generations,
            "recomb_rate": recomb_rate,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "PopGen_haplotype_count",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PopGen_haplotype_count"]
