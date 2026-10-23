"""
EpiGraphDB_get_mendelian_randomization

Get Mendelian Randomization (MR) evidence using IEU OpenGWAS data with recoverable offset paginat...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EpiGraphDB_get_mendelian_randomization(
    exposure_trait: Optional[str] = None,
    outcome_trait: Optional[str] = None,
    pval_threshold: Optional[float] = 1e-05,
    limit: Optional[int] = 50,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get Mendelian Randomization (MR) evidence using IEU OpenGWAS data with recoverable offset paginat...

    Parameters
    ----------
    exposure_trait : str
        GWAS trait name for the exposure (e.g., 'Body mass index', 'LDL cholesterol',...
    outcome_trait : str
        GWAS trait name for the outcome (e.g., 'Coronary heart disease', 'Stroke', 'A...
    pval_threshold : float
        P-value threshold for instrument selection (default 1e-5).
    limit : int
        Number of MR results per page (1-1000; default 50).
    offset : int
        Zero-based MR result offset. Continue with next_offset while has_more is true.
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
            "limit": limit,
            "offset": offset,
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
