"""
Finemap_credible_set

Single-causal-variant fine-mapping from GWAS/QTL summary statistics (per-SNP effect size + SE ove...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Finemap_credible_set(
    beta: list[Any],
    se: list[Any],
    snp: Optional[list[str]] = None,
    coverage: Optional[float] = None,
    sd_prior: Optional[float] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Single-causal-variant fine-mapping from GWAS/QTL summary statistics (per-SNP effect size + SE ove...

    Parameters
    ----------
    beta : list[Any]
        Per-SNP effect sizes over the region.
    se : list[Any]
        Standard errors of beta (positive).
    snp : list[str]
        Optional SNP identifiers (same order) to label PIPs and the credible set.
    coverage : float
        Credible-set coverage in (0,1] (default 0.95).
    sd_prior : float
        Prior SD of the effect size (default 0.15).
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
            "beta": beta,
            "se": se,
            "snp": snp,
            "coverage": coverage,
            "sd_prior": sd_prior,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Finemap_credible_set",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Finemap_credible_set"]
