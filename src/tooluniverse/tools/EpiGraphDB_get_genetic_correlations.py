"""
EpiGraphDB_get_genetic_correlations

Get genetic correlations (rg) between a GWAS trait and all other traits in the IEU OpenGWAS datab...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EpiGraphDB_get_genetic_correlations(
    trait: str,
    pval_threshold: Optional[float] = 0.05,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get genetic correlations (rg) between a GWAS trait and all other traits in the IEU OpenGWAS datab...

    Parameters
    ----------
    trait : str
        GWAS trait name to find genetic correlations for (e.g., 'Body mass index', 'D...
    pval_threshold : float
        P-value threshold for genetic correlations (default 0.05).
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
        for k, v in {"trait": trait, "pval_threshold": pval_threshold}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "EpiGraphDB_get_genetic_correlations",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["EpiGraphDB_get_genetic_correlations"]
