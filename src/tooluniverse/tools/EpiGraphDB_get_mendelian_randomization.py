"""
EpiGraphDB_get_mendelian_randomization

Get Mendelian Randomization (MR) evidence for a causal relationship between an exposure trait and...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EpiGraphDB_get_mendelian_randomization(
    exposure_trait: str,
    outcome_trait: str,
    pval_threshold: Optional[float] = 1e-05,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get Mendelian Randomization (MR) evidence for a causal relationship between an exposure trait and...

    Parameters
    ----------
    exposure_trait : str
        GWAS trait name for the exposure (e.g., 'Body mass index', 'LDL cholesterol',...
    outcome_trait : str
        GWAS trait name for the outcome (e.g., 'Coronary heart disease', 'Stroke', 'A...
    pval_threshold : float
        P-value threshold for instrument selection (default 1e-5).
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
            "exposure_trait": exposure_trait,
            "outcome_trait": outcome_trait,
            "pval_threshold": pval_threshold,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "EpiGraphDB_get_mendelian_randomization",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["EpiGraphDB_get_mendelian_randomization"]
