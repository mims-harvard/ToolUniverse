"""
Coloc_abf_test

Bayesian colocalization (coloc.abf, Giambartolomei 2014) of two GWAS/QTL signals over the same SN...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Coloc_abf_test(
    beta1: list[Any],
    se1: list[Any],
    beta2: list[Any],
    se2: list[Any],
    snp: Optional[list[str]] = None,
    sd_prior: Optional[float] = None,
    p1: Optional[float] = None,
    p2: Optional[float] = None,
    p12: Optional[float] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Bayesian colocalization (coloc.abf, Giambartolomei 2014) of two GWAS/QTL signals over the same SN...

    Parameters
    ----------
    beta1 : list[Any]
        Trait 1 per-SNP effect sizes over the region (same SNP order as trait 2).
    se1 : list[Any]
        Standard errors of beta1 (positive).
    beta2 : list[Any]
        Trait 2 per-SNP effect sizes (same SNP order/alleles).
    se2 : list[Any]
        Standard errors of beta2 (positive).
    snp : list[str]
        Optional SNP identifiers (same order) to label the best shared variant.
    sd_prior : float
        Prior SD of the effect size (default 0.15; 0.2 common for case/control log-OR).
    p1 : float
        Prior prob a SNP is causal for trait 1 (default 1e-4).
    p2 : float
        Prior prob a SNP is causal for trait 2 (default 1e-4).
    p12 : float
        Prior prob a SNP is causal for both traits (default 1e-5).
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
            "beta1": beta1,
            "se1": se1,
            "beta2": beta2,
            "se2": se2,
            "snp": snp,
            "sd_prior": sd_prior,
            "p1": p1,
            "p2": p2,
            "p12": p12,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Coloc_abf_test",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Coloc_abf_test"]
